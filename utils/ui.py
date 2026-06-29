from __future__ import annotations
import streamlit as st


def apply_css():
    st.markdown('''
    <style>
    .block-container {padding-top: 1.5rem; padding-bottom: 2rem; max-width: 1500px;}
    [data-testid="stSidebar"] {background: linear-gradient(180deg, #061b35 0%, #051326 100%);}
    [data-testid="stSidebar"] * {color: white;}
    .metric-card {background:#fff; border:1px solid #dfe6f1; border-radius:14px; padding:18px; box-shadow:0 1px 6px rgba(7,26,61,.05); min-height:116px;}
    .metric-label {font-size:12px; color:#607087; text-transform:uppercase; font-weight:700;}
    .metric-value {font-size:28px; color:#071a3d; font-weight:800; margin-top:8px;}
    .metric-delta-red {color:#e52520; font-size:13px; font-weight:700;}
    .metric-delta-green {color:#07883e; font-size:13px; font-weight:700;}
    .section-card {background:#fff; border:1px solid #dfe6f1; border-radius:14px; padding:16px; margin-bottom:16px;}
    .critical {background:#ffe8e8; color:#c91510; padding:4px 10px; border-radius:8px; font-weight:800;}
    .review {background:#fff3d9; color:#c96b00; padding:4px 10px; border-radius:8px; font-weight:800;}
    .info {background:#e8f1ff; color:#135fc2; padding:4px 10px; border-radius:8px; font-weight:800;}
    </style>
    ''', unsafe_allow_html=True)


def metric_card(label, value, delta=None, positive_good=True):
    cls = "metric-delta-green" if (delta and str(delta).strip().startswith(('▼','-'))) == positive_good else "metric-delta-red"
    st.markdown(f'''<div class="metric-card"><div class="metric-label">{label}</div><div class="metric-value">{value}</div>{f'<div class="{cls}">{delta}</div>' if delta else ''}</div>''', unsafe_allow_html=True)
