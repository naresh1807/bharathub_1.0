"""
shopping/pdf_invoice.py

ఒక Order యొక్క B2B Tax Invoice -- ఇంతకుముందు shopping/templates/
shopping/invoice.html "Download" బటన్ కేవలం బ్రౌజర్ ప్రింట్ డైలాగ్ నే
తెరిచేది (window.print()). ఇప్పుడు ఇక్కడి generate_invoice_pdf() ఒక
నిజమైన PDF ఫైల్ ని ReportLab తో సర్వర్ లోనే జనరేట్ చేస్తుంది --
invoice.html లో ఉన్న అదే డేటా (Sold By / Billed To GST వివరాలు,
లైన్ ఐటమ్స్, టోటల్, స్టేటస్) ఖచ్చితంగా అదే వరుసలో.
"""
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

from bharathub.pdf_utils import (
    BORDER, DARK_TEXT, LIGHT_BG, MUTED, NAVY, ORANGE, SUCCESS,
    build_pdf_response, get_styles,
)


def _party_cell(label, name, lines, gst_number, pan_number, styles):
    """'Sold By' / 'Billed To' బాక్స్ లోపలి కంటెంట్ -- ఒక చిన్న
    flowables జాబితాగా, ఇది తర్వాత ఒక టేబుల్ సెల్ లో పెడతాం (బాక్స్
    బోర్డర్ ఆ టేబుల్ యొక్క గ్రిడ్ లైన్ నుండే వస్తుంది)."""
    content = [
        Paragraph(label, styles["party_label"]),
        Paragraph(name, styles["party_name"]),
    ]
    for line in lines:
        if line:
            content.append(Paragraph(line, styles["party_line"]))
    if gst_number:
        content.append(Spacer(1, 3))
        content.append(Paragraph(f"<b>GSTIN:</b> {gst_number}", styles["party_line"]))
    if pan_number:
        content.append(Paragraph(f"<b>PAN:</b> {pan_number}", styles["party_line"]))
    return content


def generate_invoice_pdf(order):
    """order (shopping.models.Order, items prefetch చేసి ఉండాలి) తీసుకుని,
    ఒక HttpResponse (PDF attachment) తిరిగి ఇస్తుంది. Caller (views.py)
    ఓనర్‌షిప్/IDOR చెక్ ఇప్పటికే చేసి ఉంటుంది."""
    styles = get_styles()
    story = []

    # ── TITLE ROW: "TAX INVOICE" + Invoice #/date (కుడివైపు) ──
    header_table = Table(
        [[
            Paragraph("BharatHub Marketplace", styles["party_name"]),
            [
                Paragraph("TAX INVOICE", styles["h1_right"]),
                Paragraph(
                    f"Invoice #{order.pk} &nbsp;·&nbsp; {order.created_at:%B %d, %Y}",
                    styles["meta_right"],
                ),
            ],
        ]],
        colWidths=[90 * mm, None],
    )
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LINEBELOW", (0, 0), (-1, -1), 2, NAVY),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 14))

    # ── PARTIES: Sold By / Billed To (రెండు కాలమ్‌ల బాక్స్‌లు) ──
    seller_lines = [
        order.vendor.owner_name if getattr(order.vendor, "owner_name", None) else "",
        order.vendor.address if order.vendor.address else "",
        f"{order.vendor.vendor_email}" + (f" · {order.vendor.vendor_mobile}" if order.vendor.vendor_mobile else ""),
    ]
    buyer_lines = [
        order.buyer.contact_person if order.buyer.contact_person else "",
        order.buyer.address if order.buyer.address else "",
        f"{order.buyer.corporate_email}" + (f" · {order.buyer.mobile_number}" if order.buyer.mobile_number else ""),
    ]
    parties_table = Table(
        [[
            _party_cell(
                "SOLD BY", order.vendor.shop_name, seller_lines,
                getattr(order.vendor, "gst_number", ""), getattr(order.vendor, "pan_number", ""), styles,
            ),
            _party_cell(
                "BILLED TO", order.buyer.company_name, buyer_lines,
                getattr(order.buyer, "gst_number", ""), getattr(order.buyer, "pan_number", ""), styles,
            ),
        ]],
        colWidths=[85 * mm, 85 * mm],
    )
    parties_table.setStyle(TableStyle([
        ("BOX", (0, 0), (0, 0), 1, BORDER),
        ("BOX", (1, 0), (1, 0), 1, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(parties_table)
    story.append(Spacer(1, 12))

    if order.delivery_address:
        ship_table = Table(
            [[[
                Paragraph("📍 SHIP TO", styles["party_label"]),
                Paragraph(order.delivery_address.replace("\n", "<br/>"), styles["party_line"]),
            ]]],
            colWidths=[170 * mm],
        )
        ship_table.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 1, BORDER),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(ship_table)
        story.append(Spacer(1, 12))

    # ── LINE ITEMS TABLE ──
    item_rows = [["ITEM", "QTY", "UNIT PRICE", "AMOUNT"]]
    for item in order.items.all():
        item_rows.append([
            Paragraph(item.product.name, styles["cell"]),
            str(item.quantity),
            f"Rs. {item.price_at_order}",
            f"Rs. {item.line_total}",
        ])
    items_table = Table(item_rows, colWidths=[90 * mm, 20 * mm, 30 * mm, 30 * mm])
    items_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8.5),
        ("TEXTCOLOR", (0, 0), (-1, 0), MUTED),
        ("LINEBELOW", (0, 0), (-1, 0), 1.2, BORDER),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 9.5),
        ("TEXTCOLOR", (0, 1), (-1, -1), DARK_TEXT),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("LINEBELOW", (0, 1), (-1, -1), 0.5, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 10))

    # ── TOTAL ──
    total_table = Table(
        [["Total", f"Rs. {order.total_amount}"]], colWidths=[140 * mm, 30 * mm],
    )
    total_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 13),
        ("TEXTCOLOR", (0, 0), (-1, -1), NAVY),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("LINEABOVE", (0, 0), (-1, 0), 1.5, NAVY),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(total_table)
    story.append(Spacer(1, 14))

    # ── STATUS CHIP ──
    status_table = Table(
        [[order.get_status_display().upper()]], colWidths=[45 * mm],
    )
    status_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.Color(0.086, 0.639, 0.29, 0.12)),
        ("TEXTCOLOR", (0, 0), (-1, -1), SUCCESS),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(status_table)
    story.append(Spacer(1, 20))

    story.append(Paragraph(
        f"This invoice was generated by BharatHub based on platform order records "
        f"&middot; Order Reference: ORD-{order.pk}",
        styles["footer"],
    ))

    return build_pdf_response(
        f"BharatHub_Invoice_ORD-{order.pk}.pdf", story,
        brand_subtitle=f"Tax Invoice · Order #{order.pk}",
    )
