from __future__ import annotations
import streamlit as st
from utils.ui import apply_css, metric_card
from utils.calculations import monthly_summary, filter_df, money_fmt
from utils.alerts import build_alerts, generate_insight
from utils.app_state import load_current_data

st.set_page_config(page_title="AI Insights Center", page_icon="🤖", layout="wide")
apply_css()
st.title("6. AI Insights Center")
st.caption("Automatically generated explanations for utility trends, anomalies, and opportunities")
df, monthly, alerts = load_current_data()
states = ["All"] + sorted(df["State"].dropna().unique().tolist())
utils = ["All"] + sorted(df["Utility"].dropna().unique().tolist())
months = sorted(monthly["Bill Month"].dropna().unique())
c1,c2,c3,c4 = st.columns(4)
state = c1.multiselect("State", states, default=["All"])
utility = c2.multiselect("Utility", utils, default=["All"])
impact = c3.selectbox("Impact", ["All", "Critical", "Review", "Info", "Normal"])
date = c4.selectbox("Month", months, index=len(months)-1 if months else 0, format_func=lambda x: x.strftime('%b %Y') if hasattr(x,'strftime') else str(x))
view = filter_df(alerts, state, None, utility, [date, date])
if impact != "All": view = view[view["Alert Level"] == impact]
view = view.copy()
view["Insight"] = view.apply(generate_insight, axis=1)

c1,c2,c3,c4,c5 = st.columns(5)
with c1: metric_card("Critical Insights", str((view["Alert Level"]=="Critical").sum()))
with c2: metric_card("High Impact Insights", str((view["Estimated Monthly Impact"]>1000).sum()))
with c3: metric_card("Opportunity Insights", str((view["Cost_per_Treatment"]>view["Cost_per_Treatment"].mean()).sum()))
with c4: metric_card("Positive/Normal", str((view["Alert Level"]=="Normal").sum()))
with c5: metric_card("Total Est. Impact", money_fmt(view["Estimated Monthly Impact"].sum()))

st.subheader("AI Detected Insights")
cols = ["Alert Level","Insight","Property Name","State","Utility","Estimated Monthly Impact","Alert Type","Last_Bill_Date"]
st.dataframe(view.sort_values("Estimated Monthly Impact", ascending=False)[cols], use_container_width=True, hide_index=True)

st.download_button("Export Insights", view.to_csv(index=False).encode(), "ai_insights.csv", "text/csv")

st.info("How insights work: the app compares month-over-month usage, cost, cost/treatment, treatment volume, days billed, and bill timing. It flags changes over 10% for review and over 20% as critical.")
