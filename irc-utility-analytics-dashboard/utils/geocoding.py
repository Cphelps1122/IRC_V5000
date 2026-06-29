from __future__ import annotations

import os
import re
import time

import numpy as np
import pandas as pd
import requests
import streamlit as st

import config

CACHE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "geocode_cache_v11_exact.csv")


def _read_cache() -> pd.DataFrame:
    if os.path.exists(CACHE_PATH):
        try:
            return pd.read_csv(CACHE_PATH)
        except Exception:
            pass
    return pd.DataFrame(columns=["address", "lat", "lon", "source"])


def _write_cache(cache: pd.DataFrame):
    try:
        os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
        cache.dropna(subset=["address"]).drop_duplicates("address").to_csv(CACHE_PATH, index=False)
    except Exception:
        pass


def _clean_address(address: str) -> str:
    address = re.sub(r"\s+", " ", str(address or "")).strip(" ,")
    bad = {"unknown", "nan", "none", "", "unknown, unknown", "unknown, unknown, unknown"}
    return "" if address.lower() in bad else address


def _geocode_address(address: str):
    if not getattr(config, "GEOCODE_ADDRESSES", True) or not address:
        return None, None
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": address, "format": "json", "limit": 1, "countrycodes": "us", "addressdetails": 0},
            headers={"User-Agent": "irc-utility-analytics-dashboard-v11/1.0"},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception:
        return None, None
    return None, None


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def prepare_property_coordinates(properties: pd.DataFrame) -> pd.DataFrame:
    """Return property rows with exact lat/lon when possible.

    V11 does NOT place failed geocodes at state centers or random offsets. Wrong
    dots are worse than missing dots. If Latitude/Longitude exist in the sheet,
    those exact values are used. Otherwise the app geocodes the full street
    address and caches only successful address-level coordinates. Unmapped rows
    remain in the table with lat/lon blank so the page can list them separately.
    """
    if properties.empty:
        return properties

    rows = properties.copy()
    rows["lat"] = pd.to_numeric(rows.get("latitude"), errors="coerce")
    rows["lon"] = pd.to_numeric(rows.get("longitude"), errors="coerce")
    rows["Geocode Status"] = np.where(rows["lat"].notna() & rows["lon"].notna(), "Sheet coordinates", "Unmapped")

    cache = _read_cache()
    cache_map = {
        str(r["address"]): (r["lat"], r["lon"], r.get("source", "Address geocode"))
        for _, r in cache.dropna(subset=["address", "lat", "lon"]).iterrows()
    }
    new_cache_rows = []
    geocoded_this_run = 0
    max_geo = int(getattr(config, "MAX_GEOCODES_PER_RUN", 250))

    for idx, r in rows.iterrows():
        if pd.notna(r.get("lat")) and pd.notna(r.get("lon")):
            continue

        address = _clean_address(r.get("Address", r.get("address", "")))
        if not address:
            street = r.get("Street", r.get("street", ""))
            city = r.get("City", r.get("city", ""))
            state = r.get("State", r.get("state", ""))
            zip_code = r.get("Zip", r.get("zip", ""))
            address = _clean_address(", ".join([str(x).strip() for x in [street, city, state, zip_code] if str(x).strip() and str(x).strip().lower() not in {"unknown", "nan", "none"}]))

        if address in cache_map:
            lat, lon, src = cache_map[address]
            rows.at[idx, "lat"] = float(lat)
            rows.at[idx, "lon"] = float(lon)
            rows.at[idx, "Geocode Status"] = src or "Address geocode"
            continue

        if address and geocoded_this_run < max_geo:
            lat, lon = _geocode_address(address)
            geocoded_this_run += 1
            if lat is not None and lon is not None:
                rows.at[idx, "lat"] = lat
                rows.at[idx, "lon"] = lon
                rows.at[idx, "Geocode Status"] = "Address geocode"
                new_cache_rows.append({"address": address, "lat": lat, "lon": lon, "source": "Address geocode"})
                time.sleep(0.12)

    if new_cache_rows:
        cache = pd.concat([cache, pd.DataFrame(new_cache_rows)], ignore_index=True)
        _write_cache(cache)
    return rows
