import io
import os
import re
from datetime import timedelta
import qrcode
from PIL import Image as PILImage, ImageDraw, ImageFont
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.graphics.shapes import Drawing, Rect, Line, String
from app.services.qr_service import qr_service
from app.models.booking import Booking
from app.models.ticket import Ticket
from app.models.event_setting import EventSetting
from app.models.offers import get_offer_by_id

class TicketService:
    @classmethod
    def _get_font(cls, font_filename: str, size: int) -> ImageFont.ImageFont:
        """Loads bundled TrueType font with fallbacks to system fonts or default."""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        bundled_font = os.path.join(base_dir, "static", "fonts", font_filename)
        if os.path.exists(bundled_font):
            try:
                return ImageFont.truetype(bundled_font, size)
            except Exception:
                pass

        # Windows fallback
        win_font = os.path.join(r"C:\Windows\Fonts", font_filename)
        if os.path.exists(win_font):
            try:
                return ImageFont.truetype(win_font, size)
            except Exception:
                pass

        # Linux / container fallbacks
        linux_paths = [
            f"/usr/share/fonts/truetype/dejavu/{font_filename}",
            f"/usr/share/fonts/truetype/freefont/{font_filename}",
            f"/usr/share/fonts/truetype/liberation/{font_filename}",
        ]
        for lp in linux_paths:
            if os.path.exists(lp):
                try:
                    return ImageFont.truetype(lp, size)
                except Exception:
                    pass
        return ImageFont.load_default()

    @classmethod
    def generate_ticket_image_bytes(cls, booking: Booking, ticket: Ticket, event_setting: EventSetting) -> bytes:
        """
        Renders the official NAVRANG 2026 admission pass image matching the uploaded design:
        - Deep Midnight Navy banner (#1C1949) with Orange (#EA580C) title, Gold (#FBBF24) collaboration, and warm Gold tagline
        - 4-column white metadata grid with light borders (#E2E8F0)
        - Clean scannable QR code
        - Pale cream (#FFFDF5) important venue instructions box with amber border (#FDE68A)
        - Synchronized event timings: 06:30 PM - 10:00 PM (Gates open 06:30 PM)
        Returns JPEG bytes.
        """
        width = 1000
        height = 680
        img = PILImage.new("RGB", (width, height), "#FFFFFF")
        draw = ImageDraw.Draw(img)

        # 1. Official Header Banner (#1C1949)
        header_height = 150
        draw.rectangle([(0, 0), (width, header_height)], fill="#1C1949")

        font_title = cls._get_font("arialbd.ttf", 28)
        font_collab = cls._get_font("arialbd.ttf", 12)
        font_tagline = cls._get_font("georgiai.ttf", 13)
        font_badge = cls._get_font("arialbd.ttf", 14)

        title_text = f"❖ {event_setting.event_name.upper()} ❖"
        bbox = draw.textbbox((0, 0), title_text, font=font_title)
        draw.text(((width - (bbox[2] - bbox[0])) // 2, 16), title_text, fill="#EA580C", font=font_title)

        collab_text = "IN COLLABORATION WITH THE HAPPY CIRCLE"
        bbox = draw.textbbox((0, 0), collab_text, font=font_collab)
        draw.text(((width - (bbox[2] - bbox[0])) // 2, 58), collab_text, fill="#FBBF24", font=font_collab)

        tagline_text = event_setting.event_tagline or "Celebrate. Dance. Connect."
        bbox = draw.textbbox((0, 0), tagline_text, font=font_tagline)
        draw.text(((width - (bbox[2] - bbox[0])) // 2, 84), tagline_text, fill="#FCD34D", font=font_tagline)

        badge_text = f"OFFICIAL ENTRY PASS — PASS 1 OF {booking.ticket_count}"
        bbox = draw.textbbox((0, 0), badge_text, font=font_badge)
        draw.text(((width - (bbox[2] - bbox[0])) // 2, 114), badge_text, fill="#FFFFFF", font=font_badge)

        # 2. 4-Column Ticket Metadata Grid
        grid_x0 = 30
        grid_x1 = width - 30
        grid_y0 = 170
        row_h = 65
        col_w = (grid_x1 - grid_x0) / 4

        draw.rectangle([(grid_x0, grid_y0), (grid_x1, grid_y0 + 2 * row_h)], fill="#FFFFFF", outline="#E2E8F0", width=1)
        draw.line([(grid_x0, grid_y0 + row_h), (grid_x1, grid_y0 + row_h)], fill="#E2E8F0", width=1)
        for i in range(1, 4):
            x = grid_x0 + i * col_w
            draw.line([(x, grid_y0), (x, grid_y0 + 2 * row_h)], fill="#E2E8F0", width=1)

        font_label = cls._get_font("arialbd.ttf", 10)
        font_val = cls._get_font("arialbd.ttf", 13)
        font_subval = cls._get_font("arial.ttf", 11)

        cust_name = getattr(ticket, "customer_name", None) or getattr(booking, "customer_name", "ATTENDEE")
        tkt_no = getattr(ticket, "ticket_id", None) or f"{booking.booking_id}-01"
        price_val = getattr(ticket, "ticket_price", None) or (booking.amount / max(1, booking.ticket_count)) if booking.amount else 599

        # Row 1
        draw.text((grid_x0 + 12, grid_y0 + 10), "ATTENDEE NAME", fill="#64748B", font=font_label)
        draw.text((grid_x0 + 12, grid_y0 + 28), str(cust_name)[:22], fill="#0F172A", font=font_val)

        draw.text((grid_x0 + col_w + 12, grid_y0 + 10), "BOOKING ID", fill="#64748B", font=font_label)
        draw.text((grid_x0 + col_w + 12, grid_y0 + 28), str(booking.booking_id), fill="#0F172A", font=font_val)

        draw.text((grid_x0 + 2 * col_w + 12, grid_y0 + 10), "TICKET NUMBER", fill="#64748B", font=font_label)
        draw.text((grid_x0 + 2 * col_w + 12, grid_y0 + 28), str(tkt_no)[:20], fill="#0F172A", font=font_val)

        draw.text((grid_x0 + 3 * col_w + 12, grid_y0 + 10), "PASS ORDER", fill="#64748B", font=font_label)
        draw.text((grid_x0 + 3 * col_w + 12, grid_y0 + 28), f"Pass 1 of {booking.ticket_count}", fill="#0F172A", font=font_val)

        # Row 2
        draw.text((grid_x0 + 12, grid_y0 + row_h + 8), "EVENT DATE & TIME", fill="#64748B", font=font_label)
        draw.text((grid_x0 + 12, grid_y0 + row_h + 24), str(event_setting.event_date), fill="#0F172A", font=font_subval)
        draw.text((grid_x0 + 12, grid_y0 + row_h + 40), "06:30 PM - 10:00 PM", fill="#64748B", font=font_subval)

        draw.text((grid_x0 + col_w + 12, grid_y0 + row_h + 8), "VENUE LOCATION", fill="#64748B", font=font_label)
        draw.text((grid_x0 + col_w + 12, grid_y0 + row_h + 24), str(event_setting.venue_name), fill="#0F172A", font=font_val)
        draw.text((grid_x0 + col_w + 12, grid_y0 + row_h + 42), f"{event_setting.venue_address}, {event_setting.venue_city}"[:28], fill="#64748B", font=font_subval)

        draw.text((grid_x0 + 2 * col_w + 12, grid_y0 + row_h + 8), "PAYMENT STATUS", fill="#64748B", font=font_label)
        draw.text((grid_x0 + 2 * col_w + 12, grid_y0 + row_h + 28), f"✓ PAID (Rs. {int(price_val)})", fill="#0F172A", font=font_val)

        draw.text((grid_x0 + 3 * col_w + 12, grid_y0 + row_h + 8), "TICKET STATUS", fill="#64748B", font=font_label)
        draw.text((grid_x0 + 3 * col_w + 12, grid_y0 + row_h + 28), "● VALID", fill="#0F172A", font=font_val)

        # 3. Dynamic QR Code
        qr_payload = getattr(ticket, "qr_token_raw", None) or getattr(booking, "booking_id", "NAV2026")
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=3, border=1)
        qr.add_data(qr_payload)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="#000000", back_color="#FFFFFF").convert("RGB")
        qr_img = qr_img.resize((150, 150), PILImage.Resampling.LANCZOS)
        
        qr_x = grid_x0 + 15
        qr_y = 320
        draw.rectangle([(qr_x - 4, qr_y - 4), (qr_x + 154, qr_y + 154)], fill="#FFFFFF", outline="#CBD5E1", width=1)
        img.paste(qr_img, (qr_x, qr_y))

        # 4. Important Venue Instructions Box (#FFFDF5, border #FDE68A)
        inst_x0 = qr_x + 175
        inst_x1 = grid_x1
        inst_y0 = 315
        inst_y1 = 485
        draw.rectangle([(inst_x0, inst_y0), (inst_x1, inst_y1)], fill="#FFFDF5", outline="#FDE68A", width=1)

        font_inst_head = cls._get_font("arialbd.ttf", 11)
        font_inst_text = cls._get_font("arial.ttf", 10)
        draw.text((inst_x0 + 14, inst_y0 + 12), "IMPORTANT VENUE INSTRUCTIONS", fill="#B45309", font=font_inst_head)

        bullets = [
            "• Gates open promptly at 06:30 PM. Show this barcode or digital pass at turnstiles.",
            "• Event Timings: 06:30 PM onwards till 10:00 PM. Gates close at 10:00 PM.",
            "• Entry will be granted only after successful QR scanning at security.",
            "• Each QR code is uniquely encrypted and admits exactly one person once.",
            "• Traditional festive attire is celebrated and recommended.",
            "• Carry valid Government photo ID matching the attendee name."
        ]
        b_y = inst_y0 + 34
        for b_text in bullets:
            draw.text((inst_x0 + 14, b_y), b_text, fill="#334155", font=font_inst_text)
            b_y += 18

        # 5. Footer Line
        font_footer = cls._get_font("arial.ttf", 10)
        footer_text = f"Pass 1 of {booking.ticket_count} • Booking #{booking.booking_id} • {event_setting.event_name} × THE HAPPY CIRCLE Official E-Ticket"
        bbox = draw.textbbox((0, 0), footer_text, font=font_footer)
        draw.text(((width - (bbox[2] - bbox[0])) // 2, 510), footer_text, fill="#64748B", font=font_footer)

        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=95)
        return buffer.getvalue()

    @classmethod
    def generate_single_ticket_pdf(cls, booking: Booking, ticket: Ticket, event_setting: EventSetting) -> bytes:
        """Generates a professional, print-ready PDF for a single ticket matching the official ticket pass design."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=32,
            bottomMargin=32
        )

        story = []
        styles = getSampleStyleSheet()

        # Custom Styles matching the official ticket design
        title_style = ParagraphStyle(
            "EventTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=24,
            textColor=colors.HexColor("#EA580C"), # Vibrant Orange
            alignment=1, # Center
            spaceAfter=4
        )
        collab_style = ParagraphStyle(
            "EventCollab",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=colors.HexColor("#FBBF24"), # Radiant Gold
            alignment=1,
            spaceAfter=4
        )
        tagline_style = ParagraphStyle(
            "EventTagline",
            parent=styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=11,
            textColor=colors.HexColor("#FCD34D"), # Warm Gold Italic
            alignment=1,
            spaceAfter=10
        )
        badge_style = ParagraphStyle(
            "BadgeStyle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=13,
            textColor=colors.white,
            alignment=1
        )
        label_style = ParagraphStyle(
            "LabelStyle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            textColor=colors.HexColor("#64748B") # Slate Gray
        )
        val_style = ParagraphStyle(
            "ValStyle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=colors.HexColor("#0F172A") # Near Black
        )
        sub_val_style = ParagraphStyle(
            "SubValStyle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            textColor=colors.HexColor("#334155")
        )
        footer_style = ParagraphStyle(
            "FooterStyle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            textColor=colors.HexColor("#64748B"),
            alignment=1
        )

        # 1. Official Deep Navy / Indigo Header Banner
        header_data = [
            [Paragraph(f"&#10070; {event_setting.event_name.upper()} &#10070;", title_style)],
            [Paragraph("IN COLLABORATION WITH THE HAPPY CIRCLE", collab_style)],
            [Paragraph("Celebrate. Dance. Connect.", tagline_style)],
            [Paragraph("OFFICIAL ENTRY PASS — PASS 1 OF 1", badge_style)]
        ]
        header_table = Table(header_data, colWidths=[540])
        header_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#1C1949")), # Royal Midnight Indigo
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 10))

        # 2. 4-Column Ticket Metadata Grid
        details_data = [
            [
                Paragraph("ATTENDEE NAME", label_style),
                Paragraph("BOOKING ID", label_style),
                Paragraph("TICKET NUMBER", label_style),
                Paragraph("PASS ORDER", label_style),
            ],
            [
                Paragraph(f"{ticket.customer_name}", val_style),
                Paragraph(f"{booking.booking_id}", val_style),
                Paragraph(f"{ticket.ticket_id}", val_style),
                Paragraph("Pass 1 of 1", val_style),
            ],
            [
                Paragraph("EVENT DATE & TIME", label_style),
                Paragraph("VENUE LOCATION", label_style),
                Paragraph("PAYMENT STATUS", label_style),
                Paragraph("TICKET STATUS", label_style),
            ],
            [
                Paragraph(f"{event_setting.event_date}<br/>06:30 PM - 10:00 PM", sub_val_style),
                Paragraph(f"<b>{event_setting.venue_name}</b><br/>{event_setting.venue_address}, {event_setting.venue_city}", sub_val_style),
                Paragraph(f"✓ PAID (Rs. {int(getattr(ticket, 'ticket_price', None) or (booking.amount / max(1, booking.ticket_count)) if booking.amount else 599)})", val_style),
                Paragraph(f"● {ticket.ticket_status}", val_style),
            ],
        ]

        main_table = Table(details_data, colWidths=[135, 135, 135, 135])
        main_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFFFFF")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#E2E8F0")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ]))
        story.append(main_table)
        story.append(Spacer(1, 10))

        # 3. High-Contrast Centered Scannable QR Code
        qr_img_bytes = qr_service.generate_qr_bytes(ticket.qr_token_raw)
        qr_stream = io.BytesIO(qr_img_bytes)
        qr_image = Image(qr_stream, width=1.85 * inch, height=1.85 * inch)
        qr_notice = Paragraph("Scan this barcode at security turnstiles for gate admission", ParagraphStyle("QRN", fontName="Helvetica", fontSize=8, textColor=colors.HexColor("#64748B"), alignment=1))
        qr_table = Table([[qr_image], [qr_notice]], colWidths=[540])
        qr_table.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
        ]))
        story.append(qr_table)
        story.append(Spacer(1, 10))

        # 4. Important Venue Instructions Box
        guidelines_header = Paragraph("<b>IMPORTANT VENUE INSTRUCTIONS</b>", ParagraphStyle("GH", fontName="Helvetica-Bold", fontSize=9, textColor=colors.HexColor("#B45309")))
        guidelines_text = Paragraph(
            "• Gates open promptly at 06:30 PM. Show this barcode or digital pass at turnstiles.<br/>"
            "• Event Timings: 06:30 PM onwards till 10:00 PM. Gates close at 10:00 PM.<br/>"
            "• Entry will be granted only after successful QR scanning at security.<br/>"
            "• Each QR code is uniquely encrypted and admits exactly one person once.<br/>"
            "• Traditional festive attire is celebrated and recommended.<br/>"
            "• Carry valid Government photo ID matching the attendee name.",
            sub_val_style
        )
        rules_table = Table([[guidelines_header], [guidelines_text]], colWidths=[540])
        rules_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFFDF5")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#FDE68A")),
            ("PADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(rules_table)
        story.append(Spacer(1, 10))

        # 5. Footer Line
        story.append(Paragraph(
            f"Pass 1 of 1 • Booking #{booking.booking_id} • {event_setting.event_name} × THE HAPPY CIRCLE Official E-Ticket",
            footer_style
        ))

        doc.build(story)
        return buffer.getvalue()

    @classmethod
    def generate_booking_bundle_pdf(cls, booking: Booking, event_setting: EventSetting) -> bytes:
        """Generates a bundled multi-page PDF containing all tickets for a booking."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=32,
            bottomMargin=32
        )
        story = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "EventTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=24,
            textColor=colors.HexColor("#EA580C"), # Vibrant Orange
            alignment=1,
            spaceAfter=4
        )
        collab_style = ParagraphStyle(
            "EventCollabBundle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=colors.HexColor("#FBBF24"), # Radiant Gold
            alignment=1,
            spaceAfter=4
        )
        tagline_style = ParagraphStyle(
            "EventTagline",
            parent=styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=11,
            textColor=colors.HexColor("#FCD34D"), # Warm Gold Italic
            alignment=1,
            spaceAfter=10
        )
        badge_style = ParagraphStyle(
            "BadgeStyle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=13,
            textColor=colors.white,
            alignment=1
        )
        label_style = ParagraphStyle(
            "LabelStyle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            textColor=colors.HexColor("#64748B") # Slate Gray
        )
        val_style = ParagraphStyle(
            "ValStyle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=colors.HexColor("#0F172A")
        )
        sub_val_style = ParagraphStyle(
            "SubValStyle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            textColor=colors.HexColor("#334155")
        )
        footer_style = ParagraphStyle(
            "FooterStyle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            textColor=colors.HexColor("#64748B"),
            alignment=1
        )

        total_tickets = len(booking.tickets)
        for index, ticket in enumerate(booking.tickets):
            if index > 0:
                story.append(PageBreak())

            # 1. Official Deep Navy / Indigo Header Banner
            header_data = [
                [Paragraph(f"&#10070; {event_setting.event_name.upper()} &#10070;", title_style)],
                [Paragraph("IN COLLABORATION WITH THE HAPPY CIRCLE", collab_style)],
                [Paragraph("Celebrate. Dance. Connect.", tagline_style)],
                [Paragraph(f"OFFICIAL ENTRY PASS — PASS {index + 1} OF {total_tickets}", badge_style)]
            ]
            header_table = Table(header_data, colWidths=[540])
            header_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#1C1949")),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]))
            story.append(header_table)
            story.append(Spacer(1, 10))

            # 2. 4-Column Ticket Metadata Grid
            details_data = [
                [
                    Paragraph("ATTENDEE NAME", label_style),
                    Paragraph("BOOKING ID", label_style),
                    Paragraph("TICKET NUMBER", label_style),
                    Paragraph("PASS ORDER", label_style),
                ],
                [
                    Paragraph(f"{ticket.customer_name}", val_style),
                    Paragraph(f"{booking.booking_id}", val_style),
                    Paragraph(f"{ticket.ticket_id}", val_style),
                    Paragraph(f"Pass {index + 1} of {total_tickets}", val_style),
                ],
                [
                    Paragraph("EVENT DATE & TIME", label_style),
                    Paragraph("VENUE LOCATION", label_style),
                    Paragraph("PAYMENT STATUS", label_style),
                    Paragraph("TICKET STATUS", label_style),
                ],
                [
                    Paragraph(f"{event_setting.event_date}<br/>06:30 PM - 10:00 PM", sub_val_style),
                    Paragraph(f"<b>{event_setting.venue_name}</b><br/>{event_setting.venue_address}, {event_setting.venue_city}", sub_val_style),
                    Paragraph(f"✓ PAID (Rs. {int(getattr(ticket, 'ticket_price', None) or (booking.amount / max(1, booking.ticket_count)) if booking.amount else 599)})", val_style),
                    Paragraph(f"● {ticket.ticket_status}", val_style),
                ],
            ]

            main_table = Table(details_data, colWidths=[135, 135, 135, 135])
            main_table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFFFFF")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#E2E8F0")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ]))
            story.append(main_table)
            story.append(Spacer(1, 10))

            # 3. High-Contrast Centered Scannable QR Code
            qr_img_bytes = qr_service.generate_qr_bytes(ticket.qr_token_raw)
            qr_stream = io.BytesIO(qr_img_bytes)
            qr_image = Image(qr_stream, width=1.85 * inch, height=1.85 * inch)
            qr_notice = Paragraph("Scan this barcode at security turnstiles for gate admission", ParagraphStyle("QRN2", fontName="Helvetica", fontSize=8, textColor=colors.HexColor("#64748B"), alignment=1))
            qr_table = Table([[qr_image], [qr_notice]], colWidths=[540])
            qr_table.setStyle(TableStyle([
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
            ]))
            story.append(qr_table)
            story.append(Spacer(1, 10))

            # 4. Important Venue Instructions Box
            guidelines_header = Paragraph("<b>IMPORTANT VENUE INSTRUCTIONS</b>", ParagraphStyle("GH", fontName="Helvetica-Bold", fontSize=9, textColor=colors.HexColor("#B45309")))
            guidelines_text = Paragraph(
                "• Gates open promptly at 06:30 PM. Show this barcode or digital pass at turnstiles.<br/>"
                "• Event Timings: 06:30 PM onwards till 10:00 PM. Gates close at 10:00 PM.<br/>"
                "• Entry will be granted only after successful QR scanning at security.<br/>"
                "• Each QR code is uniquely encrypted and admits exactly one person once.<br/>"
                "• Traditional festive attire is celebrated and recommended.<br/>"
                "• Carry valid Government photo ID matching the attendee name.",
                sub_val_style
            )
            rules_table = Table([[guidelines_header], [guidelines_text]], colWidths=[540])
            rules_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFFDF5")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#FDE68A")),
                ("PADDING", (0, 0), (-1, -1), 8),
            ]))
            story.append(rules_table)
            story.append(Spacer(1, 10))

            # 5. Footer Line
            story.append(Paragraph(
                f"Pass {index + 1} of {total_tickets} • Booking #{booking.booking_id} • {event_setting.event_name} × THE HAPPY CIRCLE Official E-Ticket",
                footer_style
            ))

        doc.build(story)
        return buffer.getvalue()

ticket_service = TicketService()
