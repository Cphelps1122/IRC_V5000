from __future__ import annotations

from io import BytesIO
from xml.sax.saxutils import escape

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

import config
from utils.alerts import alert_counts, build_alerts
from utils.calculations import fmt_money, fmt_num, selected_month_summary, top_performers, utility_cost_per_usage_breakdown


def _ptext(value) -> str:
    return escape(str(value))


def monthly_takeaways(df, current_month, previous_month, alerts) -> list[str]:
    summary = selected_month_summary(df, current_month, previous_month)
    counts = alert_counts(alerts)
    cm = pd.to_datetime(current_month).strftime("B %Y")
    cm = pd.to_datetime(current_month).strftime("%B %Y")
    takeaways = []
    if pd.notna(summary["delta_amount"]):
        takeaways.append(
            f"For {cm}, total utility cost was {fmt_money(summary['current']['amount'])}, compared with {fmt_money(summary['previous']['amount'])} last month ({summary['delta_amount']:+.1f}%)."
        )
    else:
        takeaways.append(f"For {cm}, total utility cost was {fmt_money(summary['current']['amount'])}. Prior-month comparison was not available.")
    if pd.notna(summary["delta_cpt"]):
        takeaways.append(
            f"Cost per treatment was {fmt_money(summary['current']['cost_per_treatment'], 2)}, a {summary['delta_cpt']:+.1f}% change from the previous month."
        )
    takeaways.append(f"The dashboard identified {counts['Total']} active anomalies: {counts['Critical']} critical and {counts['Review']} review-level items.")
    if not alerts.empty:
        top = alerts.iloc[0]
        takeaways.append(f"Highest-priority review item: {top['Property']} / {top['Utility']} — {top['Reason']}.")
    return takeaways


def recommended_followups(alerts: pd.DataFrame) -> list[str]:
    if alerts.empty:
        return ["No critical anomalies identified for the selected month."]
    items = []
    critical = alerts[alerts["Severity"] == "Critical"].head(3)
    for _, r in critical.iterrows():
        items.append(f"Review {r['Property']} {r['Utility']} invoice: {r['Reason']}.")
    if len(items) < 4:
        review = alerts[alerts["Severity"] == "Review"].head(4 - len(items))
        for _, r in review.iterrows():
            items.append(f"Monitor {r['Property']} {r['Utility']} trend next month: {r['Reason']}.")
    return items or ["Continue monitoring portfolio-level cost per treatment and utility-specific cost per usage."]


def generate_monthly_pdf(df, current_month, previous_month) -> bytes:
    alerts = build_alerts(df, current_month, previous_month)
    counts = alert_counts(alerts)
    summary = selected_month_summary(df, current_month, previous_month)
    performers = top_performers(df, current_month, previous_month, n=5)
    utility_breakdown = utility_cost_per_usage_breakdown(df, current_month, previous_month)

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(letter),
        rightMargin=0.35 * inch,
        leftMargin=0.35 * inch,
        topMargin=0.30 * inch,
        bottomMargin=0.30 * inch,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=18, textColor=colors.HexColor("#0F172A"), spaceAfter=4)
    h_style = ParagraphStyle("Header", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=10, textColor=colors.HexColor("#0F172A"), spaceBefore=4, spaceAfter=4)
    small = ParagraphStyle("Small", parent=styles["BodyText"], fontSize=8, leading=10, textColor=colors.HexColor("#334155"))

    story = []
    month_label = pd.to_datetime(current_month).strftime("%B %Y")
    prev_label = pd.to_datetime(previous_month).strftime("%B %Y") if previous_month is not None else "N/A"
    story.append(Paragraph(_ptext(f"{config.REPORT_TITLE}: {month_label}"), title_style))
    story.append(Paragraph(_ptext(f"{config.REPORT_SUBTITLE} | Previous month: {prev_label}"), small))
    story.append(Spacer(1, 0.08 * inch))

    kpi_data = [[
        "Total Cost", "Prev Cost", "Cost Change", "Cost/Treatment", "Prev CPT", "CPT Change", "Total Usage", "Treatments", "Alerts"
    ], [
        fmt_money(summary['current']['amount']),
        fmt_money(summary['previous']['amount']),
        f"{summary['delta_amount']:+.1f}%" if pd.notna(summary['delta_amount']) else "N/A",
        fmt_money(summary['current']['cost_per_treatment'], 2),
        fmt_money(summary['previous']['cost_per_treatment'], 2),
        f"{summary['delta_cpt']:+.1f}%" if pd.notna(summary['delta_cpt']) else "N/A",
        fmt_num(summary['current']['usage']),
        fmt_num(summary['current']['treatments']),
        f"{counts['Critical']} critical / {counts['Review']} review",
    ]]
    story.append(Table(kpi_data, colWidths=[1.1*inch]*9, style=[
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#0F172A")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("BACKGROUND", (0,1), (-1,1), colors.HexColor("#F8FAFC")),
        ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#CBD5E1")),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTNAME", (0,1), (-1,1), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 7.4),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(Spacer(1, 0.08 * inch))

    story.append(Paragraph("Key Monthly Takeaways", h_style))
    for takeaway in monthly_takeaways(df, current_month, previous_month, alerts)[:4]:
        story.append(Paragraph(_ptext("- " + takeaway), small))
    story.append(Spacer(1, 0.06 * inch))

    anomaly_rows = [["Property", "Utility", "Issue", "Impact"]]
    if not alerts.empty:
        for _, r in alerts.head(5).iterrows():
            anomaly_rows.append([str(r["Property"])[:22], str(r["Utility"])[:10], str(r["Reason"])[:48], fmt_money(r.get("Estimated Monthly Impact", 0))])
    else:
        anomaly_rows.append(["No active anomalies", "", "", ""])

    performer_rows = [["Property", "State", "Cost/Treatment", "Change"]]
    if not performers.empty:
        for _, r in performers.iterrows():
            chg = r.get("Improvement %")
            performer_rows.append([str(r["property"])[:24], str(r["state"]), fmt_money(r.get("Cost/Treatment"), 2), f"{chg:+.1f}%" if pd.notna(chg) else "N/A"])
    else:
        performer_rows.append(["No performers found", "", "", ""])

    story.append(Paragraph("Top Anomalies", h_style))
    story.append(Table(anomaly_rows, colWidths=[1.65*inch, .75*inch, 3.35*inch, .75*inch], style=_small_table_style()))
    story.append(Spacer(1, 0.05 * inch))
    story.append(Paragraph("Top Performing Properties", h_style))
    story.append(Table(performer_rows, colWidths=[2.65*inch, .65*inch, 1.25*inch, 1.0*inch], style=_small_table_style()))
    story.append(Spacer(1, 0.05 * inch))

    story.append(Paragraph("Utility Breakdown", h_style))
    utility_rows = [["Utility", "Cost/Usage", "Prev", "Change", "Current Cost", "Usage Unit"]]
    if not utility_breakdown.empty:
        for _, r in utility_breakdown.head(6).iterrows():
            utility_rows.append([str(r["Utility"]), fmt_money(r["This Month"], 3), fmt_money(r["Previous Month"], 3), f"{r['% Change']:+.1f}%" if pd.notna(r["% Change"]) else "N/A", fmt_money(r["Current Cost"]), str(r["Unit"])])
    else:
        utility_rows.append(["No utility breakdown available", "", "", "", "", ""])
    story.append(Table(utility_rows, colWidths=[1.15*inch, 1.15*inch, 1.0*inch, .85*inch, 1.15*inch, 1.15*inch], style=_small_table_style()))

    story.append(Spacer(1, 0.06 * inch))
    story.append(Paragraph("Recommended Follow-Up", h_style))
    for item in recommended_followups(alerts)[:4]:
        story.append(Paragraph(_ptext("- " + item), small))

    doc.build(story)
    return buf.getvalue()


def _small_table_style():
    return TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1E293B")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("BACKGROUND", (0,1), (-1,-1), colors.HexColor("#FFFFFF")),
        ("TEXTCOLOR", (0,1), (-1,-1), colors.HexColor("#0F172A")),
        ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#CBD5E1")),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 7.0),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 3),
        ("RIGHTPADDING", (0,0), (-1,-1), 3),
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ])
