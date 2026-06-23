from __future__ import annotations

import numpy as np
import pandas as pd

import config
from utils.calculations import pct_change, utility_aggregate


def _severity_from_values(*changes) -> str:
    valid = [abs(float(c)) for c in changes if c is not None and not pd.isna(c)]
    if not valid:
        return "Info"
    high = max(valid)
    if high >= getattr(config, "CRITICAL_THRESHOLD", 20.0):
        return "Critical"
    if high >= getattr(config, "WARNING_THRESHOLD", 10.0):
        return "Review"
    return "Info"


def _priority(sev: str) -> int:
    return {"Critical": 3, "Review": 2, "Info": 1, "Normal": 0}.get(str(sev), 0)


def _format_us_date(value) -> str:
    if value is None or pd.isna(value):
        return "—"
    d = pd.to_datetime(value, errors="coerce")
    if pd.isna(d):
        return "—"
    return f"{d.month}/{d.day}/{d.year}"


def _latest_bill_text(combo_history: pd.DataFrame, current_month) -> str:
    prior = combo_history[combo_history["billing_month"] < pd.to_datetime(current_month)].copy()
    if prior.empty:
        return "No prior bill on file"
    # Use the latest actual bill date when available; otherwise use the latest service month.
    latest_date = prior["billing_date"].dropna().max()
    if pd.notna(latest_date):
        return f"Latest bill on file: {_format_us_date(latest_date)}"
    latest_month = prior["billing_month"].dropna().max()
    if pd.notna(latest_month):
        return f"Latest bill on file: {pd.to_datetime(latest_month).strftime('%b %Y')}"
    return "No prior bill on file"


def build_alerts(df: pd.DataFrame, current_month, previous_month=None) -> pd.DataFrame:
    """Create alert records for current month changes plus selected-month missing bills.

    Missing-bill logic is based on the selected report month, not days since today.
    A property/utility combination is flagged only if that combination exists in
    the filtered historical data but has no bill in the selected month.
    """
    uagg = utility_aggregate(df)
    if uagg.empty:
        return pd.DataFrame(columns=["Severity", "Property", "Utility", "Reason"])

    current_month = pd.to_datetime(current_month)
    previous_month = pd.to_datetime(previous_month) if previous_month is not None else None
    cur = uagg[uagg["billing_month"] == current_month].copy()
    prev = uagg[uagg["billing_month"] == previous_month].copy() if previous_month is not None else uagg.iloc[0:0].copy()

    prev = prev.rename(columns={
        "amount": "prev_amount", "usage": "prev_usage", "treatments": "prev_treatments",
        "cost_per_treatment": "prev_cost_per_treatment", "cost_per_usage": "prev_cost_per_usage",
        "billing_date": "prev_billing_date",
    })
    merge_cols = ["state", "property", "utility"]
    merged = cur.merge(prev[merge_cols + ["prev_amount", "prev_usage", "prev_treatments", "prev_cost_per_treatment", "prev_cost_per_usage", "prev_billing_date"]], on=merge_cols, how="left")

    rows = []
    for _, r in merged.iterrows():
        cost_chg = pct_change(r["amount"], r.get("prev_amount"))
        usage_chg = pct_change(r["usage"], r.get("prev_usage"))
        cpt_chg = pct_change(r["cost_per_treatment"], r.get("prev_cost_per_treatment"))
        cpu_chg = pct_change(r["cost_per_usage"], r.get("prev_cost_per_usage"))
        treatment_chg = pct_change(r["treatments"], r.get("prev_treatments"))

        reasons = []
        severity = _severity_from_values(
            cost_chg if pd.notna(cost_chg) and cost_chg > 0 else np.nan,
            usage_chg if pd.notna(usage_chg) and usage_chg > 0 else np.nan,
            cpt_chg if pd.notna(cpt_chg) and cpt_chg > 0 else np.nan,
            cpu_chg if pd.notna(cpu_chg) and cpu_chg > 0 else np.nan,
        )

        if pd.notna(cost_chg) and cost_chg >= config.WARNING_THRESHOLD:
            reasons.append(f"Cost increased {cost_chg:.1f}%")
        if pd.notna(usage_chg) and usage_chg >= config.WARNING_THRESHOLD:
            reasons.append(f"Usage increased {usage_chg:.1f}%")
        if pd.notna(cpt_chg) and cpt_chg >= config.WARNING_THRESHOLD:
            reasons.append(f"Cost/treatment increased {cpt_chg:.1f}%")
        if pd.notna(cpu_chg) and cpu_chg >= config.WARNING_THRESHOLD:
            reasons.append(f"Cost/usage increased {cpu_chg:.1f}%")

        if pd.notna(cost_chg) and pd.notna(usage_chg) and cost_chg >= config.WARNING_THRESHOLD and usage_chg <= config.FLAT_CHANGE_TOLERANCE:
            severity = "Critical" if cost_chg >= config.CRITICAL_THRESHOLD else max(severity, "Review", key=_priority)
            reasons.append("Cost rose while usage was flat/decreased")

        if pd.notna(usage_chg) and pd.notna(treatment_chg) and usage_chg >= config.WARNING_THRESHOLD and treatment_chg <= config.FLAT_CHANGE_TOLERANCE:
            severity = "Critical" if usage_chg >= config.CRITICAL_THRESHOLD else max(severity, "Review", key=_priority)
            reasons.append("Usage rose faster than treatments")

        if not reasons and severity == "Info":
            continue

        rows.append({
            "Severity": severity,
            "State": r["state"],
            "Property": r["property"],
            "Utility": r["utility"],
            "Reason": "; ".join(dict.fromkeys(reasons)) or "Minor movement",
            "Current Cost": r["amount"],
            "Previous Cost": r.get("prev_amount"),
            "Cost Change %": cost_chg,
            "Current Usage": r["usage"],
            "Previous Usage": r.get("prev_usage"),
            "Usage Change %": usage_chg,
            "Current Cost/Treatment": r["cost_per_treatment"],
            "Previous Cost/Treatment": r.get("prev_cost_per_treatment"),
            "Cost/Treatment Change %": cpt_chg,
            "Current Cost/Usage": r["cost_per_usage"],
            "Previous Cost/Usage": r.get("prev_cost_per_usage"),
            "Cost/Usage Change %": cpu_chg,
            "Treatments Change %": treatment_chg,
            "Estimated Monthly Impact": max(0, (r["amount"] or 0) - (r.get("prev_amount") if pd.notna(r.get("prev_amount")) else 0)),
            "Latest Bill": _format_us_date(r.get("billing_date")),
            "Latest Month On File": pd.to_datetime(r.get("billing_month")).strftime("%b %Y") if pd.notna(r.get("billing_month")) else "—",
            "Missing Bill": False,
            "Explanation": explain_change(r["utility"], cost_chg, usage_chg, treatment_chg, cpt_chg),
        })

    # Missing bills for the selected month only.
    # A combo is expected only when it already had at least one bill BEFORE the
    # selected month. This avoids flagging properties/utilities that did not yet
    # exist in earlier report months.
    combo_span = (
        uagg.groupby(["state", "property", "utility"], as_index=False)
        .agg(first_month=("billing_month", "min"), last_month=("billing_month", "max"))
    )
    expected = combo_span[combo_span["first_month"] < current_month][["state", "property", "utility"]].drop_duplicates()
    current_combos = cur[["state", "property", "utility"]].drop_duplicates()
    missing = expected.merge(current_combos, on=["state", "property", "utility"], how="left", indicator=True)
    missing = missing[missing["_merge"] == "left_only"].drop(columns=["_merge"])
    for _, combo in missing.iterrows():
        history = uagg[
            (uagg["state"] == combo["state"]) &
            (uagg["property"] == combo["property"]) &
            (uagg["utility"] == combo["utility"])
        ].copy()

        # Use the most recent bill BEFORE the selected month as the reference.
        # This is more useful than leaving the card blank when the current-month
        # bill is missing, and it still keeps the alert honest.
        prior = history[history["billing_month"] < current_month].copy().sort_values("billing_month")
        latest_rows = prior[prior["billing_month"] == prior["billing_month"].max()] if not prior.empty else history.iloc[0:0]
        latest_amount = latest_rows["amount"].sum() if not latest_rows.empty else np.nan
        latest_usage = latest_rows["usage"].sum() if not latest_rows.empty else np.nan
        latest_treatments = latest_rows["treatments"].max() if not latest_rows.empty else np.nan
        latest_scale = latest_rows["usage_scale"].dropna().iloc[0] if not latest_rows.empty and latest_rows["usage_scale"].notna().any() else 1
        latest_cpt = latest_amount / latest_treatments if pd.notna(latest_amount) and pd.notna(latest_treatments) and latest_treatments else np.nan
        latest_cpu = latest_amount / latest_usage * latest_scale if pd.notna(latest_amount) and pd.notna(latest_usage) and latest_usage else np.nan
        latest_month_label = pd.to_datetime(latest_rows["billing_month"].max()).strftime("%b %Y") if not latest_rows.empty else "—"

        latest_bill_msg = _latest_bill_text(history, current_month)
        reason = f"No bill found for selected month. {latest_bill_msg}"
        rows.append({
            "Severity": "Critical",
            "State": combo["state"],
            "Property": combo["property"],
            "Utility": combo["utility"],
            "Reason": reason,
            "Current Cost": np.nan,
            "Previous Cost": latest_amount,
            "Cost Change %": np.nan,
            "Current Usage": np.nan,
            "Previous Usage": latest_usage,
            "Usage Change %": np.nan,
            "Current Cost/Treatment": np.nan,
            "Previous Cost/Treatment": latest_cpt,
            "Cost/Treatment Change %": np.nan,
            "Current Cost/Usage": np.nan,
            "Previous Cost/Usage": latest_cpu,
            "Cost/Usage Change %": np.nan,
            "Treatments Change %": np.nan,
            "Estimated Monthly Impact": latest_amount if pd.notna(latest_amount) else 0,
            "Latest Bill": latest_bill_msg.replace("Latest bill on file: ", ""),
            "Latest Month On File": latest_month_label,
            "Missing Bill": True,
            "Explanation": "No current-month bill was found for this property and utility. Confirm whether the bill is missing, delayed, or entered under a different period.",
        })

    if not rows:
        return pd.DataFrame(columns=["Severity", "Property", "Utility", "Reason"])
    out = pd.DataFrame(rows)
    out["Priority"] = out["Severity"].map({"Critical": 3, "Review": 2, "Info": 1}).fillna(0)
    out = out.sort_values(["Priority", "Estimated Monthly Impact"], ascending=[False, False]).drop(columns=["Priority"])
    return out


def explain_change(utility, cost_chg, usage_chg, treatment_chg, cpt_chg) -> str:
    def ok(x):
        return x is not None and not pd.isna(x)
    u = str(utility).title()
    if ok(cost_chg) and ok(usage_chg) and cost_chg >= 20 and usage_chg <= 5:
        return f"{u} cost rose significantly while usage stayed relatively flat. Review rates, fees, billing adjustments, or invoice line items."
    if ok(usage_chg) and ok(treatment_chg) and usage_chg >= 20 and treatment_chg <= 5:
        if "Water" in u or "Sewer" in u:
            return f"{u} usage rose much faster than treatment volume. Check for leak, meter issue, irrigation, or unusual facility activity."
        return f"{u} usage rose much faster than treatment volume. Check equipment operation, schedule changes, or meter/billing issues."
    if ok(cpt_chg) and cpt_chg >= 20:
        return "Cost per treatment increased sharply, meaning utility cost rose faster than treatment volume. Prioritize review."
    if ok(cost_chg) and ok(usage_chg) and abs(cost_chg - usage_chg) <= 5 and cost_chg >= 10:
        return "Cost and usage increased at a similar rate, which may be operationally consistent. Compare treatment volume and days billed."
    if ok(cost_chg) and cost_chg < 0:
        return "Cost decreased compared with the prior month. Monitor to confirm the improvement continues."
    return "Review cost, usage, days billed, and treatment volume to determine whether the change is operational or billing-related."


def alert_counts(alerts: pd.DataFrame) -> dict:
    if alerts is None or alerts.empty:
        return {"Critical": 0, "Review": 0, "Info": 0, "Total": 0}
    return {
        "Critical": int((alerts["Severity"] == "Critical").sum()),
        "Review": int((alerts["Severity"] == "Review").sum()),
        "Info": int((alerts["Severity"] == "Info").sum()),
        "Total": int(len(alerts)),
    }
