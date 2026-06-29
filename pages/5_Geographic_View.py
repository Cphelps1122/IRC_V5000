from __future__ import annotations
import streamlit as st
from utils.ui import apply_css, metric_card
from utils.calculations import monthly_summary, filter_df, money_fmt, num_fmt
from utils.alerts import build_alerts
from utils.charts import state_choropleth, line
from utils.app_state import load_current_data

st.set_page_config(page_title="Geographic View", page_icon="🗺️", layout="wide")
apply_css()
st.title("5. Geographic View")
st.caption("Visualize performance and alerts across your dialysis center portfolio")
df, monthly, alerts = load_current_data()
utils = ["All"] + sorted(df["Utility"].dropna().unique().tolist())
months = sorted(monthly["Bill Month"].dropna().unique())
c1,c2,c3 = st.columns(3)
metric = c1.selectbox("Map Metric", ["Cost_per_Treatment", "Usage_per_Treatment", "Total_Cost", "Total_Usage"])
utility = c2.multiselect("Utility", utils, default=["All"])
date = c3.selectbox("Month", months, index=len(months)-1 if months else 0, format_func=lambda x: x.strftime('%b %Y') if hasattr(x,'strftime') else str(x))
view = filter_df(monthly, None, None, utility, [date, date])

c1,c2,c3,c4,c5 = st.columns(5)
with c1: metric_card("Total Centers", str(view["Property Name"].nunique()))
with c2: metric_card("Total Monthly Cost", money_fmt(view["Total_Cost"].sum()))
with c3: metric_card("Total Monthly Usage", num_fmt(view["Total_Usage"].sum()))
with c4: metric_card("Avg Cost/Treatment", f"${view['Cost_per_Treatment'].mean():,.2f}" if len(view) else "—")
with c5: metric_card("Critical Alerts", str((filter_df(alerts,None,None,utility,[date,date])["Alert Level"]=="Critical").sum()))

left,right = st.columns([2,1])
with left:
    st.plotly_chart(state_choropleth(view, metric), use_container_width=True)
with right:
    st.subheader("State Summary")
    state_summary = view.groupby("State", as_index=False).agg(Centers=("Property Name","nunique"), Total_Cost=("Total_Cost","sum"), Cost_per_Treatment=("Cost_per_Treatment","mean"))
    st.dataframe(state_summary.sort_values("Total_Cost", ascending=False), use_container_width=True, hide_index=True)
    selected_state = st.selectbox("Drill Down State", sorted(view["State"].dropna().unique())) if len(view) else None
    if selected_state:
        st.markdown(f"### {selected_state} Centers")
        st.dataframe(view[view["State"]==selected_state].sort_values("Cost_per_Treatment", ascending=False)[["Property Name","Utility","Total_Cost","Cost_per_Treatment","Usage_per_Treatment"]], use_container_width=True, hide_index=True)

st.subheader("Top 10 Highest Cost per Treatment")
st.dataframe(view.sort_values("Cost_per_Treatment", ascending=False)[["Property Name","State","Utility","Cost_per_Treatment","Total_Cost","Total_Usage"]].head(10), use_container_width=True, hide_index=True)
