from __future__ import annotations
import streamlit as st
from utils.ui import apply_css, metric_card
from utils.calculations import monthly_summary, latest_month, filter_df, money_fmt, num_fmt
from utils.alerts import build_alerts
from utils.charts import line
from utils.app_state import load_current_data

st.set_page_config(page_title="Operations Command Center", page_icon="🏠", layout="wide")
apply_css()
st.title("1. Operations Command Center")
st.caption("Portfolio overview and key performance indicators")

df, monthly, alerts = load_current_data()
states = ["All"] + sorted(df["State"].dropna().unique().tolist())
utils = ["All"] + sorted(df["Utility"].dropna().unique().tolist())
col1,col2,col3 = st.columns(3)
state = col1.multiselect("State", states, default=["All"])
utility = col2.multiselect("Utility", utils, default=["All"])
months = sorted(monthly["Bill Month"].dropna().unique())
date = col3.selectbox("Month", months, index=len(months)-1 if months else 0, format_func=lambda x: x.strftime('%b %Y') if hasattr(x,'strftime') else str(x))
cur = filter_df(monthly, state, None, utility, [date, date])
a_cur = filter_df(alerts, state, None, utility, [date, date])

c1,c2,c3,c4,c5 = st.columns(5)
with c1: metric_card("Total Portfolio Cost", money_fmt(cur["Total_Cost"].sum()))
with c2: metric_card("Total Usage", num_fmt(cur["Total_Usage"].sum()))
with c3: metric_card("Avg Cost per Treatment", f"${cur['Cost_per_Treatment'].mean():,.2f}" if len(cur) else "—")
with c4: metric_card("Flagged Properties", str((a_cur["Alert Level"].isin(["Critical","Review"])).sum()))
with c5: metric_card("Missing/Late Bills", str((a_cur["Alert Type"]=="Missing/Late Bill").sum()))

st.subheader("Top Changes")
t1,t2,t3 = st.columns(3)
with t1:
    st.markdown("**Top 10 Cost Increases**")
    st.dataframe(cur.sort_values("Total_Cost_Change", ascending=False)[["Property Name","Utility","Total_Cost","Total_Cost_Change"]].head(10), use_container_width=True, hide_index=True)
with t2:
    st.markdown("**Top 10 Usage Increases**")
    st.dataframe(cur.sort_values("Total_Usage_Change", ascending=False)[["Property Name","Utility","Total_Usage","Total_Usage_Change"]].head(10), use_container_width=True, hide_index=True)
with t3:
    st.markdown("**Top 10 Cost/Treatment Increases**")
    st.dataframe(cur.sort_values("Cost_per_Treatment_Change", ascending=False)[["Property Name","Utility","Cost_per_Treatment","Cost_per_Treatment_Change"]].head(10), use_container_width=True, hide_index=True)

st.subheader("Portfolio Trends")
filtered = filter_df(monthly, state, None, utility, None)
trend = filtered.groupby("Bill Month", as_index=False).agg(Total_Cost=("Total_Cost","sum"), Total_Usage=("Total_Usage","sum"), Cost_per_Treatment=("Cost_per_Treatment","mean"))
c1,c2,c3 = st.columns(3)
with c1: st.plotly_chart(line(trend,"Bill Month","Total_Cost","Total Cost"), use_container_width=True)
with c2: st.plotly_chart(line(trend,"Bill Month","Total_Usage","Total Usage"), use_container_width=True)
with c3: st.plotly_chart(line(trend,"Bill Month","Cost_per_Treatment","Avg Cost / Treatment"), use_container_width=True)

st.subheader("Flagged Properties Summary")
st.dataframe(a_cur.sort_values("Estimated Monthly Impact", ascending=False)[["Alert Level","Property Name","State","Utility","Alert Type","Reason","Total_Usage_Change","Total_Cost_Change","Cost_per_Treatment_Change","Last_Bill_Date"]], use_container_width=True, hide_index=True)
