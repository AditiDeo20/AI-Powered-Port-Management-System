"""Professional PDF renderer for Tender Publication workflow documents.

The renderer consumes the persisted workflow record and does not insert any
commercial or approval values. It produces a static, reviewable PDF suitable
for downloading as an LAC, Board Note, or Tender draft.
"""

from __future__ import annotations

from html import escape
from io import BytesIO
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import LongTable, Paragraph, Spacer, Table, TableStyle


NAVY = colors.HexColor("#0B2D52")
GOLD = colors.HexColor("#D97706")
PALE_BLUE = colors.HexColor("#EEF5FB")
LIGHT_GREY = colors.HexColor("#E2E8F0")
TEXT_GREY = colors.HexColor("#475569")
PAGE_WIDTH, PAGE_HEIGHT = A4


def _font_names() -> tuple[str, str]:
    """Use Windows Arial when present, otherwise use ReportLab built-in fonts."""
    font_directory = Path("C:/Windows/Fonts")
    regular = font_directory / "arial.ttf"
    bold = font_directory / "arialbd.ttf"
    if regular.is_file() and bold.is_file():
        if "TenderPdfRegular" not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont("TenderPdfRegular", str(regular)))
        if "TenderPdfBold" not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont("TenderPdfBold", str(bold)))
        return "TenderPdfRegular", "TenderPdfBold"
    return "Helvetica", "Helvetica-Bold"


def _paragraph(text: Any, style: ParagraphStyle) -> Paragraph:
    safe = escape(str(text if text not in (None, "") else "Not available"))
    safe = safe.replace("\n", "<br/>")
    return Paragraph(safe, style)


def _money(value: Any) -> str:
    try:
        return f"INR {float(value):,.2f}"
    except (TypeError, ValueError):
        return "Not available"


def _footer(canvas: Any, document: Any) -> None:
    canvas.saveState()
    canvas.setStrokeColor(GOLD)
    canvas.setLineWidth(0.6)
    canvas.line(document.leftMargin, 13 * mm, PAGE_WIDTH - document.rightMargin, 13 * mm)
    canvas.setFillColor(TEXT_GREY)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(document.leftMargin, 8 * mm, "Port Land Lease MMS - Source-backed Tender Workflow")
    canvas.drawRightString(PAGE_WIDTH - document.rightMargin, 8 * mm, f"Page {document.page}")
    canvas.restoreState()


def _heading(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(text), style)


def _key_value_table(rows: list[tuple[str, Any]], body_style: ParagraphStyle, label_style: ParagraphStyle) -> LongTable:
    cells = [[_paragraph(label, label_style), _paragraph(value, body_style)] for label, value in rows]
    table = LongTable(cells, colWidths=[57 * mm, 113 * mm], repeatRows=0, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (0, -1), PALE_BLUE),
        ("GRID", (0, 0), (-1, -1), 0.35, LIGHT_GREY),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def build_tender_document_pdf(
    workflow: dict[str, Any],
    config: dict[str, Any],
    kind: str,
) -> bytes:
    """Render one tender workflow record as a polished static PDF."""
    from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate

    titles = {
        "lac": "LAC Proposal Draft",
        "board-note": "Board Note Draft",
        "tender": "Tender / RFP Draft",
    }
    if kind not in titles:
        raise ValueError("Document type must be lac, board-note, or tender.")

    regular_font, bold_font = _font_names()
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TenderTitle", parent=styles["Title"], fontName=bold_font, fontSize=20,
        leading=24, textColor=NAVY, alignment=TA_LEFT, spaceAfter=2,
    )
    eyebrow_style = ParagraphStyle(
        "TenderEyebrow", parent=styles["Normal"], fontName=bold_font, fontSize=8.5,
        leading=11, textColor=GOLD, tracking=1.1, spaceAfter=4,
    )
    section_style = ParagraphStyle(
        "TenderSection", parent=styles["Heading2"], fontName=bold_font, fontSize=12,
        leading=15, textColor=NAVY, spaceBefore=12, spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "TenderBody", parent=styles["BodyText"], fontName=regular_font, fontSize=9,
        leading=13, textColor=colors.HexColor("#1E293B"),
    )
    label_style = ParagraphStyle(
        "TenderLabel", parent=body_style, fontName=bold_font, textColor=NAVY,
    )
    small_style = ParagraphStyle(
        "TenderSmall", parent=body_style, fontSize=8, leading=10, textColor=TEXT_GREY,
    )
    centred_style = ParagraphStyle(
        "TenderCentred", parent=body_style, alignment=TA_CENTER, fontSize=8, leading=10,
    )
    table_header_style = ParagraphStyle(
        "TenderTableHeader", parent=centred_style, fontName=bold_font, textColor=colors.white,
    )

    buffer = BytesIO()
    document = BaseDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=19 * mm,
        bottomMargin=20 * mm,
        title=titles[kind],
        author="Port Land Lease MMS",
    )
    frame = Frame(document.leftMargin, document.bottomMargin, document.width, document.height, id="body")
    document.addPageTemplates([PageTemplate(id="TenderDocument", frames=[frame], onPage=_footer)])

    status_label = str(workflow.get("status_label") or workflow.get("status") or "Not available")
    source_files = config.get("source_files", {})
    template_key = {"lac": "embarkation_checklist", "board-note": "board_note_template", "tender": "tender_template"}[kind]

    story: list[Any] = [
        _heading("SOURCE-BACKED WORKFLOW", eyebrow_style),
        _heading(titles[kind], title_style),
        _paragraph("Draft for review only. This document is not approved or publishable until the required authority approvals and template review are complete.", body_style),
        Spacer(1, 7 * mm),
        _key_value_table([
            ("Workflow ID", workflow.get("id")),
            ("Current stage", status_label),
            ("Selected plot", workflow.get("plot_label")),
            ("Source template/reference", source_files.get(template_key, "Not configured")),
        ], body_style, label_style),
        _heading("Source-backed plot context", section_style),
    ]

    snapshot_rows = [
        (key.replace("_", " ").title(), value)
        for key, value in (workflow.get("source_snapshot") or {}).items()
        if value not in (None, "")
    ]
    story.append(_key_value_table(snapshot_rows, body_style, label_style) if snapshot_rows else _paragraph("No source plot context was available when this workflow was created.", body_style))

    story.append(_heading("Entered proposal inputs", section_style))
    definitions = {field["key"]: field for field in config.get("form_fields", [])}
    input_rows = []
    for key, value in (workflow.get("fields") or {}).items():
        if value not in (None, ""):
            input_rows.append((definitions.get(key, {}).get("label", key.replace("_", " ").title()), value))
    story.append(_key_value_table(input_rows, body_style, label_style) if input_rows else _paragraph("No proposal values have been entered.", body_style))

    if kind == "lac":
        story.append(_heading("LAC checklist responses", section_style))
        checklist_rows = [[
            _paragraph("No.", table_header_style),
            _paragraph("Check point", table_header_style),
            _paragraph("Verified response", table_header_style),
        ]]
        for item in (workflow.get("checklist") or {}).get("items", []):
            checklist_rows.append([
                _paragraph(item.get("number"), centred_style),
                _paragraph(item.get("label"), body_style),
                _paragraph(item.get("answer"), body_style),
            ])
        if len(checklist_rows) > 1:
            checklist_table = LongTable(checklist_rows, colWidths=[13 * mm, 81 * mm, 76 * mm], repeatRows=1, hAlign="LEFT")
            checklist_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.35, LIGHT_GREY),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            story.append(checklist_table)
        else:
            story.append(_paragraph("No checklist responses are recorded.", body_style))

    calculation = workflow.get("calculation") or {}
    story.append(_heading("Financial calculation draft", section_style))
    if calculation.get("ready"):
        story.append(_key_value_table([
            ("Developed area", f"{float(calculation['developed_area_sqm']):,.2f} sq. m"),
            ("Base monthly rent", _money(calculation.get("base_monthly_rent"))),
            ("Base annual rent", _money(calculation.get("base_annual_rent"))),
            ("Upfront premium before GST", _money(calculation.get("upfront_premium_before_gst"))),
            ("GST amount", _money(calculation.get("gst_amount"))),
            ("Upfront premium including GST", _money(calculation.get("upfront_premium_including_gst"))),
        ], body_style, label_style))
        schedule = calculation.get("schedule") or []
        if schedule:
            story.extend([Spacer(1, 4 * mm), _paragraph("Year-wise present-value schedule", label_style)])
            schedule_rows = [[
                _paragraph("Year", table_header_style),
                _paragraph("Annual rent", table_header_style),
                _paragraph("Discount factor", table_header_style),
                _paragraph("Present value", table_header_style),
            ]]
            for row in schedule:
                schedule_rows.append([
                    _paragraph(row.get("year"), centred_style),
                    _paragraph(_money(row.get("annual_rent")), body_style),
                    _paragraph(f"{float(row.get('discount_factor', 0)):.6f}", centred_style),
                    _paragraph(_money(row.get("present_value")), body_style),
                ])
            schedule_table = LongTable(schedule_rows, colWidths=[20 * mm, 52 * mm, 38 * mm, 60 * mm], repeatRows=1, hAlign="LEFT")
            schedule_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.35, LIGHT_GREY),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(schedule_table)
    else:
        missing = calculation.get("missing_fields") or []
        message = "Calculation is pending approved inputs"
        if missing:
            message += ": " + ", ".join(map(str, missing))
        story.append(_paragraph(message + ".", body_style))

    story.append(_heading("Source references", section_style))
    references = calculation.get("source_references") or []
    if references:
        story.append(_key_value_table([("Reference", value) for value in references], body_style, label_style))
    else:
        story.append(_paragraph("No calculation source references are recorded yet.", body_style))

    story.append(_heading("Workflow history", section_style))
    history_rows = [[
        _paragraph("Time (UTC)", table_header_style),
        _paragraph("Action", table_header_style),
        _paragraph("Stage change", table_header_style),
        _paragraph("Comment", table_header_style),
    ]]
    for event in workflow.get("events") or []:
        stage_change = f"{event.get('from') or '-'} to {event.get('to') or '-'}"
        history_rows.append([
            _paragraph(event.get("at"), small_style),
            _paragraph(event.get("action"), small_style),
            _paragraph(stage_change, small_style),
            _paragraph(event.get("comment") or "-", small_style),
        ])
    history_table = LongTable(history_rows, colWidths=[42 * mm, 35 * mm, 45 * mm, 48 * mm], repeatRows=1, hAlign="LEFT")
    history_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.35, LIGHT_GREY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(history_table)
    document.build(story)
    return buffer.getvalue()
