import html

import pandas as pd
import streamlit as st

from utils.auth import require_auth
from utils.app_state import render_page_setup
from utils.alerts import alert_counts, build_alerts
from utils.calculations import fmt_money, fmt_num, selected_month_summary, top_performers, utility_cost_per_usage_breakdown
from utils.data_loader import load_data
from utils.reporting import generate_monthly_pdf, monthly_takeaways, recommended_followups
from utils.theme import apply_theme, alert_cards, compact_table, kpi_card, page_header, panel_start, panel_end, delta_html

st.set_page_config(page_title="Monthly Summary Report", page_icon="📄", layout="wide")
require_auth()
apply_theme()

try:
    df = load_data()
except Exception as e:
    st.error(f"Could not load data: {e}")
    st.stop()

page_header("Monthly Summary Report", "One-page overview for leadership with PDF export. No raw data export included.")
filters = render_page_setup(df)
fdf = filters["filtered"]
current_month = filters["current_month"]
previous_month = filters["previous_month"]

summary = selected_month_summary(fdf, current_month, previous_month)
alerts = build_alerts(fdf, current_month, previous_month)
counts = alert_counts(alerts)

cols = st.columns(5)
with cols[0]:
    kpi_card("Total Cost", fmt_money(summary["current"]["amount"]), fmt_money(summary["previous"]["amount"]), summary["delta_amount"], delta_direction="treatment_adjusted", reference_delta=summary["delta_treatments"])
with cols[1]:
    kpi_card("Cost / Treatment", fmt_money(summary["current"]["cost_per_treatment"], 2), fmt_money(summary["previous"]["cost_per_treatment"], 2), summary["delta_cpt"], delta_direction="lower_is_better")
with cols[2]:
    kpi_card("Usage", fmt_num(summary["current"]["usage"]), fmt_num(summary["previous"]["usage"]), summary["delta_usage"], delta_direction="treatment_adjusted", reference_delta=summary["delta_treatments"])
with cols[3]:
    kpi_card("Treatments", fmt_num(summary["current"]["treatments"]), fmt_num(summary["previous"]["treatments"]), summary["delta_treatments"], delta_direction="higher_is_better")
with cols[4]:
    kpi_card("Anomalies", str(counts["Total"]), f"{counts['Critical']} Critical", None, f"{counts['Review']} Review")

panel_start("Export Report", "Downloads a clean one-page landscape PDF for emailing a monthly overview.")
pdf_bytes = generate_monthly_pdf(fdf, current_month, previous_month)
st.download_button(
    "Export Monthly Report PDF",
    data=pdf_bytes,
    file_name=f"utility-summary-{current_month.strftime('%Y-%m')}.pdf",
    mime="application/pdf",
    use_container_width=True,
)
panel_end()

left, right = st.columns([1.1, 1])
with left:
    panel_start("Key Monthly Takeaways", "Automatically generated from cost, usage, treatment, and alert movement.")
    for item in monthly_takeaways(fdf, current_month, previous_month, alerts):
        st.markdown(f'<div class="insight-box">{html.escape(str(item))}</div>', unsafe_allow_html=True)
    panel_end()

with right:
    panel_start("Recommended Follow-Up", "Action-focused summary for analyst or management review.")
    for item in recommended_followups(alerts):
        st.markdown(f'<div class="insight-box">{html.escape(str(item))}</div>', unsafe_allow_html=True)
    panel_end()

panel_start("Top Anomalies", "Highest-priority flags for the selected month.")
alert_cards(alerts, max_cards=5)
panel_end()

col_a, col_b = st.columns(2)
with col_a:
    panel_start("Top Performing Properties", "Lowest cost per treatment in the selected filtered view.")
    performers = top_performers(fdf, current_month, previous_month, n=7)
    if not performers.empty:
        display = performers.rename(columns={"property": "Property", "state": "State"}).copy()
        display["Cost/Treatment"] = display["Cost/Treatment"].apply(lambda x: fmt_money(x, 2))
        display["Prev Cost/Treatment"] = display["Prev Cost/Treatment"].apply(lambda x: fmt_money(x, 2))
        display["Improvement %"] = display["Improvement %"].apply(lambda x: delta_html(x, direction="lower_is_better"))
        compact_table(display, ["Property", "State", "Cost/Treatment", "Prev Cost/Treatment", "Improvement %"], max_rows=7)
    else:
        st.info("No performer data available.")
    panel_end()

with col_b:
    panel_start("Utility Breakdown", "Cost per usage by utility, keeping units separate.")
    util = utility_cost_per_usage_breakdown(fdf, current_month, previous_month)
    if not util.empty:
        u = util.copy()
        u["This Month"] = u["This Month"].apply(lambda x: fmt_money(x, 4))
        u["Previous Month"] = u["Previous Month"].apply(lambda x: fmt_money(x, 4))
        u["% Change"] = u["% Change"].apply(lambda x: delta_html(x, direction="lower_is_better"))
        u["Current Cost"] = u["Current Cost"].apply(lambda x: fmt_money(x))
        compact_table(u, ["Utility", "This Month", "Previous Month", "% Change", "Unit", "Current Cost"], max_rows=8)
    else:
        st.info("No utility breakdown available.")
    panel_end()
