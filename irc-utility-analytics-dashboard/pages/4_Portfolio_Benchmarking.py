from __future__ import annotations
import streamlit as st
from utils.ui import apply_css, metric_card
from utils.calculations import monthly_summary, filter_df, money_fmt
from utils.charts import scatter
from utils.app_state import load_current_data

st.set_page_config(page_title="Portfolio Benchmarking", page_icon="📊", layout="wide")
apply_css()
st.title("4. Portfolio Benchmarking")
st.caption("Compare performance across all dialysis centers")
df, monthly, alerts = load_current_data()
states = ["All"] + sorted(df["State"].dropna().unique().tolist())
utils = ["All"] + sorted(df["Utility"].dropna().unique().tolist())
months = sorted(monthly["Bill Month"].dropna().unique())
c1,c2,c3 = st.columns(3)
state = c1.multiselect("State", states, default=["All"])
utility = c2.multiselect("Utility", utils, default=["All"])
date = c3.selectbox("Month", months, index=len(months)-1 if months else 0, format_func=lambda x: x.strftime('%b %Y') if hasattr(x,'strftime') else str(x))
view = filter_df(monthly, state, None, utility, [date, date])

c1,c2,c3,c4 = st.columns(4)
with c1: metric_card("Portfolio Avg Cost / Treatment", f"${view['Cost_per_Treatment'].mean():,.2f}" if len(view) else "—")
with c2: metric_card("Portfolio Avg Usage / Treatment", f"{view['Usage_per_Treatment'].mean():,.0f}" if len(view) else "—")
with c3: metric_card("Total Portfolio Cost", money_fmt(view["Total_Cost"].sum()))
with c4: metric_card("Total Treatments", f"{view['Treatments'].sum():,.0f}")

st.subheader("Rankings")
a,b,c,d = st.columns(4)
with a:
    st.markdown("**Top 10 Lowest Cost/Treatment**")
    st.dataframe(view.sort_values("Cost_per_Treatment")[["Property Name","State","Utility","Cost_per_Treatment"]].head(10), use_container_width=True, hide_index=True)
with b:
    st.markdown("**Top 10 Highest Cost/Treatment**")
    st.dataframe(view.sort_values("Cost_per_Treatment", ascending=False)[["Property Name","State","Utility","Cost_per_Treatment"]].head(10), use_container_width=True, hide_index=True)
with c:
    st.markdown("**Top 10 Lowest Usage/Treatment**")
    st.dataframe(view.sort_values("Usage_per_Treatment")[["Property Name","State","Utility","Usage_per_Treatment"]].head(10), use_container_width=True, hide_index=True)
with d:
    st.markdown("**Top 10 Highest Usage/Treatment**")
    st.dataframe(view.sort_values("Usage_per_Treatment", ascending=False)[["Property Name","State","Utility","Usage_per_Treatment"]].head(10), use_container_width=True, hide_index=True)

st.subheader("Outlier Charts")
c1,c2,c3 = st.columns(3)
with c1: st.plotly_chart(scatter(view,"Treatments","Cost_per_Treatment","Cost/Treatment vs Treatments", color="Utility", hover_name="Property Name"), use_container_width=True)
with c2: st.plotly_chart(scatter(view,"Treatments","Usage_per_Treatment","Usage/Treatment vs Treatments", color="Utility", hover_name="Property Name"), use_container_width=True)
with c3: st.plotly_chart(scatter(view,"Usage_per_Treatment","Cost_per_Treatment","Cost/Treatment vs Usage/Treatment", color="State", hover_name="Property Name"), use_container_width=True)

st.subheader("Center Performance Summary by State")
state_summary = view.groupby("State", as_index=False).agg(Centers=("Property Name","nunique"), Total_Cost=("Total_Cost","sum"), Avg_Cost_per_Treatment=("Cost_per_Treatment","mean"), Total_Treatments=("Treatments","sum"), Avg_Usage_per_Treatment=("Usage_per_Treatment","mean"))
st.dataframe(state_summary, use_container_width=True, hide_index=True)
