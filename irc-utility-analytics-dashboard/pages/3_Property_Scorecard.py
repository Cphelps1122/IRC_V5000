import pandas as pd
import streamlit as st

from utils.auth import require_auth
from utils.app_state import render_page_setup
from utils.alerts import build_alerts
from utils.calculations import fmt_money, fmt_num, monthly_trend, selected_month_summary, utility_aggregate
from utils.charts import line_chart, bar_chart
from utils.data_loader import load_data
from utils.theme import apply_theme, alert_cards, compact_table, kpi_card, page_header, panel_start, panel_end

st.set_page_config(page_title="Property Scorecard", page_icon="🏥", layout="wide")
require_auth()
apply_theme()

try:
    df = load_data()
except Exception as e:
    st.error(f"Could not load data: {e}")
    st.stop()

page_header("Property Scorecard", "Property-level investigation with KPIs, trend context, and condensed billing history.")
filters = render_page_setup(df)
fdf = filters["filtered"]
current_month = filters["current_month"]
previous_month = filters["previous_month"]

properties = sorted(fdf["property"].dropna().unique().tolist())
if not properties:
    st.info("No properties match the selected filters.")
    st.stop()

# A scorecard needs one focus property, while the global filter can still select many.
selected_property = st.selectbox("Scorecard property", properties, index=0, help="The main filters can select multiple properties. Choose one here for the detailed scorecard.")
prop_df = fdf[fdf["property"] == selected_property].copy()

page_header(selected_property, f"Focused scorecard for {current_month.strftime('%b %Y')}")
summary = selected_month_summary(prop_df, current_month, previous_month)
alerts = build_alerts(prop_df, current_month, previous_month)

cols = st.columns(5)
with cols[0]:
    kpi_card("Current Cost", fmt_money(summary["current"]["amount"]), fmt_money(summary["previous"]["amount"]), summary["delta_amount"], delta_direction="treatment_adjusted", reference_delta=summary["delta_treatments"])
with cols[1]:
    kpi_card("Cost / Treatment", fmt_money(summary["current"]["cost_per_treatment"], 2), fmt_money(summary["previous"]["cost_per_treatment"], 2), summary["delta_cpt"], delta_direction="lower_is_better")
with cols[2]:
    kpi_card("Cost / Usage", fmt_money(summary["current"]["cost_per_usage"], 4), fmt_money(summary["previous"]["cost_per_usage"], 4), summary["delta_cpu"], delta_direction="lower_is_better")
with cols[3]:
    kpi_card("Usage", fmt_num(summary["current"]["usage"]), fmt_num(summary["previous"]["usage"]), summary["delta_usage"], delta_direction="treatment_adjusted", reference_delta=summary["delta_treatments"])
with cols[4]:
    kpi_card("Treatments", fmt_num(summary["current"]["treatments"]), fmt_num(summary["previous"]["treatments"]), summary["delta_treatments"], delta_direction="higher_is_better")

left, right = st.columns([1.45, 1])
with left:
    panel_start("Monthly Trends", "Cost and cost per treatment across available billing months.")
    trend = monthly_trend(prop_df)
    if not trend.empty:
        fig = line_chart(trend, "month_label", ["amount", "cost_per_treatment"], "Cost and Cost per Treatment", height=370)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No property trend data available.")
    panel_end()

with right:
    panel_start("Automatic Explanation", "Rule-based notes from current month compared with the prior month.")
    alert_cards(alerts, max_cards=4)
    panel_end()

bottom_left, bottom_right = st.columns([1, 1])
with bottom_left:
    panel_start("Utility Cost Mix", "Current month spend split by utility.")
    cur = prop_df[prop_df["billing_month"] == current_month]
    mix = cur.groupby("utility", as_index=False)["amount"].sum().sort_values("amount", ascending=False)
    if not mix.empty:
        fig = bar_chart(mix, "utility", "amount", title="Current Month Cost", height=320)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No current month utility mix available.")
    panel_end()

with bottom_right:
    panel_start("Condensed Billing History", "Decision-making summary only; not a raw spreadsheet explorer.")
    hist = utility_aggregate(prop_df).sort_values("billing_month", ascending=False)
    if not hist.empty:
        table = hist[["billing_month", "utility", "amount", "usage", "treatments", "cost_per_treatment", "cost_per_usage", "days_billed"]].copy()
        table["Month"] = table["billing_month"].dt.strftime("%b %Y")
        table["Utility"] = table["utility"]
        table["Cost"] = table["amount"].apply(lambda x: fmt_money(x))
        table["Usage"] = table["usage"].apply(lambda x: fmt_num(x))
        table["Treatments"] = table["treatments"].apply(lambda x: fmt_num(x))
        table["Cost/Treatment"] = table["cost_per_treatment"].apply(lambda x: fmt_money(x, 2))
        table["Cost/Usage"] = table["cost_per_usage"].apply(lambda x: fmt_money(x, 4))
        table["Days Billed"] = table["days_billed"].apply(lambda x: fmt_num(x))
        compact_table(table, ["Month", "Utility", "Cost", "Usage", "Treatments", "Cost/Treatment", "Cost/Usage", "Days Billed"], max_rows=10)
    else:
        st.info("No billing history available.")
    panel_end()
