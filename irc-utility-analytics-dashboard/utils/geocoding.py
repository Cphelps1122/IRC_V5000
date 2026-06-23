from __future__ import annotations

import hashlib
import os
import time

import numpy as np
import pandas as pd
import requests
import streamlit as st

import config

CACHE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "geocode_cache.csv")

STATE_CENTERS = {
    "AL": (32.806671, -86.791130), "AK": (61.370716, -152.404419), "AZ": (33.729759, -111.431221),
    "AR": (34.969704, -92.373123), "CA": (36.116203, -119.681564), "CO": (39.059811, -105.311104),
    "CT": (41.597782, -72.755371), "DE": (39.318523, -75.507141), "FL": (27.766279, -81.686783),
    "GA": (33.040619, -83.643074), "HI": (21.094318, -157.498337), "ID": (44.240459, -114.478828),
    "IL": (40.349457, -88.986137), "IN": (39.849426, -86.258278), "IA": (42.011539, -93.210526),
    "KS": (38.526600, -96.726486), "KY": (37.668140, -84.670067), "LA": (31.169546, -91.867805),
    "ME": (44.693947, -69.381927), "MD": (39.063946, -76.802101), "MA": (42.230171, -71.530106),
    "MI": (43.326618, -84.536095), "MN": (45.694454, -93.900192), "MS": (32.741646, -89.678696),
    "MO": (38.456085, -92.288368), "MT": (46.921925, -110.454353), "NE": (41.125370, -98.268082),
    "NV": (38.313515, -117.055374), "NH": (43.452492, -71.563896), "NJ": (40.298904, -74.521011),
    "NM": (34.840515, -106.248482), "NY": (42.165726, -74.948051), "NC": (35.630066, -79.806419),
    "ND": (47.528912, -99.784012), "OH": (40.388783, -82.764915), "OK": (35.565342, -96.928917),
    "OR": (44.572021, -122.070938), "PA": (40.590752, -77.209755), "RI": (41.680893, -71.511780),
    "SC": (33.856892, -80.945007), "SD": (44.299782, -99.438828), "TN": (35.747845, -86.692345),
    "TX": (31.054487, -97.563461), "UT": (40.150032, -111.862434), "VT": (44.045876, -72.710686),
    "VA": (37.769337, -78.169968), "WA": (47.400902, -121.490494), "WV": (38.491226, -80.954453),
    "WI": (44.268543, -89.616508), "WY": (42.755966, -107.302490), "DC": (38.897438, -77.026817),
}


def _read_cache() -> pd.DataFrame:
    if os.path.exists(CACHE_PATH):
        try:
            return pd.read_csv(CACHE_PATH)
        except Exception:
            pass
    return pd.DataFrame(columns=["address", "lat", "lon"])


def _write_cache(cache: pd.DataFrame):
    try:
        os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
        cache.drop_duplicates("address").to_csv(CACHE_PATH, index=False)
    except Exception:
        pass


def _fallback_coordinate(state: str, property_name: str):
    base = STATE_CENTERS.get(str(state).upper(), (39.5, -98.35))
    digest = hashlib.md5(str(property_name).encode("utf-8")).hexdigest()
    a = int(digest[:4], 16) / 65535
    b = int(digest[4:8], 16) / 65535
    # Small deterministic offset so dots in the same state do not overlap perfectly.
    lat = base[0] + (a - 0.5) * 1.6
    lon = base[1] + (b - 0.5) * 2.2
    return lat, lon


def _geocode_address(address: str):
    if not getattr(config, "GEOCODE_ADDRESSES", True) or not address:
        return None, None
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": address, "format": "json", "limit": 1, "countrycodes": "us"},
            headers={"User-Agent": "irc-utility-analytics-dashboard/1.0"},
            timeout=8,
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
    """Return property rows with lat/lon.

    Uses existing latitude/longitude columns if available. Otherwise attempts
    address geocoding and caches results. If geocoding does not return a result,
    a state-level fallback dot is used so every property remains visible.
    """
    if properties.empty:
        return properties
    rows = properties.copy()
    rows["lat"] = pd.to_numeric(rows.get("latitude"), errors="coerce")
    rows["lon"] = pd.to_numeric(rows.get("longitude"), errors="coerce")

    cache = _read_cache()
    cache_map = {str(r["address"]): (r["lat"], r["lon"]) for _, r in cache.dropna(subset=["address"]).iterrows()}
    new_cache_rows = []
    geocoded_this_run = 0
    max_geo = int(getattr(config, "MAX_GEOCODES_PER_RUN", 250))

    for idx, r in rows.iterrows():
        if pd.notna(r.get("lat")) and pd.notna(r.get("lon")):
            continue
        address = str(r.get("Address", r.get("address", ""))).strip()
        if address in cache_map and pd.notna(cache_map[address][0]) and pd.notna(cache_map[address][1]):
            rows.at[idx, "lat"] = float(cache_map[address][0])
            rows.at[idx, "lon"] = float(cache_map[address][1])
            continue
        lat = lon = None
        if address and geocoded_this_run < max_geo:
            lat, lon = _geocode_address(address)
            geocoded_this_run += 1
            if lat is not None and lon is not None:
                new_cache_rows.append({"address": address, "lat": lat, "lon": lon})
                # Be gentle with the public geocoder.
                time.sleep(0.05)
        if lat is None or lon is None:
            lat, lon = _fallback_coordinate(r.get("State", r.get("state", "")), r.get("Property", r.get("property", "")))
        rows.at[idx, "lat"] = lat
        rows.at[idx, "lon"] = lon

    if new_cache_rows:
        cache = pd.concat([cache, pd.DataFrame(new_cache_rows)], ignore_index=True)
        _write_cache(cache)
    return rows
