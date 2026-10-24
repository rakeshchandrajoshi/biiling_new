"""Solar Rays quotation PDF engine. No Streamlit dependency.

All company details and module/make values are supplied via the snapshot;
this module does not invent financial or technical specifications.
"""
from __future__ import annotations

import base64
import math
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.platypus import (
    BaseDocTemplate, Frame, Image, PageBreak, PageTemplate,
    Paragraph, Spacer, Table, TableStyle,
)

ROOT = Path(__file__).resolve().parent
DEFAULT_LOGO_PATH = ROOT / "LOGO_SOLARNEW.jpg"
PAGE_W, PAGE_H = A4
SOLAR = colors.HexColor("#F6B80E")
DARK = colors.HexColor("#B9810A")
NAVY = colors.HexColor("#172438")
SLATE = colors.HexColor("#526277")
BORDER = colors.HexColor("#CFD8E3")
LIGHT = colors.HexColor("#F7F9FC")
WHITE = colors.white
DEFAULT_NAME = "SOLAR RAYS ENERGY SOLUTIONS LLP"
DEFAULT_ADDRESS = "12A/220, VRINDAVAN COLONY Utrahtia Railway Station Lucknow, Lucknow, Uttar Pradesh, 226029"


def money(value: Any) -> str:
    try:
        return f"INR {float(value):,.2f}"
    except (ValueError, TypeError):
        return "INR 0.00"


def safe_para(value: Any, style: ParagraphStyle) -> Paragraph:
    text = "" if value is None else str(value)
    return Paragraph(escape(text).replace("\n", "<br/>"), style)


def _logo_source(settings: Dict[str, Any]):
    encoded = settings.get("logo_b64", "")
    if encoded:
        try:
            data = base64.b64decode(encoded, validate=True)
            if data:
                return BytesIO(data)
        except (ValueError, TypeError, base64.binascii.Error):
            pass
    return str(DEFAULT_LOGO_PATH) if DEFAULT_LOGO_PATH.is_file() else None


def _logo_flowable(settings: Dict[str, Any], max_width=32*mm, max_height=19*mm):
    source = _logo_source(settings)
    if source is None:
        return safe_para("SOLAR RAYS", ParagraphStyle("logofallback", fontName="Helvetica-Bold", fontSize=12, textColor=NAVY))
    try:
        image = Image(source)
        ratio = min(max_width/image.imageWidth, max_height/image.imageHeight)
        image.drawWidth = image.imageWidth * ratio
        image.drawHeight = image.imageHeight * ratio
        return image
    except Exception:
        return safe_para("SOLAR RAYS", ParagraphStyle("logofallback", fontName="Helvetica-Bold", fontSize=12, textColor=NAVY))


def _header_footer(canvas, doc, settings):
    canvas.saveState()
    canvas.setFillColor(SOLAR)
    canvas.rect(0, PAGE_H - 8*mm, PAGE_W, 8*mm, stroke=0, fill=1)
    source = _logo_source(settings)
    if source is not None:
        try:
            canvas.drawImage(ImageReader(source), 16*mm, PAGE_H - 31*mm, width=24*mm, height=21*mm,
                             preserveAspectRatio=True, anchor="c", mask="auto")
        except Exception:
            pass
    name = str(settings.get("company_name") or DEFAULT_NAME).upper()
    canvas.setFillColor(NAVY)
    canvas.setFont("Helvetica-Bold", 10.5)
    canvas.drawString(43*mm, PAGE_H - 16.2*mm, name[:55])
    canvas.setFont("Helvetica", 7.4)
    canvas.setFillColor(SLATE)
    canvas.drawString(43*mm, PAGE_H - 21.1*mm, str(settings.get("tagline") or "Solar Power & Energy Solutions")[:75])
    legal_line = f"GSTIN: {settings.get('gstin','')}     State Code: {settings.get('state_code','09')}     State: {settings.get('state','Uttar Pradesh')}"
    canvas.drawString(43*mm, PAGE_H - 26*mm, legal_line[:110])
    canvas.setStrokeColor(BORDER)
    canvas.line(16*mm, PAGE_H - 33*mm, PAGE_W - 16*mm, PAGE_H - 33*mm)

    canvas.setStrokeColor(DARK)
    canvas.line(16*mm, 16*mm, PAGE_W-16*mm, 16*mm)
    canvas.setFillColor(SLATE)
    canvas.setFont("Helvetica", 6.6)
    footer = "  |  ".join(filter(None, [settings.get("website", ""), settings.get("email", ""), settings.get("phone1", "")]))
    canvas.drawString(16*mm, 11*mm, str(footer)[:105])
    canvas.drawRightString(PAGE_W-16*mm, 11*mm, f"Page {doc.page}")
    canvas.restoreState()


def styles():
    base = getSampleStyleSheet()
    return {
        "hero": ParagraphStyle("SRHero", parent=base["Heading1"], fontName="Helvetica-Bold", fontSize=23, leading=27, textColor=NAVY, spaceAfter=6),
        "title": ParagraphStyle("SRTitle", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=16, leading=19, textColor=NAVY, spaceAfter=6),
        "h2": ParagraphStyle("SRH2", parent=base["Heading3"], fontName="Helvetica-Bold", fontSize=11, leading=13, textColor=NAVY, spaceBefore=7, spaceAfter=5),
        "body": ParagraphStyle("SRBody", parent=base["BodyText"], fontSize=9.0, leading=13.7, textColor=NAVY, spaceAfter=6),
        "small": ParagraphStyle("SRSmall", parent=base["BodyText"], fontSize=7.6, leading=10.2, textColor=NAVY),
        "tiny": ParagraphStyle("SRTiny", parent=base["BodyText"], fontSize=7.0, leading=8.8, textColor=NAVY),
        "bold": ParagraphStyle("SRBold", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=7.7, leading=10, textColor=NAVY),
        "th": ParagraphStyle("SRTH", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=7.4, leading=9.2, textColor=WHITE),
        "right": ParagraphStyle("SRRight", parent=base["BodyText"], alignment=TA_RIGHT, fontSize=7.7, textColor=NAVY),
        "center": ParagraphStyle("SRCenter", parent=base["BodyText"], alignment=TA_CENTER, fontSize=10, textColor=SLATE, spaceAfter=6),
    }


def basic_table(rows, ss, widths=(39*mm, 136*mm)):
    contents = [[safe_para(label, ss["bold"]), safe_para(value, ss["small"])] for label, value in rows]
    table = Table(contents, colWidths=list(widths), hAlign="LEFT", repeatRows=0)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), LIGHT),
        ("GRID", (0, 0), (-1, -1), 0.40, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def detail_table(records, columns, widths, ss):
    entries = [[safe_para(c, ss["th"]) for c in columns]]
    for item in records:
        entries.append([safe_para(item.get(c, ""), ss["tiny"]) for c in columns])
    table = Table(entries, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.38, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def default_boq(project: Dict[str, Any]) -> List[Dict[str, Any]]:
    cap = float(project.get("capacity_kw", 5) or 5)
    watt = int(project.get("panel_wattage", 580) or 580)
    panels = int(math.ceil(cap * 1000 / watt))
    return [
        {"S.No.": 1, "Description": f"Solar PV array - {cap:g} kW system using {watt} Wp modules", "Make": project.get("panel_brand", "As selected"), "Unit": "Wp", "Qty": panels},
        {"S.No.": 2, "Description": f"{project.get('system_type', 'On-Grid')} solar inverter", "Make": project.get("inverter_brand", "As selected"), "Unit": "kW", "Qty": project.get("inverter_capacity_kw", cap)},
        {"S.No.": 3, "Description": "Module mounting structure with required fasteners for rooftop installation", "Make": project.get("structure_make", "GI / HDG"), "Unit": "Set", "Qty": 1},
        {"S.No.": 4, "Description": "ACDB / DCDB, surge protection and electrical protection", "Make": "As per approved design", "Unit": "Set", "Qty": 1},
        {"S.No.": 5, "Description": "AC/DC cables, conduit, junctions, connectors and accessories", "Make": "As per approved design", "Unit": "Lot", "Qty": 1},
        {"S.No.": 6, "Description": "Earthing system and lightning protection", "Make": "As per approved design", "Unit": "Set", "Qty": 1},
        {"S.No.": 7, "Description": "Installation, testing and commissioning", "Make": "Solar Rays", "Unit": "Job", "Qty": 1},
    ]


def default_materials(project: Dict[str, Any]) -> List[Dict[str, Any]]:
    cap = float(project.get("capacity_kw", 5) or 5)
    watt = int(project.get("panel_wattage", 580) or 580)
    panels = int(math.ceil(cap * 1000 / watt))
    return [
        {"S.No.": 1, "Component": "Solar PV Modules", "Description": f"Bifacial Mono PERC / TOPCon modules, approx. {watt} Wp each", "Quantity": f"{panels} Nos.", "Make": project.get("panel_brand", "As selected")},
        {"S.No.": 2, "Component": "Inverter / PCU", "Description": f"{project.get('system_type', 'On-Grid')} inverter, {project.get('phase', '')}", "Quantity": f"{project.get('inverter_capacity_kw', cap)} kW / 1 No.", "Make": project.get("inverter_brand", "As selected")},
        {"S.No.": 3, "Component": "DC Distribution Box", "Description": "IP65 enclosure, DC protection, SPD, fuses as required", "Quantity": "1 Set", "Make": "As per approved design"},
        {"S.No.": 4, "Component": "AC Distribution Box", "Description": "IP65 enclosure, MCB/MCCB, SPD and protection", "Quantity": "1 Set", "Make": "As per approved design"},
        {"S.No.": 5, "Component": "AC Cable", "Description": "Copper / aluminium cable as per approved design", "Quantity": "As per system", "Make": "Standard approved make"},
        {"S.No.": 6, "Component": "Interconnecting DC Cable", "Description": "UV resistant rated solar DC cable", "Quantity": "As per system", "Make": "Standard approved make"},
        {"S.No.": 7, "Component": "Module Mounting Structure", "Description": "GI / HDG structure as per module layout", "Quantity": "As per module layout", "Make": project.get("structure_make", "GI / HDG")},
        {"S.No.": 8, "Component": "Earthing Cable", "Description": "Copper / GI conductor sized for design", "Quantity": "As per system", "Make": "Standard approved make"},
        {"S.No.": 9, "Component": "Earthing", "Description": "Earth electrodes / rods with accessories", "Quantity": "3 Sets (typical)", "Make": "Standard approved make"},
        {"S.No.": 10, "Component": "Lightning Arrestor", "Description": "Lightning protection with supports", "Quantity": "1 Set", "Make": "Standard approved make"},
    ]


def generate_quote_pdf(data: Dict[str, Any]) -> bytes:
    """Generate printable quotation PDF from a saved snapshot."""
    settings = data.get("settings", {})
    customer = data.get("customer", {})
    project = data.get("project", {})
    commercial = data.get("commercial", {})
    terms = data.get("terms", {})
    boq = data.get("boq", []) or default_boq(project)
    materials = data.get("materials", []) or default_materials(project)
    ss = styles()
    out = BytesIO()
    doc = BaseDocTemplate(out, pagesize=A4, leftMargin=17*mm, rightMargin=17*mm,
                          topMargin=37*mm, bottomMargin=20*mm,
                          title=f"Solar quotation {data.get('quote_ref', '')}",
                          author=str(settings.get("company_name") or DEFAULT_NAME).upper())
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, leftPadding=0,
                  rightPadding=0, bottomPadding=0, topPadding=0, id="quotation-frame")
    doc.addPageTemplates(PageTemplate(id="quotation", frames=[frame],
                                  onPage=lambda canvas, d: _header_footer(canvas, d, settings)))
    story = []
    company_name = str(settings.get("company_name") or DEFAULT_NAME).upper()
    registered_address = settings.get("registered_address") or settings.get("office_address") or DEFAULT_ADDRESS

    # 1 — Proposal / company & technical summary
    story.append(safe_para("SOLAR POWER PROPOSAL", ss["hero"]))
    story.append(safe_para(f"{project.get('capacity_kw', '')} kW {project.get('system_type', '')} Solar Power Project", ss["center"]))
    story.append(Spacer(1, 3*mm))
    story.append(basic_table([
        ("Prepared for", customer.get("name", "")),
        ("Quotation reference", data.get("quote_ref", "")),
        ("Date", data.get("quote_date", "")),
        ("Customer contact", customer.get("phone", "")),
        ("Customer address", customer.get("address", "")),
        ("Customer GSTIN", customer.get("gstin", "")),
    ], ss))
    story.append(Spacer(1, 6*mm))
    story.append(safe_para("About the Company", ss["h2"]))
    story.append(safe_para(settings.get("intro_text") or (
        "SOLAR RAYS ENERGY SOLUTIONS LLP designs, installs and maintains rooftop solar power systems "
        "focused on reliable engineering, clean energy and long-term savings."), ss["body"]))
    story.append(safe_para("Company Registration Details", ss["h2"]))
    story.append(basic_table([
        ("Legal name", company_name),
        ("Registered address", registered_address),
        ("GSTIN", settings.get("gstin", "")),
        ("State code / State", f"{settings.get('state_code', '09')} / {settings.get('state', 'Uttar Pradesh')}"),
    ], ss))
    story.append(safe_para("Project Snapshot", ss["h2"]))
    story.append(basic_table([
        ("System / Capacity", f"{project.get('system_type', '')} / {project.get('capacity_kw', '')} kW"),
        ("Phase", project.get("phase", "")),
        ("Solar module make", f"{project.get('panel_brand', '')} — {project.get('panel_wattage', '')} Wp"),
        ("Number of panels", project.get("panel_count", "")),
        ("Inverter", f"{project.get('inverter_brand', '')} — {project.get('inverter_capacity_kw', '')} kW"),
    ], ss))
    story.append(PageBreak())

    # 2 — Commercial quote
    story.append(safe_para("COMMERCIAL QUOTATION", ss["title"]))
    story.append(safe_para(f"Customer: {customer.get('name', '')}  |  Ref: {data.get('quote_ref', '')}", ss["small"]))
    story.append(Spacer(1, 4*mm))
    story.append(safe_para("Bill of Quantities (BOQ)", ss["h2"]))
    story.append(detail_table(boq, ["S.No.", "Description", "Make", "Unit", "Qty"],
                              [12*mm, 81*mm, 49*mm, 17*mm, 16*mm], ss))
    story.append(Spacer(1, 4*mm))
    summary = [
        ("Basic amount", money(commercial.get("basic_amount", 0))),
        ("Discount", money(commercial.get("discount", 0))),
        ("Taxable value", money(commercial.get("taxable_value", 0))),
        (f"GST @ {commercial.get('gst_rate', 0)}%", money(commercial.get("gst_amount", 0))),
        ("Other charges", money(commercial.get("other_charges", 0))),
        ("Grand total", money(commercial.get("grand_total", 0))),
    ]
    if float(commercial.get("total_subsidy", 0) or 0) > 0:
        summary.extend([
            ("Indicative total subsidy", money(commercial.get("total_subsidy", 0))),
            ("Effective cost after indicative subsidy", money(commercial.get("effective_price", 0))),
        ])
    story.append(safe_para("Commercial Summary", ss["h2"]))
    story.append(basic_table(summary, ss, widths=(91*mm, 84*mm)))
    if float(commercial.get("total_subsidy", 0) or 0) > 0:
        story.append(Spacer(1, 2*mm))
        story.append(safe_para(commercial.get("subsidy_note", "Subsidy is indicative and subject to eligibility and applicable government rules."), ss["tiny"]))
    story.append(safe_para("Terms & Conditions", ss["h2"]))
    term_lines = [
        f"Quotation valid for {terms.get('validity_days', 10)} days",
        f"Payment: {terms.get('payment_terms', '')}",
        f"Delivery / commissioning: {terms.get('delivery_timeline', '')}",
        f"Net-metering: {terms.get('net_metering', '')}",
        f"Warranty: {terms.get('warranty', '')}",
    ]
    for line in term_lines:
        story.append(safe_para("• " + line, ss["tiny"]))
    if any(settings.get(k) for k in ("bank_name", "bank_account", "ifsc")):
        story.append(safe_para("Payment Details", ss["h2"]))
        story.append(basic_table([
            ("Account name", settings.get("bank_account_name", company_name)),
            ("Bank / branch", f"{settings.get('bank_name', '')} / {settings.get('bank_branch', '')}"),
            ("Account / IFSC", f"{settings.get('bank_account', '')} / {settings.get('ifsc', '')}"),
        ], ss))
    story.append(PageBreak())

    # 3 — Material details
    story.append(safe_para("DETAILED MATERIAL SPECIFICATIONS", ss["title"]))
    story.append(safe_para("Final selected makes and specifications are shown below.", ss["small"]))
    story.append(Spacer(1, 4*mm))
    story.append(detail_table(materials, ["S.No.", "Component", "Description", "Quantity", "Make"],
                              [12*mm, 39*mm, 59*mm, 24*mm, 41*mm], ss))
    story.append(Spacer(1, 5*mm))
    story.append(safe_para("Material Note", ss["h2"]))
    story.append(safe_para(terms.get("material_note", "Final make, models and quantities subject to approved design and mutual agreement."), ss["tiny"]))
    story.append(safe_para("Company Details", ss["h2"]))
    story.append(basic_table([
        ("Name", company_name),
        ("Registered address", registered_address),
        ("GSTIN", settings.get("gstin", "")),
        ("State code / State", f"{settings.get('state_code', '09')} / {settings.get('state', 'Uttar Pradesh')}"),
        ("Website", settings.get("website", "")),
        ("Email / Phone", " / ".join(filter(None, [settings.get("email", ""), settings.get("phone1", ""), settings.get("phone2", "")]))),
    ], ss))
    story.append(Spacer(1, 5*mm))
    story.append(safe_para(f"For {company_name}", ss["bold"]))
    story.append(Spacer(1, 5*mm))
    story.append(safe_para("Authorized Signatory", ss["small"]))

    doc.build(story)
    return out.getvalue()
