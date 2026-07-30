"""
bharathub/pdf_utils.py

ప్రాజెక్ట్ మొత్తంలో అన్ని PDF డాక్యుమెంట్‌లకీ (Invoice, Resume, Offer
Letter, Appointment Letter, Employment Letter) ఉమ్మడిగా ఉండే బ్రాండింగ్/
లేఅవుట్ బిల్డింగ్ బ్లాక్‌లు -- ఇంతకుముందు ఇవన్నీ బ్రౌజర్ "Print to PDF"
(window.print()) మీద ఆధారపడేవి (ఏ సర్వర్-సైడ్ PDF లైబ్రరీ లేదు కాబట్టి)
-- ఇప్పుడు ReportLab తో నిజమైన, ఇండస్ట్రీ-స్టాండర్డ్ PDF ఫైల్‌లు
సర్వర్ లోనే జనరేట్ అవుతాయి, ఏ బ్రౌజర్‌లో నైనా ఒకేలా కనిపిస్తాయి.

ఈ మాడ్యూల్ ఇచ్చేవి:
  - BRAND్ కలర్స్ (సైట్ CSS లో వాడే అవే హెక్స్ కోడ్‌లు: --primary,
    --accent, --muted, --border, --success)
  - Paragraph స్టైల్స్ (title, section heading, body, muted, table cell)
  - build_pdf_response(): ఒక BytesIO బఫర్ లో SimpleDocTemplate build
    చేసి, తుది HttpResponse (Content-Type: application/pdf,
    Content-Disposition) తిరిగి ఇస్తుంది -- ప్రతి డాక్యుమెంట్ దీన్నే
    కాల్ చేస్తుంది, ఫైల్ save/cleanup వంటివి పట్టించుకోవాల్సిన
    అవసరం లేదు.
  - _letterhead(): ప్రతి పేజీ పైన BharatHub పేరు + కింద ఒక పేజీ-నంబర్
    footer -- SimpleDocTemplate యొక్క onPage కాల్‌బ్యాక్ ద్వారా.
"""
import io

from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate

# సైట్ CSS (:root వేరియబుల్స్) లో వాడే అవే హెక్స్ కోడ్‌లు -- PDF, వెబ్
# పేజీ రెండూ ఒకే బ్రాండ్ లుక్ కలిగి ఉండటానికి.
NAVY = colors.HexColor("#1a365d")
ORANGE = colors.HexColor("#ff8c00")
MUTED = colors.HexColor("#6b7280")
BORDER = colors.HexColor("#e5e7eb")
SUCCESS = colors.HexColor("#16a34a")
LIGHT_BG = colors.HexColor("#f9fafb")
DARK_TEXT = colors.HexColor("#1f2937")

PAGE_MARGIN = 18 * mm


def get_styles():
    """ప్రతి డాక్యుమెంట్ జనరేటర్ వాడుకునే ఉమ్మడి Paragraph స్టైల్స్."""
    base = getSampleStyleSheet()
    styles = {
        "doc_title": ParagraphStyle(
            "doc_title", parent=base["Title"], fontName="Helvetica-Bold",
            fontSize=19, textColor=NAVY, alignment=TA_CENTER, spaceAfter=2,
        ),
        "doc_subtitle": ParagraphStyle(
            "doc_subtitle", parent=base["Normal"], fontName="Helvetica",
            fontSize=9.5, textColor=MUTED, alignment=TA_CENTER, spaceAfter=18,
        ),
        "h1_right": ParagraphStyle(
            "h1_right", parent=base["Title"], fontName="Helvetica-Bold",
            fontSize=18, textColor=NAVY, alignment=TA_RIGHT, spaceAfter=2,
        ),
        "meta_right": ParagraphStyle(
            "meta_right", parent=base["Normal"], fontName="Helvetica",
            fontSize=9, textColor=MUTED, alignment=TA_RIGHT,
        ),
        "section_label": ParagraphStyle(
            "section_label", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=9.5, textColor=NAVY, spaceBefore=14, spaceAfter=6,
            leading=12,
        ),
        "body": ParagraphStyle(
            "body", parent=base["Normal"], fontName="Helvetica",
            fontSize=10.5, textColor=DARK_TEXT, leading=17, spaceAfter=10,
        ),
        "name_title": ParagraphStyle(
            "name_title", parent=base["Title"], fontName="Helvetica-Bold",
            fontSize=22, textColor=NAVY, alignment=TA_LEFT, spaceAfter=2,
        ),
        "headline": ParagraphStyle(
            "headline", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=11, textColor=ORANGE, spaceAfter=6,
        ),
        "contact_line": ParagraphStyle(
            "contact_line", parent=base["Normal"], fontName="Helvetica",
            fontSize=9, textColor=MUTED, spaceAfter=12,
        ),
        "party_name": ParagraphStyle(
            "party_name", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=11, textColor=NAVY, spaceAfter=2,
        ),
        "party_line": ParagraphStyle(
            "party_line", parent=base["Normal"], fontName="Helvetica",
            fontSize=9, textColor=DARK_TEXT, leading=13,
        ),
        "party_label": ParagraphStyle(
            "party_label", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=8, textColor=MUTED, spaceAfter=4,
        ),
        "cell": ParagraphStyle(
            "cell", parent=base["Normal"], fontName="Helvetica",
            fontSize=9.5, textColor=DARK_TEXT, leading=13,
        ),
        "cell_label": ParagraphStyle(
            "cell_label", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=9.5, textColor=MUTED,
        ),
        "cell_value": ParagraphStyle(
            "cell_value", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=9.5, textColor=DARK_TEXT,
        ),
        "note": ParagraphStyle(
            "note", parent=base["Normal"], fontName="Helvetica-Oblique",
            fontSize=8.5, textColor=MUTED, leading=13,
            backColor=colors.HexColor("#fffbeb"), borderPadding=8,
        ),
        "footer": ParagraphStyle(
            "footer", parent=base["Normal"], fontName="Helvetica",
            fontSize=7.5, textColor=MUTED, alignment=TA_CENTER,
        ),
    }
    return styles


def _draw_letterhead(canvas_obj, doc, brand_subtitle=""):
    """ప్రతి పేజీ పైన ఒక సన్నని BharatHub బ్రాండ్ బార్ + కింద పేజీ
    నంబర్ -- SimpleDocTemplate యొక్క onFirstPage/onLaterPages
    కాల్‌బ్యాక్ గా వాడతాం (canvas-level డ్రాయింగ్, flowables కాదు,
    కాబట్టి ప్రతి పేజీ మీదా ఖచ్చితంగా అదే స్థానంలో కనిపిస్తుంది)."""
    canvas_obj.saveState()
    width, height = A4

    # top accent rule
    canvas_obj.setStrokeColor(NAVY)
    canvas_obj.setLineWidth(2)
    canvas_obj.line(PAGE_MARGIN, height - 14 * mm, width - PAGE_MARGIN, height - 14 * mm)

    canvas_obj.setFont("Helvetica-Bold", 9)
    canvas_obj.setFillColor(NAVY)
    canvas_obj.drawString(PAGE_MARGIN, height - 11 * mm, "BharatHub")
    if brand_subtitle:
        canvas_obj.setFont("Helvetica", 7.5)
        canvas_obj.setFillColor(MUTED)
        canvas_obj.drawRightString(width - PAGE_MARGIN, height - 11 * mm, brand_subtitle)

    # footer: page number
    canvas_obj.setFont("Helvetica", 7.5)
    canvas_obj.setFillColor(MUTED)
    canvas_obj.drawCentredString(
        width / 2, 10 * mm, f"Page {canvas_obj.getPageNumber()}",
    )
    canvas_obj.restoreState()


def build_pdf_response(filename, story, brand_subtitle=""):
    """story (ReportLab flowables జాబితా) తీసుకుని, letterhead తో ఒక
    పూర్తి PDF బిల్డ్ చేసి, దాన్ని నేరుగా డౌన్‌లోడ్ అయ్యేలా
    HttpResponse గా తిరిగి ఇస్తుంది. ప్రతి view ఇదే ఫంక్షన్ కాల్
    చేస్తుంది -- ఫైల్ handling/cleanup ఏమీ దీనికి బయట రాయాల్సిన
    అవసరం లేదు."""
    buffer = io.BytesIO()
    doc = BaseDocTemplate(
        buffer, pagesize=A4,
        topMargin=22 * mm, bottomMargin=16 * mm,
        leftMargin=PAGE_MARGIN, rightMargin=PAGE_MARGIN,
        title=filename,
    )
    frame = Frame(
        doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal",
    )

    def on_page(canvas_obj, doc_obj):
        _draw_letterhead(canvas_obj, doc_obj, brand_subtitle)

    template = PageTemplate(id="branded", frames=[frame], onPage=on_page)
    doc.addPageTemplates([template])
    doc.build(story)

    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
