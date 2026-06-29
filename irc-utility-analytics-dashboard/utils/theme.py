from __future__ import annotations

import html
from typing import Callable

import pandas as pd
import streamlit as st

DARK = {
    "name": "dark",
    "bg": "#07111F",
    "panel": "#0F1F35",
    "panel2": "#122945",
    "text": "#EAF2FF",
    "muted": "#9FB4CF",
    "border": "rgba(148, 163, 184, 0.22)",
    "accent": "#38BDF8",
    "accent2": "#22C55E",
    "warning": "#F59E0B",
    "danger": "#EF4444",
    "info": "#60A5FA",
    "card_shadow": "0 14px 36px rgba(0,0,0,0.22)",
    "plotly_template": "plotly_dark",
}

LIGHT = {
    "name": "light",
    "bg": "#F5F7FB",
    "panel": "#FFFFFF",
    "panel2": "#F8FAFC",
    "text": "#0F172A",
    "muted": "#64748B",
    "border": "rgba(15, 23, 42, 0.12)",
    "accent": "#0284C7",
    "accent2": "#16A34A",
    "warning": "#D97706",
    "danger": "#DC2626",
    "info": "#2563EB",
    "card_shadow": "0 12px 30px rgba(15,23,42,0.08)",
    "plotly_template": "plotly_white",
}


def init_theme():
    if "theme_mode" not in st.session_state:
        st.session_state.theme_mode = "dark"


def current_theme():
    init_theme()
    return DARK if st.session_state.theme_mode == "dark" else LIGHT


def theme_toggle():
    init_theme()
    selected = st.sidebar.toggle(
        "Light mode",
        value=(st.session_state.theme_mode == "light"),
        help="Switch the dashboard from dark mode to light mode.",
    )
    st.session_state.theme_mode = "light" if selected else "dark"


def apply_theme():
    t = current_theme()
    st.markdown(
        f"""
        <style>
        :root {{
            --app-bg: {t['bg']};
            --panel-bg: {t['panel']};
            --panel-bg-2: {t['panel2']};
            --text-main: {t['text']};
            --text-muted: {t['muted']};
            --border: {t['border']};
            --accent: {t['accent']};
            --accent-2: {t['accent2']};
            --warning: {t['warning']};
            --danger: {t['danger']};
            --info: {t['info']};
        }}
        .stApp {{
            background: radial-gradient(circle at top left, rgba(56, 189, 248, 0.11), transparent 24rem), var(--app-bg) !important;
            color: var(--text-main) !important;
        }}
        [data-testid="stSidebar"] {{
            background: linear-gradient(180deg, #050B14 0%, #0A1628 55%, #07111F 100%) !important;
            border-right: 1px solid rgba(148, 163, 184, 0.18);
        }}
        [data-testid="stSidebar"] * {{ color: #EAF2FF !important; }}
        .block-container {{
            padding-top: 1.25rem;
            padding-bottom: 3rem;
            max-width: 1500px;
        }}
        h1, h2, h3 {{ color: var(--text-main) !important; letter-spacing: -0.02em; }}
        p, span, label, div {{ color: inherit; }}
        .page-title {{
            font-size: 1.9rem;
            font-weight: 850;
            color: var(--text-main);
            margin-bottom: 0.2rem;
        }}
        .page-subtitle {{
            color: var(--text-muted);
            font-size: 0.95rem;
            margin-bottom: 1rem;
        }}
        .metric-card {{
            background: linear-gradient(180deg, var(--panel-bg) 0%, var(--panel-bg-2) 100%);
            border: 1px solid var(--border);
            border-radius: 18px;
            padding: 18px 18px 16px 18px;
            box-shadow: {t['card_shadow']};
            min-height: 134px;
        }}
        .metric-label {{
            color: var(--text-muted);
            font-size: 0.77rem;
            text-transform: uppercase;
            letter-spacing: 0.075em;
            font-weight: 750;
        }}
        .metric-value {{
            color: var(--text-main);
            font-size: 1.7rem;
            font-weight: 850;
            line-height: 1.15;
            margin-top: 0.42rem;
            overflow-wrap: anywhere;
        }}
        .metric-prev {{
            color: var(--text-muted);
            font-size: 0.82rem;
            margin-top: 0.36rem;
        }}
        .delta-up {{ color: var(--danger); font-weight: 850; }}
        .delta-down {{ color: var(--accent-2); font-weight: 850; }}
        .delta-neutral {{ color: var(--text-muted); font-weight: 850; }}
        .panel {{
            background: linear-gradient(180deg, var(--panel-bg) 0%, var(--panel-bg-2) 100%);
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 18px;
            box-shadow: {t['card_shadow']};
            margin-bottom: 1rem;
        }}
        .panel-title {{
            color: var(--text-main);
            font-weight: 850;
            font-size: 1.05rem;
            margin-bottom: 0.15rem;
        }}
        .panel-caption {{ color: var(--text-muted); font-size: 0.86rem; margin-bottom: 0.8rem; }}
        .small-muted {{ color: var(--text-muted); font-size: 0.86rem; }}
        .pill {{
            display: inline-block;
            border-radius: 999px;
            padding: 0.22rem 0.62rem;
            font-size: 0.76rem;
            font-weight: 850;
            margin-right: 0.35rem;
            white-space: nowrap;
        }}
        .pill-danger {{ background: rgba(239,68,68,0.16); color: #FCA5A5; border: 1px solid rgba(239,68,68,0.35); }}
        .pill-warning {{ background: rgba(245,158,11,0.16); color: #FCD34D; border: 1px solid rgba(245,158,11,0.35); }}
        .pill-good {{ background: rgba(34,197,94,0.16); color: #86EFAC; border: 1px solid rgba(34,197,94,0.35); }}
        .pill-info {{ background: rgba(96,165,250,0.16); color: #93C5FD; border: 1px solid rgba(96,165,250,0.35); }}
        .insight-box {{
            border-left: 4px solid var(--accent);
            background: rgba(56,189,248,0.08);
            border-radius: 12px;
            padding: 12px 14px;
            margin-bottom: 0.7rem;
            color: var(--text-main);
        }}

        /* Strong readability guardrails for dark mode and Streamlit widgets. */
        [data-testid="stAppViewContainer"], [data-testid="stAppViewContainer"] * {{
            color: var(--text-main);
        }}
        .stMarkdown, .stMarkdown *, .stCaptionContainer, .stCaptionContainer *,
        [data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] * {{
            color: inherit;
        }}
        .element-container, .element-container * { color: inherit; }
        label, [data-testid="stWidgetLabel"], [data-testid="stWidgetLabel"] * {{
            color: var(--text-main) !important;
        }}
        .stSelectbox label, .stMultiSelect label, .stRadio label, .stTextInput label {{
            color: var(--text-main) !important;
        }}
        div[data-baseweb="select"] div,
        div[data-baseweb="select"] span,
        div[data-baseweb="select"] p,
        div[data-baseweb="select"] input,
        div[data-baseweb="tag"],
        div[data-baseweb="tag"] span {{
            color: #EAF2FF !important;
            -webkit-text-fill-color: #EAF2FF !important;
        }}
        div[data-baseweb="tag"] {{
            background-color: rgba(56, 189, 248, 0.18) !important;
            border: 1px solid rgba(56, 189, 248, 0.35) !important;
        }}
        [data-testid="stMetric"], [data-testid="stMetric"] * {{
            color: var(--text-main) !important;
        }}
        
        .stButton > button, .stDownloadButton > button {{
            border-radius: 12px;
            border: 1px solid var(--border);
            background: linear-gradient(180deg, var(--panel-bg-2), var(--panel-bg));
            color: var(--text-main);
            font-weight: 800;
        }}
        .stButton > button:hover, .stDownloadButton > button:hover {{
            border-color: var(--accent);
            color: var(--accent);
        }}
        .st-key-sticky_filters {{
            position: sticky;
            top: 0;
            z-index: 999;
            background: color-mix(in srgb, var(--app-bg) 88%, transparent);
            backdrop-filter: blur(18px);
            border: 1px solid var(--border);
            border-radius: 18px;
            padding: 0.65rem 0.75rem 0.75rem;
            margin-bottom: 1rem;
            box-shadow: 0 10px 26px rgba(0,0,0,0.18);
        }}
        .filter-title {{
            color: var(--text-muted);
            font-size: 0.72rem;
            text-transform: uppercase;
            letter-spacing: .08em;
            font-weight: 850;
            margin-bottom: .25rem;
        }}
        div[data-baseweb="select"] > div,
        div[data-baseweb="input"] > div,
        input, textarea {{
            background-color: rgba(18, 41, 69, 0.92) !important;
            border: 1px solid rgba(148, 163, 184, 0.38) !important;
            color: #EAF2FF !important;
            -webkit-text-fill-color: #EAF2FF !important;
            border-radius: 12px !important;
        }}
        div[data-baseweb="select"] span,
        div[data-baseweb="select"] svg,
        div[data-baseweb="select"] input {{
            color: #EAF2FF !important;
            fill: #EAF2FF !important;
            -webkit-text-fill-color: #EAF2FF !important;
        }}
        div[data-baseweb="popover"] ul,
        div[data-baseweb="popover"] li,
        div[role="listbox"] {{
            background-color: #0F1F35 !important;
            color: #EAF2FF !important;
        }}
        div[role="option"], div[role="option"] span,
        div[data-baseweb="menu"] li, div[data-baseweb="menu"] li span {{
            color: #EAF2FF !important;
            background-color: #0F1F35 !important;
        }}
        .dashboard-table {{ width:100%; border-collapse: separate; border-spacing:0 10px; table-layout: fixed; }}
        .dashboard-table th {{
            text-align:left; color:var(--text-muted); font-size:.72rem; text-transform:uppercase;
            letter-spacing:.07em; padding:0 .65rem .25rem .65rem;
        }}
        .dashboard-table td {{
            background: rgba(15,31,53,.70); border-top:1px solid var(--border); border-bottom:1px solid var(--border);
            padding:.72rem .65rem; vertical-align:top; color:var(--text-main); font-size:.88rem;
            white-space: normal; overflow-wrap:anywhere;
        }}
        .dashboard-table td:first-child {{ border-left:1px solid var(--border); border-radius:14px 0 0 14px; }}
        .dashboard-table td:last-child {{ border-right:1px solid var(--border); border-radius:0 14px 14px 0; }}
        .alert-card {{
            background: linear-gradient(180deg, rgba(15,31,53,.92), rgba(18,41,69,.88));
            border: 1px solid var(--border);
            border-radius: 18px;
            padding: 14px 16px;
            margin-bottom: 12px;
            box-shadow: {t['card_shadow']};
        }}
        .alert-head {{ display:flex; justify-content:space-between; gap:1rem; align-items:flex-start; }}
        .alert-title {{ font-weight:850; font-size:1rem; color:var(--text-main); }}
        .alert-sub {{ color:var(--text-muted); font-size:.84rem; margin-top:.18rem; }}
        .alert-reason {{ margin-top:.65rem; font-size:.9rem; color:var(--text-main); line-height:1.35; }}
        .mini-grid {{ display:grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap:.55rem; margin-top:.75rem; }}
        .mini-stat {{ border:1px solid var(--border); background:rgba(255,255,255,.035); border-radius:12px; padding:.55rem .65rem; }}
        .mini-label {{ color:var(--text-muted); font-size:.68rem; text-transform:uppercase; letter-spacing:.06em; font-weight:800; }}
        .mini-value {{ color:var(--text-main); font-size:.9rem; font-weight:850; margin-top:.12rem; }}
        @media (max-width: 900px) {{ .mini-grid {{ grid-template-columns: repeat(2, minmax(0,1fr)); }} }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(title: str, subtitle: str = ""):
    st.markdown(f'<div class="page-title">{html.escape(title)}</div>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<div class="page-subtitle">{html.escape(subtitle)}</div>', unsafe_allow_html=True)


def delta_html(delta: float | None) -> str:
    if delta is None or pd.isna(delta):
        return ""
    cls = "delta-neutral"
    arrow = "→"
    if delta > 0:
        cls = "delta-up"
        arrow = "▲"
    elif delta < 0:
        cls = "delta-down"
        arrow = "▼"
    return f'<span class="{cls}">{arrow} {abs(delta):.1f}%</span>'


def kpi_card(label: str, value: str, previous: str = "", delta: float | None = None, caption: str = ""):
    previous_html = f'<div class="metric-prev">Prev: {html.escape(str(previous))} {delta_html(delta)}</div>' if previous else ""
    caption_html = f'<div class="small-muted">{html.escape(str(caption))}</div>' if caption else ""
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{html.escape(str(label))}</div>
            <div class="metric-value">{html.escape(str(value))}</div>
            {previous_html}
            {caption_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def panel_start(title: str, caption: str = ""):
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown(f'<div class="panel-title">{html.escape(title)}</div>', unsafe_allow_html=True)
    if caption:
        st.markdown(f'<div class="panel-caption">{html.escape(caption)}</div>', unsafe_allow_html=True)


def panel_end():
    st.markdown('</div>', unsafe_allow_html=True)


def severity_pill(severity: str) -> str:
    sev = str(severity)
    cls = "pill-info"
    if sev == "Critical":
        cls = "pill-danger"
    elif sev == "Review":
        cls = "pill-warning"
    elif sev in {"Normal", "Improved"}:
        cls = "pill-good"
    return f'<span class="pill {cls}">{html.escape(sev)}</span>'


def compact_table(df: pd.DataFrame, columns: list[str], formatters: dict[str, Callable] | None = None, max_rows: int = 10, empty_message: str = "No records found."):
    if df is None or df.empty:
        st.info(empty_message)
        return
    d = df.copy().head(max_rows)
    formatters = formatters or {}
    header = "".join(f"<th>{html.escape(str(col))}</th>" for col in columns)
    rows = []
    for _, r in d.iterrows():
        cells = []
        for col in columns:
            val = r.get(col, "")
            if col in formatters:
                try:
                    val = formatters[col](val)
                except Exception:
                    val = "—"
            if pd.isna(val):
                val = "—"
            cells.append(f"<td>{val if str(val).startswith('<span') else html.escape(str(val))}</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")
    st.markdown(f"<table class='dashboard-table'><thead><tr>{header}</tr></thead><tbody>{''.join(rows)}</tbody></table>", unsafe_allow_html=True)
    if len(df) > max_rows:
        st.caption(f"Showing top {max_rows} of {len(df)} records.")


def alert_cards(alerts: pd.DataFrame, max_cards: int = 12):
    if alerts is None or alerts.empty:
        st.success("No active anomalies for the selected filters.")
        return
    for _, r in alerts.head(max_cards).iterrows():
        sev = r.get("Severity", "Info")
        prop = html.escape(str(r.get("Property", "Unknown")))
        utility = html.escape(str(r.get("Utility", "Unknown")))
        reason = html.escape(str(r.get("Reason", "Review item")))
        explanation = html.escape(str(r.get("Explanation", "")))
        cost_chg = r.get("Cost Change %")
        usage_chg = r.get("Usage Change %")
        cpt_chg = r.get("Cost/Treatment Change %")
        upt_chg = r.get("Usage/Treatment Change %")
        treatment_chg = r.get("Treatments Change %")
        impact = r.get("Estimated Monthly Impact")
        current_cost = r.get("Current Cost")
        current_cpt = r.get("Current Cost/Treatment")
        current_upt = r.get("Current Usage/Treatment")
        current_usage = r.get("Current Usage")
        is_missing = bool(r.get("Missing Bill", False)) or (pd.isna(current_cost) and "No bill found" in str(r.get("Reason", "")))

        if is_missing:
            metric_1_label = "Latest Cost on File"
            metric_1_value = _fmt_money_html(r.get("Previous Cost"))
            metric_2_label = "Latest Usage on File"
            metric_2_value = _fmt_num_html(r.get("Previous Usage"))
            metric_3_label = "Latest Treatments"
            metric_3_value = _fmt_num_html(r.get("Previous Treatments"))
            metric_4_label = "Latest Cost/Treatment"
            metric_4_value = _fmt_money_html(r.get("Previous Cost/Treatment"), 2)
            metric_5_label = "Latest Month on File"
            metric_5_value = html.escape(str(r.get("Latest Month On File", "—")))
            metric_6_label = "Est. Impact"
            metric_6_value = _fmt_money_html(impact)
        else:
            metric_1_label = "Current Cost"
            metric_1_value = _fmt_money_html(current_cost)
            metric_2_label = "Treatment Δ"
            metric_2_value = _fmt_pct_html(treatment_chg)
            metric_3_label = "Cost/Treatment Δ"
            metric_3_value = _fmt_pct_html(cpt_chg)
            metric_4_label = "Usage/Treatment Δ"
            metric_4_value = _fmt_pct_html(upt_chg)
            metric_5_label = "Cost/Treatment"
            metric_5_value = _fmt_money_html(current_cpt, 2)
            metric_6_label = "Usage/Treatment"
            metric_6_value = _fmt_num_html(current_upt, 2)

        st.markdown(
            f"""
            <div class="alert-card">
              <div class="alert-head">
                <div>
                  <div>{severity_pill(sev)} <span class="alert-title">{prop}</span></div>
                  <div class="alert-sub">{utility}</div>
                </div>
                <div class="alert-sub">Open Property Scorecard for details</div>
              </div>
              <div class="alert-reason"><b>Reason:</b> {reason}</div>
              <div class="mini-grid">
                <div class="mini-stat"><div class="mini-label">{metric_1_label}</div><div class="mini-value">{metric_1_value}</div></div>
                <div class="mini-stat"><div class="mini-label">{metric_2_label}</div><div class="mini-value">{metric_2_value}</div></div>
                <div class="mini-stat"><div class="mini-label">{metric_3_label}</div><div class="mini-value">{metric_3_value}</div></div>
                <div class="mini-stat"><div class="mini-label">{metric_4_label}</div><div class="mini-value">{metric_4_value}</div></div>
              </div>
              <div class="mini-grid">
                <div class="mini-stat"><div class="mini-label">{metric_5_label}</div><div class="mini-value">{metric_5_value}</div></div>
                <div class="mini-stat"><div class="mini-label">{metric_6_label}</div><div class="mini-value">{metric_6_value}</div></div>
                <div class="mini-stat" style="grid-column: span 2;"><div class="mini-label">Explanation</div><div class="mini-value" style="font-weight:650; line-height:1.35;">{explanation}</div></div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    if len(alerts) > max_cards:
        st.caption(f"Showing top {max_cards} of {len(alerts)} alerts. Use filters to narrow the queue.")


def _fmt_money_html(v, digits=0):
    if v is None or pd.isna(v):
        return "—"
    return html.escape(f"${float(v):,.{digits}f}")


def _fmt_num_html(v, digits=0):
    if v is None or pd.isna(v):
        return "—"
    return html.escape(f"{float(v):,.{digits}f}")


def _fmt_pct_html(v):
    if v is None or pd.isna(v):
        return "—"
    cls = "delta-up" if v > 0 else "delta-down" if v < 0 else "delta-neutral"
    arrow = "▲" if v > 0 else "▼" if v < 0 else "→"
    return f'<span class="{cls}">{arrow} {abs(float(v)):.1f}%</span>'
