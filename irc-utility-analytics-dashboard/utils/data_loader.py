from __future__ import annotations

from io import StringIO, BytesIO
import re
import datetime as dt

import numpy as np
import pandas as pd
import requests
import streamlit as st

import config


def _secret_or_config(name: str, default=""):
    try:
        val = st.secrets.get(name, None)
    except Exception:
        val = None
    if val in (None, ""):
        return getattr(config, name, default)
    return val


def parse_sheet_id(url: str) -> str:
    if not url:
        return ""
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", url)
    return m.group(1) if m else ""


def parse_gid(url: str) -> str:
    if not url:
        return ""
    m = re.search(r"gid=([0-9]+)", url)
    return m.group(1) if m else "0"


@st.cache_data(ttl=30, show_spinner=False)
def load_google_sheet_cached(sheet_id: str, gid: str, cache_buster: str) -> pd.DataFrame:
    urls = [
        f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}",
        f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&gid={gid}",
    ]
    last_error = None
    headers = {"User-Agent": "Mozilla/5.0"}
    for url in urls:
        try:
            r = requests.get(url, headers=headers, timeout=20)
            r.raise_for_status()
            text = r.text
            if "<!DOCTYPE html" in text[:250] or "<html" in text[:300].lower():
                raise ValueError("Google returned HTML instead of CSV. Check that the sheet is viewable by link.")
            return pd.read_csv(StringIO(text))
        except Exception as e:
            last_error = e

    try:
        xlsx_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
        r = requests.get(xlsx_url, headers=headers, timeout=25)
        r.raise_for_status()
        return pd.read_excel(BytesIO(r.content), sheet_name=getattr(config, "GOOGLE_WORKSHEET", 0))
    except Exception as e:
        last_error = e
    raise RuntimeError(f"Could not load Google Sheet. Last error: {last_error}")


def load_raw_data() -> pd.DataFrame:
    sheet_url = _secret_or_config("GOOGLE_SHEET_URL", "")
    sheet_id = _secret_or_config("GOOGLE_SHEET_ID", "") or parse_sheet_id(sheet_url)
    gid = str(_secret_or_config("GOOGLE_SHEET_GID", "") or parse_gid(sheet_url) or "0")
    if not sheet_id:
        raise RuntimeError("No Google Sheet is configured. Add GOOGLE_SHEET_URL or GOOGLE_SHEET_ID in config.py or Streamlit Secrets.")
    return load_google_sheet_cached(sheet_id, gid, dt.datetime.utcnow().strftime("%Y%m%d%H%M"))


def _find_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    normalized = {str(c).strip().lower(): c for c in df.columns}
    for cand in candidates:
        key = cand.strip().lower()
        if key in normalized:
            return normalized[key]
    for c in df.columns:
        c_low = str(c).strip().lower()
        for cand in candidates:
            if cand.strip().lower() in c_low:
                return c
    return None


def to_number(s: pd.Series) -> pd.Series:
    return pd.to_numeric(
        s.astype(str)
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.replace("--", "", regex=False)
        .str.strip(),
        errors="coerce",
    )



US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL", "IN", "IA",
    "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT",
    "VA", "WA", "WV", "WI", "WY", "DC"
}


def _clean_location_fields(out: pd.DataFrame) -> pd.DataFrame:
    """Fix common sheet-entry location issues before mapping/filtering.

    Some rows have City values like "Augusta GA" while the State cell is blank.
    Without this cleanup the dashboard shows UNKNOWN as a state and the map/table
    counts become confusing.
    """
    out["city"] = out["city"].fillna("Unknown").astype(str).str.strip()
    out["state"] = out["state"].fillna("Unknown").astype(str).str.upper().str.strip()
    bad_state = out["state"].isin(["", "NAN", "NONE", "UNKNOWN"])

    # If city ends with a two-letter state abbreviation, split it out.
    city_extract = out["city"].str.extract(r"^(?P<city>.*?)[,\s]+(?P<state>[A-Za-z]{2})$")
    can_fix = bad_state & city_extract["state"].str.upper().isin(US_STATES)
    out.loc[can_fix, "state"] = city_extract.loc[can_fix, "state"].str.upper()
    out.loc[can_fix, "city"] = city_extract.loc[can_fix, "city"].str.strip()

    out.loc[out["state"].isin(["", "NAN", "NONE", "UNKNOWN"]), "state"] = "Unknown"
    out.loc[out["city"].isin(["", "nan", "None", "UNKNOWN"]), "city"] = "Unknown"
    return out


def _format_us_date(value) -> str:
    if value is None or pd.isna(value):
        return "—"
    d = pd.to_datetime(value, errors="coerce")
    if pd.isna(d):
        return "—"
    return f"{d.month}/{d.day}/{d.year}"


def normalize_data(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    df.columns = [str(c).strip() for c in df.columns]
    colmap = {
        "property": _find_col(df, ["Property Name", "Property", "Facility", "Center"]),
        "provider": _find_col(df, ["Provider", "Vendor", "Utility Provider"]),
        "street": _find_col(df, ["Street", "Address"]),
        "city": _find_col(df, ["City"]),
        "state": _find_col(df, ["State"]),
        "zip": _find_col(df, ["Zip Code", "Zip"]),
        "latitude": _find_col(df, ["Latitude", "Lat"]),
        "longitude": _find_col(df, ["Longitude", "Long", "Lng"]),
        "treatments": _find_col(df, ["# Treatments", "Treatments", "Treatment Count"]),
        "utility": _find_col(df, ["Utility", "Utility Type"]),
        "meter": _find_col(df, ["Meter #", "Meter", "Meter Number"]),
        "unit": _find_col(df, ["Unit of Measure", "UOM", "Unit"]),
        "account": _find_col(df, ["Acct Number", "Account", "Account Number"]),
        "billing_date": _find_col(df, ["Billing Date", "Bill Date"]),
        "month": _find_col(df, ["Month"]),
        "year": _find_col(df, ["Year"]),
        "billing_period": _find_col(df, ["Billing Period"]),
        "days_billed": _find_col(df, ["Number Days Billed", "Days Billed"]),
        "due_date": _find_col(df, ["Due Date"]),
        "usage": _find_col(df, ["Usage", "Consumption"]),
        "amount": _find_col(df, ["$ Amount", "Amount", "Cost", "Total Cost"]),
    }

    out = pd.DataFrame()
    for key, col in colmap.items():
        out[key] = df[col] if col is not None else np.nan

    for c in ["property", "provider", "street", "city", "state", "utility", "unit", "meter", "account"]:
        out[c] = out[c].fillna("Unknown").astype(str).str.strip()
        out.loc[out[c].isin(["", "nan", "None"]), c] = "Unknown"

    out = _clean_location_fields(out)
    out["zip"] = out["zip"].fillna("").astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
    out["amount"] = to_number(out["amount"]).fillna(0)
    out["usage"] = to_number(out["usage"]).fillna(0)
    out["treatments"] = to_number(out["treatments"]).fillna(0)
    out["days_billed"] = to_number(out["days_billed"]).fillna(0)
    out["latitude"] = to_number(out["latitude"])
    out["longitude"] = to_number(out["longitude"])
    out["billing_date"] = pd.to_datetime(out["billing_date"], errors="coerce")
    out["due_date"] = pd.to_datetime(out["due_date"], errors="coerce")

    # Prefer the service/reporting Month + Year columns when available.
    # The billing date can fall in the following calendar month, so using bill date
    # would make monthly comparisons and missing-bill checks misleading.
    service_month = _month_year_to_timestamp(out.get("month"), out.get("year"))
    bill_month = out["billing_date"].dt.to_period("M").dt.to_timestamp()
    out["billing_month"] = service_month.fillna(bill_month)
    out = out.dropna(subset=["billing_month"])

    out["month_label"] = out["billing_month"].dt.strftime("%b %Y")
    out["utility"] = out["utility"].str.title().replace({"Elec": "Electric", "Electricity": "Electric", "Nat Gas": "Gas", "Natural Gas": "Gas"})
    out["usage_scale"] = out.apply(lambda r: usage_scale(r.get("utility", ""), r.get("unit", "")), axis=1)
    out["usage_unit_label"] = out.apply(lambda r: usage_unit_label(r.get("utility", ""), r.get("unit", "")), axis=1)
    out["cost_per_usage"] = np.where(out["usage"] > 0, out["amount"] / out["usage"] * out["usage_scale"], np.nan)
    out["address"] = out.apply(_full_address, axis=1)
    return out


def _month_year_to_timestamp(month_s: pd.Series, year_s: pd.Series) -> pd.Series:
    month_num = pd.to_numeric(month_s, errors="coerce")
    month_names = pd.to_datetime(month_s.astype(str).str[:3], format="%b", errors="coerce").dt.month
    month_num = month_num.fillna(month_names)
    year_num = pd.to_numeric(year_s, errors="coerce")
    valid = month_num.notna() & year_num.notna()
    result = pd.Series(pd.NaT, index=month_s.index, dtype="datetime64[ns]")
    if valid.any():
        result.loc[valid] = pd.to_datetime(
            dict(year=year_num.loc[valid].astype(int), month=month_num.loc[valid].astype(int), day=1),
            errors="coerce",
        )
    return result


def _full_address(r) -> str:
    parts = [r.get("street", ""), r.get("city", ""), r.get("state", ""), str(r.get("zip", ""))]
    return ", ".join([str(p).strip() for p in parts if str(p).strip() and str(p).strip() != "Unknown"])


def load_data() -> pd.DataFrame:
    raw = load_raw_data()
    return normalize_data(raw)


def usage_scale(utility: str, unit: str = "") -> float:
    u = str(utility).lower()
    unit_l = str(unit).lower()
    if "water" in u or "sewer" in u or "gal" in unit_l:
        return 1000.0
    return 1.0


def usage_unit_label(utility: str, unit: str = "") -> str:
    u = str(utility).lower()
    unit_clean = str(unit).strip()
    if "electric" in u or "kwh" in unit_clean.lower():
        return "kWh"
    if "water" in u:
        return "1,000 gal"
    if "sewer" in u:
        return "1,000 gal"
    if "gas" in u or "therm" in unit_clean.lower():
        return "therm"
    if "trash" in u or "waste" in u:
        return "unit"
    return unit_clean if unit_clean and unit_clean != "Unknown" else "usage unit"


def available_months(df: pd.DataFrame) -> list[pd.Timestamp]:
    return sorted(pd.to_datetime(df["billing_month"].dropna().unique()))
