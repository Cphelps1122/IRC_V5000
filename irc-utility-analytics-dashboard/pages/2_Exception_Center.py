import pandas as pd
import streamlit as st

from utils.auth import require_auth
from utils.app_state import render_page_setup
from utils.alerts import alert_counts, build_alerts
from utils.calculations import fmt_money
from utils.data_loader import load_data
from utils.theme import apply_theme, alert_cards, kpi_card, page_header, panel_start, panel_end

st.set_page_config(page_title="Exception Center", page_icon="🚨", layout="wide")
require_auth()
apply_theme()

try:
    df = load_data()
except Exception as e:
    st.error(f"Could not load data: {e}")
    st.stop()

page_header("Exception Center", "Professional anomaly queue. No raw spreadsheet table or horizontal scrolling.")
filters = render_page_setup(df, include_alert_level=True)
fdf = filters["filtered"]
current_month = filters["current_month"]
previous_month = filters["previous_month"]
selected_alerts = filters["selected_alert_values"]

alerts = build_alerts(fdf, current_month, previous_month)
if selected_alerts:
    alerts = alerts[alerts["Severity"].isin(selected_alerts)]
counts = alert_counts(alerts)

cols = st.columns(4)
with cols[0]:
    kpi_card("Critical", str(counts["Critical"]), "Needs review", None)
with cols[1]:
    kpi_card("Review", str(counts["Review"]), "Watch list", None)
with cols[2]:
    total_impact = alerts["Estimated Monthly Impact"].sum() if not alerts.empty else 0
    kpi_card("Est. Impact", fmt_money(total_impact), "Current flags", None)
with cols[3]:
    kpi_card("Total Flags", str(counts["Total"]), "Visible queue", None)

panel_start("Anomaly Queue", "Each card shows the issue, explanation, and key month-over-month metrics without forcing horizontal scrolling.")
alert_cards(alerts, max_cards=30)
panel_end()
