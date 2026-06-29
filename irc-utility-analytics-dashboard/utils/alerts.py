from __future__ import annotations

import numpy as np
import pandas as pd

import config
from utils.calculations import pct_change, utility_aggregate


def _priority(sev: str) -> int:
    return {"Critical": 3, "Review": 2, "Info": 1, "Normal": 0}.get(str(sev), 0)


def _max_severity(a: str, b: str) -> str:
    return a if _priority(a) >= _priority(b) else b


def _severity_from_positive_change(value) -> str:
    if value is None or pd.isna(value):
        return "Info"
    try:
        v = float(value)
    except Exception:
        return "Info"
    if v >= getattr(config, "CRITICAL_THRESHOLD", 20.0):
        return "Critical"
    if v >= getattr(config, "WARNING_THRESHOLD", 10.0):
        return "Review"
    return "Info"


def _fmt_pct(v) -> str:
    if v is None or pd.isna(v):
        return "not available"
    return f"{float(v):+.1f}%"


def _latest_month_text(combo_history: pd.DataFrame, current_month) -> str:
    prior = combo_history[combo_history["billing_month"] < pd.to_datetime(current_month)].copy()
    if prior.empty:
        return "No prior month on file"
    latest_month = prior["billing_month"].dropna().max()
    if pd.notna(latest_month):
        return f"Latest month on file: {pd.to_datetime(latest_month).strftime('%B %Y')}"
    return "No prior month on file"


def _expected_amount_from_treatments(previous_amount, treatment_chg):
    """Expected cost if cost moved exactly with treatment volume."""
    if previous_amount is None or pd.isna(previous_amount):
        return np.nan
    if treatment_chg is None or pd.isna(treatment_chg):
        return previous_amount
    return float(previous_amount) * (1 + float(treatment_chg) / 100.0)


def explain_change(utility, cost_chg, usage_chg, treatment_chg, cpt_chg, cpu_chg=None, upt_chg=None) -> str:
    """Plain-English, treatment-centered explanation for an alert."""
    flat = getattr(config, "TREATMENT_FLAT_THRESHOLD", 5.0)
    buffer = getattr(config, "VOLUME_JUSTIFIED_BUFFER", 5.0)

    if pd.notna(cpt_chg) and cpt_chg >= getattr(config, "WARNING_THRESHOLD", 10.0):
        return f"Cost per treatment increased {_fmt_pct(cpt_chg)}. Utility spend rose faster than treatment volume."
    if pd.notna(upt_chg) and upt_chg >= getattr(config, "WARNING_THRESHOLD", 10.0):
        return f"Usage per treatment increased {_fmt_pct(upt_chg)}. Usage is not tracking with treatment volume."

    if pd.notna(cost_chg) and pd.notna(treatment_chg) and cost_chg > treatment_chg + buffer:
        return f"Cost changed {_fmt_pct(cost_chg)} while treatments changed {_fmt_pct(treatment_chg)}. Cost is outpacing treatment volume."
    if pd.notna(usage_chg) and pd.notna(treatment_chg) and usage_chg > treatment_chg + buffer:
        return f"Usage changed {_fmt_pct(usage_chg)} while treatments changed {_fmt_pct(treatment_chg)}. Usage is outpacing treatment volume."
    if pd.notna(cost_chg) and pd.notna(usage_chg) and pd.notna(treatment_chg) and treatment_chg <= flat and (cost_chg >= getattr(config, "WARNING_THRESHOLD", 10.0) or usage_chg >= getattr(config, "WARNING_THRESHOLD", 10.0)):
        return f"Cost/usage increased while treatments were essentially flat ({_fmt_pct(treatment_chg)}). Review billing, rate changes, leaks, or equipment activity."
    if pd.notna(treatment_chg) and treatment_chg < -flat and ((pd.notna(cost_chg) and cost_chg > 0) or (pd.notna(usage_chg) and usage_chg > 0)):
        return f"Treatments decreased {_fmt_pct(treatment_chg)}, but cost or usage increased. This moves opposite of treatment volume."
    return "Cost, usage, and treatment movement appear reasonably aligned."


def build_alerts(df: pd.DataFrame, current_month, previous_month=None) -> pd.DataFrame:
    """Create treatment-driven alert records.

    V11 alert logic uses treatments as the primary driver. Raw cost or raw usage
    changes are not enough by themselves. The dashboard flags items when:
    - cost/treatment increases,
    - usage/treatment increases,
    - cost or usage rises materially faster than treatments,
    - cost/usage rises while treatments are flat or down,
    - the selected reporting month has no bill for a historical property/utility.
    """
    columns = [
        "Severity", "State", "Property", "Utility", "Reason", "Current Cost", "Previous Cost", "Cost Change %",
        "Current Usage", "Previous Usage", "Usage Change %", "Current Treatments", "Previous Treatments", "Treatments Change %",
        "Current Cost/Treatment", "Previous Cost/Treatment", "Cost/Treatment Change %",
        "Current Cost/Usage", "Previous Cost/Usage", "Cost/Usage Change %",
        "Current Usage/Treatment", "Previous Usage/Treatment", "Usage/Treatment Change %",
        "Estimated Monthly Impact", "Latest Month On File", "Missing Bill", "Explanation"
    ]
    uagg = utility_aggregate(df)
    if uagg.empty:
        return pd.DataFrame(columns=columns)

    current_month = pd.to_datetime(current_month).to_period("M").to_timestamp()
    previous_month = pd.to_datetime(previous_month).to_period("M").to_timestamp() if previous_month is not None else None
    cur = uagg[uagg["billing_month"] == current_month].copy()
    prev = uagg[uagg["billing_month"] == previous_month].copy() if previous_month is not None else uagg.iloc[0:0].copy()

    prev = prev.rename(columns={
        "amount": "prev_amount",
        "usage": "prev_usage",
        "treatments": "prev_treatments",
        "cost_per_treatment": "prev_cost_per_treatment",
        "cost_per_usage": "prev_cost_per_usage",
        "usage_per_treatment": "prev_usage_per_treatment",
    })
    merge_cols = ["state", "property", "utility"]
    prev_cols = merge_cols + ["prev_amount", "prev_usage", "prev_treatments", "prev_cost_per_treatment", "prev_cost_per_usage", "prev_usage_per_treatment"]
    merged = cur.merge(prev[prev_cols], on=merge_cols, how="left") if not cur.empty else cur

    warning = getattr(config, "WARNING_THRESHOLD", 10.0)
    critical = getattr(config, "CRITICAL_THRESHOLD", 20.0)
    flat = getattr(config, "TREATMENT_FLAT_THRESHOLD", 5.0)
    buffer = getattr(config, "VOLUME_JUSTIFIED_BUFFER", 5.0)

    rows: list[dict] = []
    for _, r in merged.iterrows():
        cost_chg = pct_change(r["amount"], r.get("prev_amount"))
        usage_chg = pct_change(r["usage"], r.get("prev_usage"))
        treatment_chg = pct_change(r["treatments"], r.get("prev_treatments"))
        cpt_chg = pct_change(r["cost_per_treatment"], r.get("prev_cost_per_treatment"))
        cpu_chg = pct_change(r["cost_per_usage"], r.get("prev_cost_per_usage"))
        upt_chg = pct_change(r["usage_per_treatment"], r.get("prev_usage_per_treatment"))

        reasons: list[str] = []
        severity = "Info"

        # Primary treatment-normalized anomalies.
        if pd.notna(cpt_chg) and cpt_chg >= warning:
            severity = _max_severity(severity, _severity_from_positive_change(cpt_chg))
            reasons.append(f"Cost/treatment increased {cpt_chg:.1f}%")
        if pd.notna(upt_chg) and upt_chg >= warning:
            severity = _max_severity(severity, _severity_from_positive_change(upt_chg))
            reasons.append(f"Usage/treatment increased {upt_chg:.1f}%")

        # Raw cost/usage only matter when they are not justified by treatment movement.
        if pd.notna(cost_chg) and pd.notna(treatment_chg):
            cost_gap = cost_chg - treatment_chg
            if cost_gap >= warning:
                severity = _max_severity(severity, "Critical" if cost_gap >= critical else "Review")
                if abs(treatment_chg) <= flat:
                    reasons.append(f"Cost increased {cost_chg:.1f}% while treatments stayed flat ({treatment_chg:+.1f}%)")
                else:
                    reasons.append(f"Cost outpaced treatments by {cost_gap:.1f} pts")
            elif cost_chg >= warning and cost_chg > treatment_chg + buffer:
                severity = _max_severity(severity, "Review")
                reasons.append(f"Cost increased more than treatment volume")

        if pd.notna(usage_chg) and pd.notna(treatment_chg):
            usage_gap = usage_chg - treatment_chg
            if usage_gap >= warning:
                severity = _max_severity(severity, "Critical" if usage_gap >= critical else "Review")
                if abs(treatment_chg) <= flat:
                    reasons.append(f"Usage increased {usage_chg:.1f}% while treatments stayed flat ({treatment_chg:+.1f}%)")
                else:
                    reasons.append(f"Usage outpaced treatments by {usage_gap:.1f} pts")
            elif usage_chg >= warning and usage_chg > treatment_chg + buffer:
                severity = _max_severity(severity, "Review")
                reasons.append(f"Usage increased more than treatment volume")

        if pd.notna(treatment_chg) and treatment_chg < -flat:
            if (pd.notna(cost_chg) and cost_chg > 0) or (pd.notna(usage_chg) and usage_chg > 0):
                severity = _max_severity(severity, "Critical" if max(cost_chg if pd.notna(cost_chg) else 0, usage_chg if pd.notna(usage_chg) else 0) >= critical else "Review")
                reasons.append(f"Treatments decreased {abs(treatment_chg):.1f}% while cost/usage increased")

        if not reasons:
            continue

        expected_amount = _expected_amount_from_treatments(r.get("prev_amount"), treatment_chg)
        estimated_impact = max(0, float(r.get("amount") or 0) - float(expected_amount)) if pd.notna(expected_amount) else max(0, float(r.get("amount") or 0) - float(r.get("prev_amount") or 0))

        rows.append({
            "Severity": severity,
            "State": r["state"],
            "Property": r["property"],
            "Utility": r["utility"],
            "Reason": "; ".join(dict.fromkeys(reasons)),
            "Current Cost": r["amount"],
            "Previous Cost": r.get("prev_amount"),
            "Cost Change %": cost_chg,
            "Current Usage": r["usage"],
            "Previous Usage": r.get("prev_usage"),
            "Usage Change %": usage_chg,
            "Current Treatments": r["treatments"],
            "Previous Treatments": r.get("prev_treatments"),
            "Treatments Change %": treatment_chg,
            "Current Cost/Treatment": r["cost_per_treatment"],
            "Previous Cost/Treatment": r.get("prev_cost_per_treatment"),
            "Cost/Treatment Change %": cpt_chg,
            "Current Cost/Usage": r["cost_per_usage"],
            "Previous Cost/Usage": r.get("prev_cost_per_usage"),
            "Cost/Usage Change %": cpu_chg,
            "Current Usage/Treatment": r["usage_per_treatment"],
            "Previous Usage/Treatment": r.get("prev_usage_per_treatment"),
            "Usage/Treatment Change %": upt_chg,
            "Estimated Monthly Impact": estimated_impact,
            "Latest Month On File": pd.to_datetime(r.get("billing_month")).strftime("%B %Y") if pd.notna(r.get("billing_month")) else "—",
            "Missing Bill": False,
            "Explanation": explain_change(r["utility"], cost_chg, usage_chg, treatment_chg, cpt_chg, cpu_chg, upt_chg),
        })

    # Missing bills for the selected month only.
    combo_span = (
        uagg.groupby(["state", "property", "utility"], as_index=False)
        .agg(first_month=("billing_month", "min"), last_month=("billing_month", "max"))
    )
    expected = combo_span[combo_span["first_month"] < current_month][["state", "property", "utility"]].drop_duplicates()
    current_combos = cur[["state", "property", "utility"]].drop_duplicates() if not cur.empty else pd.DataFrame(columns=["state", "property", "utility"])
    missing = expected.merge(current_combos, on=["state", "property", "utility"], how="left", indicator=True)
    missing = missing[missing["_merge"] == "left_only"].drop(columns=["_merge"])
    for _, combo in missing.iterrows():
        history = uagg[
            (uagg["state"] == combo["state"]) &
            (uagg["property"] == combo["property"]) &
            (uagg["utility"] == combo["utility"])
        ].copy()
        prior = history[history["billing_month"] < current_month].copy().sort_values("billing_month")
        latest_rows = prior[prior["billing_month"] == prior["billing_month"].max()] if not prior.empty else history.iloc[0:0]
        latest_amount = latest_rows["amount"].sum() if not latest_rows.empty else np.nan
        latest_usage = latest_rows["usage"].sum() if not latest_rows.empty else np.nan
        latest_treatments = latest_rows["treatments"].max() if not latest_rows.empty else np.nan
        latest_scale = latest_rows["usage_scale"].dropna().iloc[0] if not latest_rows.empty and latest_rows["usage_scale"].notna().any() else 1
        latest_cpt = latest_amount / latest_treatments if pd.notna(latest_amount) and pd.notna(latest_treatments) and latest_treatments else np.nan
        latest_cpu = latest_amount / latest_usage * latest_scale if pd.notna(latest_amount) and pd.notna(latest_usage) and latest_usage else np.nan
        latest_upt = latest_usage / latest_treatments if pd.notna(latest_usage) and pd.notna(latest_treatments) and latest_treatments else np.nan
        latest_month_label = pd.to_datetime(latest_rows["billing_month"].max()).strftime("%B %Y") if not latest_rows.empty else "—"
        latest_month_msg = _latest_month_text(history, current_month)

        rows.append({
            "Severity": "Critical",
            "State": combo["state"],
            "Property": combo["property"],
            "Utility": combo["utility"],
            "Reason": f"No bill found for selected month. {latest_month_msg}",
            "Current Cost": np.nan,
            "Previous Cost": latest_amount,
            "Cost Change %": np.nan,
            "Current Usage": np.nan,
            "Previous Usage": latest_usage,
            "Usage Change %": np.nan,
            "Current Treatments": np.nan,
            "Previous Treatments": latest_treatments,
            "Treatments Change %": np.nan,
            "Current Cost/Treatment": np.nan,
            "Previous Cost/Treatment": latest_cpt,
            "Cost/Treatment Change %": np.nan,
            "Current Cost/Usage": np.nan,
            "Previous Cost/Usage": latest_cpu,
            "Cost/Usage Change %": np.nan,
            "Current Usage/Treatment": np.nan,
            "Previous Usage/Treatment": latest_upt,
            "Usage/Treatment Change %": np.nan,
            "Estimated Monthly Impact": latest_amount if pd.notna(latest_amount) else 0,
            "Latest Month On File": latest_month_label,
            "Missing Bill": True,
            "Explanation": "The selected reporting month has no bill for this property and utility. Review the source bill entry or confirm the bill has not been received.",
        })

    out = pd.DataFrame(rows, columns=columns)
    if out.empty:
        return out
    out["Priority"] = out["Severity"].map({"Critical": 3, "Review": 2, "Info": 1}).fillna(0)
    out = out.sort_values(["Priority", "Estimated Monthly Impact"], ascending=[False, False]).drop(columns=["Priority"])
    return out.reset_index(drop=True)


def alert_counts(alerts: pd.DataFrame) -> dict:
    if alerts is None or alerts.empty:
        return {"Critical": 0, "Review": 0, "Info": 0, "Total": 0}
    return {
        "Critical": int((alerts["Severity"] == "Critical").sum()),
        "Review": int((alerts["Severity"] == "Review").sum()),
        "Info": int((alerts["Severity"] == "Info").sum()),
        "Total": int(len(alerts)),
    }
