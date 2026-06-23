from __future__ import annotations

import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh

import config
from utils.auth import logout_button
from utils.calculations import filter_dimension, selected_previous_month
from utils.data_loader import available_months
from utils.theme import theme_toggle


def auto_refresh():
    seconds = int(getattr(config, "AUTO_REFRESH_SECONDS", 30))
    if seconds > 0:
        st_autorefresh(interval=seconds * 1000, key="live_sheet_refresh")


def render_sidebar_shell():
    st.sidebar.markdown("### IRC Utility Operations")
    st.sidebar.caption("Live Google Sheet dashboard")
    theme_toggle()
    st.sidebar.divider()
    st.sidebar.caption(f"Auto-refresh: every {getattr(config, 'AUTO_REFRESH_SECONDS', 30)} seconds")
    st.sidebar.caption("Data source: configured Google Sheet")
    st.sidebar.divider()
    logout_button()


def _options(series: pd.Series) -> list[str]:
    vals = sorted([str(v) for v in series.dropna().unique().tolist() if str(v).strip() and str(v).strip() != "Unknown"])
    return ["All"] + vals


def _selection_all(default_key: str):
    return st.session_state.get(default_key, ["All"])


def _clean_selection(selection):
    if not selection or "All" in selection:
        return []
    return selection


def render_top_filters(df: pd.DataFrame, include_provider: bool = False, include_alert_level: bool = False) -> dict:
    months = available_months(df)
    if not months:
        st.error("No billing months were found in the data.")
        st.stop()
    labels = [pd.to_datetime(m).strftime("%b %Y") for m in months]
    label_to_month = dict(zip(labels, months))

    with st.container(key="sticky_filters"):
        st.markdown('<div class="filter-title">Frozen filters</div>', unsafe_allow_html=True)
        base_cols = [1.0, 1.15, 1.7, 1.35]
        if include_provider:
            base_cols.append(1.45)
        if include_alert_level:
            base_cols.append(1.2)
        base_cols.append(0.85)
        cols = st.columns(base_cols)
        with cols[0]:
            default_idx = len(months) - 1
            selected_label = st.selectbox("Current month", labels, index=default_idx, key="filter_current_month")
            current_month = pd.to_datetime(label_to_month[selected_label])
            previous_month = selected_previous_month(df, current_month)
        with cols[1]:
            state_selection = st.multiselect("State", _options(df["state"]), default=_selection_all("filter_state"), key="filter_state")
        state_filtered = filter_dimension(df, states=state_selection)
        with cols[2]:
            property_selection = st.multiselect("Property", _options(state_filtered["property"]), default=_selection_all("filter_property"), key="filter_property")
        prop_filtered = filter_dimension(state_filtered, properties=property_selection)
        with cols[3]:
            utility_selection = st.multiselect("Utility", _options(prop_filtered["utility"]), default=_selection_all("filter_utility"), key="filter_utility")

        col_index = 4
        provider_selection = ["All"]
        if include_provider:
            provider_filtered = filter_dimension(prop_filtered, utilities=utility_selection)
            with cols[col_index]:
                provider_selection = st.multiselect("Provider", _options(provider_filtered["provider"]), default=_selection_all("filter_provider"), key="filter_provider")
            col_index += 1

        alert_selection = ["All"]
        if include_alert_level:
            with cols[col_index]:
                alert_selection = st.multiselect("Alert level", ["All", "Critical", "Review", "Info"], default=_selection_all("filter_alert_level"), key="filter_alert_level")
            col_index += 1

        with cols[col_index]:
            st.markdown("<div style='height:1.72rem'></div>", unsafe_allow_html=True)
            if st.button("Reset filters", use_container_width=True):
                for k in ["filter_state", "filter_property", "filter_utility", "filter_provider", "filter_alert_level"]:
                    if k in st.session_state:
                        st.session_state[k] = ["All"]
                st.rerun()

        filtered = filter_dimension(df, states=state_selection, properties=property_selection, utilities=utility_selection, providers=provider_selection)
        st.caption(
            f"Current: {current_month.strftime('%b %Y')} | Previous: {previous_month.strftime('%b %Y') if previous_month is not None else 'None found'} | "
            f"Showing {filtered['property'].nunique():,} properties and {filtered['utility'].nunique():,} utilities"
        )

    return {
        "current_month": current_month,
        "previous_month": previous_month,
        "states": state_selection,
        "properties": property_selection,
        "utilities": utility_selection,
        "providers": provider_selection,
        "alert_levels": alert_selection,
        "filtered": filtered,
        "selected_state_values": _clean_selection(state_selection),
        "selected_property_values": _clean_selection(property_selection),
        "selected_utility_values": _clean_selection(utility_selection),
        "selected_provider_values": _clean_selection(provider_selection),
        "selected_alert_values": _clean_selection(alert_selection),
    }


def render_page_setup(df: pd.DataFrame, include_provider: bool = False, include_alert_level: bool = False) -> dict:
    auto_refresh()
    render_sidebar_shell()
    return render_top_filters(df, include_provider=include_provider, include_alert_level=include_alert_level)
