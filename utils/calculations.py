from __future__ import annotations

import numpy as np
import pandas as pd


def fmt_money(v, digits=0):
    if v is None or pd.isna(v):
        return "—"
    return f"${float(v):,.{digits}f}"


def fmt_num(v, digits=0):
    if v is None or pd.isna(v):
        return "—"
    return f"{float(v):,.{digits}f}"


def fmt_pct(v):
    if v is None or pd.isna(v):
        return "—"
    arrow = "▲" if v > 0 else "▼" if v < 0 else "→"
    return f"{arrow} {abs(float(v)):.1f}%"


def pct_change(current, previous):
    if previous is None or pd.isna(previous) or previous == 0:
        return np.nan
    return (current - previous) / previous * 100.0


def selected_previous_month(df: pd.DataFrame, current_month) -> pd.Timestamp | None:
    months = sorted(pd.to_datetime(df["billing_month"].dropna().unique()))
    if not months:
        return None
    current_month = pd.to_datetime(current_month)
    previous_calendar = current_month - pd.DateOffset(months=1)
    previous_calendar = pd.Timestamp(previous_calendar.year, previous_calendar.month, 1)
    if previous_calendar in months:
        return previous_calendar
    prior = [m for m in months if m < current_month]
    return prior[-1] if prior else None


def _normalize_selection(values) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        values = [values]
    vals = [v for v in values if v and v != "All"]
    if not values or "All" in values:
        return []
    return vals


def filter_dimension(df: pd.DataFrame, states=None, properties=None, utilities=None, providers=None) -> pd.DataFrame:
    out = df.copy()
    states = _normalize_selection(states)
    properties = _normalize_selection(properties)
    utilities = _normalize_selection(utilities)
    providers = _normalize_selection(providers)
    if states:
        out = out[out["state"].isin(states)]
    if properties:
        out = out[out["property"].isin(properties)]
    if utilities:
        out = out[out["utility"].isin(utilities)]
    if providers and "provider" in out.columns:
        out = out[out["provider"].isin(providers)]
    return out


def utility_aggregate(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["billing_month", "property", "state", "utility", "amount", "usage", "treatments", "days_billed"])
    agg = (
        df.groupby(["billing_month", "state", "property", "utility"], dropna=False)
        .agg(
            amount=("amount", "sum"),
            usage=("usage", "sum"),
            treatments=("treatments", "max"),
            days_billed=("days_billed", "max"),
            provider=("provider", "first"),
            unit=("unit", "first"),
            usage_unit_label=("usage_unit_label", "first"),
            usage_scale=("usage_scale", "first"),
            city=("city", "first"),
            street=("street", "first"),
            zip=("zip", "first"),
            address=("address", "first"),
            latitude=("latitude", "first"),
            longitude=("longitude", "first"),
        )
        .reset_index()
    )
    agg["cost_per_usage"] = np.where(agg["usage"] > 0, agg["amount"] / agg["usage"] * agg["usage_scale"], np.nan)
    agg["cost_per_treatment"] = np.where(agg["treatments"] > 0, agg["amount"] / agg["treatments"], np.nan)
    agg["usage_per_treatment"] = np.where(agg["treatments"] > 0, agg["usage"] / agg["treatments"], np.nan)
    return agg


def portfolio_month_summary(df: pd.DataFrame, month) -> dict:
    d = df[df["billing_month"] == pd.to_datetime(month)] if month is not None else df.iloc[0:0]
    if d.empty:
        return {"amount": 0, "usage": 0, "treatments": 0, "cost_per_treatment": np.nan, "cost_per_usage": np.nan}
    amount = d["amount"].sum()
    usage = d["usage"].sum()
    treatments = d.groupby(["billing_month", "property"])["treatments"].max().sum()
    return {
        "amount": amount,
        "usage": usage,
        "treatments": treatments,
        "cost_per_treatment": amount / treatments if treatments else np.nan,
        "cost_per_usage": amount / usage if usage else np.nan,
    }


def selected_month_summary(df: pd.DataFrame, current_month, previous_month) -> dict:
    current = portfolio_month_summary(df, current_month)
    previous = portfolio_month_summary(df, previous_month) if previous_month is not None else portfolio_month_summary(df.iloc[0:0], current_month)
    return {
        "current": current,
        "previous": previous,
        "delta_amount": pct_change(current["amount"], previous["amount"]),
        "delta_usage": pct_change(current["usage"], previous["usage"]),
        "delta_treatments": pct_change(current["treatments"], previous["treatments"]),
        "delta_cpt": pct_change(current["cost_per_treatment"], previous["cost_per_treatment"]),
        "delta_cpu": pct_change(current["cost_per_usage"], previous["cost_per_usage"]),
    }


def utility_cost_per_usage_breakdown(df: pd.DataFrame, current_month, previous_month=None) -> pd.DataFrame:
    uagg = utility_aggregate(df)
    rows = []
    for utility, g in uagg.groupby("utility"):
        cur = g[g["billing_month"] == pd.to_datetime(current_month)]
        prev = g[g["billing_month"] == pd.to_datetime(previous_month)] if previous_month is not None else g.iloc[0:0]
        cur_amount, cur_usage = cur["amount"].sum(), cur["usage"].sum()
        prev_amount, prev_usage = prev["amount"].sum(), prev["usage"].sum()
        scale = cur["usage_scale"].dropna().iloc[0] if not cur.empty and cur["usage_scale"].notna().any() else 1
        unit = cur["usage_unit_label"].dropna().iloc[0] if not cur.empty and cur["usage_unit_label"].notna().any() else "usage unit"
        cur_cpu = cur_amount / cur_usage * scale if cur_usage else np.nan
        prev_cpu = prev_amount / prev_usage * scale if prev_usage else np.nan
        rows.append({
            "Utility": utility,
            "This Month": cur_cpu,
            "Previous Month": prev_cpu,
            "% Change": pct_change(cur_cpu, prev_cpu),
            "Unit": unit,
            "Current Cost": cur_amount,
            "Current Usage": cur_usage,
        })
    return pd.DataFrame(rows).sort_values("Utility") if rows else pd.DataFrame()


def monthly_trend(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    cost = df.groupby("billing_month", as_index=False)["amount"].sum()
    usage = df.groupby("billing_month", as_index=False)["usage"].sum()
    treatments = df.groupby(["billing_month", "property"], as_index=False)["treatments"].max().groupby("billing_month", as_index=False)["treatments"].sum()
    out = cost.merge(usage, on="billing_month", how="outer").merge(treatments, on="billing_month", how="outer").sort_values("billing_month")
    out["cost_per_treatment"] = np.where(out["treatments"] > 0, out["amount"] / out["treatments"], np.nan)
    out["month_label"] = out["billing_month"].dt.strftime("%b %Y")
    return out


def top_performers(df: pd.DataFrame, current_month, previous_month=None, n=5) -> pd.DataFrame:
    uagg = utility_aggregate(df)
    cur = uagg[uagg["billing_month"] == pd.to_datetime(current_month)]
    if cur.empty:
        return pd.DataFrame()
    cur_prop = cur.groupby(["property", "state"], as_index=False).agg(amount=("amount", "sum"), treatments=("treatments", "max"), usage=("usage", "sum"))
    cur_prop["Cost/Treatment"] = np.where(cur_prop["treatments"] > 0, cur_prop["amount"] / cur_prop["treatments"], np.nan)
    cur_prop["Usage/Treatment"] = np.where(cur_prop["treatments"] > 0, cur_prop["usage"] / cur_prop["treatments"], np.nan)
    if previous_month is not None:
        prev = uagg[uagg["billing_month"] == pd.to_datetime(previous_month)]
        prev_prop = prev.groupby(["property"], as_index=False).agg(prev_amount=("amount", "sum"), prev_treatments=("treatments", "max"))
        prev_prop["Prev Cost/Treatment"] = np.where(prev_prop["prev_treatments"] > 0, prev_prop["prev_amount"] / prev_prop["prev_treatments"], np.nan)
        cur_prop = cur_prop.merge(prev_prop[["property", "Prev Cost/Treatment"]], on="property", how="left")
        cur_prop["Improvement %"] = cur_prop.apply(lambda r: pct_change(r["Cost/Treatment"], r["Prev Cost/Treatment"]), axis=1)
    else:
        cur_prop["Prev Cost/Treatment"] = np.nan
        cur_prop["Improvement %"] = np.nan
    return cur_prop.sort_values("Cost/Treatment", na_position="last").head(n)
