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
    vals = sorted([
        str(v).strip()
        for v in series.dropna().unique().tolist()
        if str(v).strip() and str(v).strip().lower() not in {"unknown", "nan", "none"}
    ])
    return ["All"] + vals


def _clean_selection(selection):
    if not selection or "All" in selection:
        return []
    return [x for x in selection if x != "All"]


def _safe_default(key: str, options: list[str]) -> list[str]:
    """Keep multiselect widgets from crashing when dependent options change.

    Streamlit raises an exception if a multiselect default contains a value that
    is not currently in the option list. This happens when users select several
    properties and then change state/utility filters. This function keeps valid
    selections and falls back to All when none are valid.
    """
    existing = st.session_state.get(key, ["All"])
    if isinstance(existing, str):
        existing = [existing]
    if not existing or "All" in existing:
        return ["All"] if "All" in options else []
    valid = [x for x in existing if x in options]
    return valid if valid else (["All"] if "All" in options else [])


def _multiselect(label: str, options: list[str], key: str, help_text: str | None = None) -> list[str]:
    return st.multiselect(
        label,
        options,
        default=_safe_default(key, options),
        key=key,
        help=help_text,
    )


def _current_month_default_index(months_desc: list[pd.Timestamp]) -> int:
    """Choose the default report month.

    The dashboard should open on the current calendar month when that month exists
    in the sheet. If the current calendar month is not available yet, it opens on
    the newest month in the data. The month list is displayed newest-first so the
    most useful reporting month is always at the top of the filter.
    """
    if not months_desc:
        return 0
    today_month = pd.Timestamp.today().to_period("M").to_timestamp()
    for idx, month in enumerate(months_desc):
        if pd.to_datetime(month) == today_month:
            return idx
    return 0


def render_top_filters(df: pd.DataFrame, include_provider: bool = False, include_alert_level: bool = False) -> dict:
    months = available_months(df)

    # Always include the actual current calendar/report month, even if no bill
    # rows have been entered for that month yet. This lets the dashboard open on
    # June 2026 during June 2026 and properly surface missing current-month bills
    # instead of hiding the month until the first bill is added.
    today_month = pd.Timestamp.today().to_period("M").to_timestamp()
    month_set = {pd.to_datetime(m).to_period("M").to_timestamp() for m in months}
    month_set.add(today_month)

    if not month_set:
        st.error("No billing months were found in the data.")
        st.stop()

    # Show newest/current months first instead of burying them at the bottom.
    months_desc = sorted(list(month_set), reverse=True)
    labels = [pd.to_datetime(m).strftime("%B %Y") for m in months_desc]
    label_to_month = dict(zip(labels, months_desc))

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
            default_idx = _current_month_default_index(months_desc)
            # Use a new key so existing deployed sessions do not keep an older
            # month selection after this month-order fix is uploaded.
            selected_label = st.selectbox("Current month", labels, index=default_idx, key="filter_current_month_v3")
            current_month = pd.to_datetime(label_to_month[selected_label])
            previous_month = selected_previous_month(df, current_month)

        state_options = _options(df["state"])
        with cols[1]:
            state_selection = _multiselect("State", state_options, "filter_state")

        state_filtered = filter_dimension(df, states=state_selection)
        property_options = _options(state_filtered["property"])
        with cols[2]:
            property_selection = _multiselect("Property", property_options, "filter_property")

        prop_filtered = filter_dimension(state_filtered, properties=property_selection)
        utility_options = _options(prop_filtered["utility"])
        with cols[3]:
            utility_selection = _multiselect("Utility", utility_options, "filter_utility")

        col_index = 4
        provider_selection = ["All"]
        if include_provider:
            provider_filtered = filter_dimension(prop_filtered, utilities=utility_selection)
            provider_options = _options(provider_filtered["provider"])
            with cols[col_index]:
                provider_selection = _multiselect("Provider", provider_options, "filter_provider")
            col_index += 1

        alert_selection = ["All"]
        if include_alert_level:
            with cols[col_index]:
                alert_selection = _multiselect("Alert level", ["All", "Critical", "Review", "Info"], "filter_alert_level")
            col_index += 1

        with cols[col_index]:
            st.markdown("<div style='height:1.72rem'></div>", unsafe_allow_html=True)
            if st.button("Reset filters", use_container_width=True):
                for k in ["filter_state", "filter_property", "filter_utility", "filter_provider", "filter_alert_level"]:
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
