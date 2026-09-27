import io
from datetime import timedelta
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

class TicketService:
    @staticmethod
    def generate_single_ticket_pdf(booking: Booking, ticket: Ticket, event_setting: EventSetting) -> bytes:
        """Generates a professional, print-ready PDF for a single ticket."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        story = []
        styles = getSampleStyleSheet()

        # Custom Styles
        title_style = ParagraphStyle(
            "EventTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=24,
            textColor=colors.HexColor("#D97706"), # Festive Gold
            alignment=1, # Center
            spaceAfter=4
        )
        tagline_style = ParagraphStyle(
            "EventTagline",
            parent=styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=11,
            textColor=colors.HexColor("#FCD34D"),
            alignment=1,
            spaceAfter=14
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
            fontSize=9,
            textColor=colors.HexColor("#9CA3AF")
        )
        val_style = ParagraphStyle(
            "ValStyle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=12,
            textColor=colors.HexColor("#111827")
        )
        sub_val_style = ParagraphStyle(
            "SubValStyle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            textColor=colors.HexColor("#374151")
        )
        footer_style = ParagraphStyle(
            "FooterStyle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            textColor=colors.HexColor("#6B7280"),
            alignment=1
        )

        # Header Box Table
        header_data = [
            [Paragraph(f"✦ {event_setting.event_name.upper()} ✦", title_style)],
            [Paragraph(f"{event_setting.event_tagline}", tagline_style)],
            [Paragraph("OFFICIAL ENTRY PASS — ADMIT ONE", badge_style)]
        ]
        header_table = Table(header_data, colWidths=[540])
        header_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#1E1B4B")), # Royal Midnight Indigo
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 14))

        # QR Code Generation (Contains verification token URL)
        qr_img_bytes = qr_service.generate_qr_bytes(ticket.qr_token_raw)
        qr_stream = io.BytesIO(qr_img_bytes)
        qr_image = Image(qr_stream, width=2.1*inch, height=2.1*inch)

        # Ticket Meta Left & QR Right
        details_data = [
            [
                Paragraph("ATTENDEE NAME", label_style),
                Paragraph("BOOKING ID", label_style),
                ""
            ],
            [
                Paragraph(f"{ticket.customer_name}", val_style),
                Paragraph(f"{booking.booking_id}", val_style),
                qr_image
            ],
            [
                Paragraph("TICKET NUMBER", label_style),
                Paragraph("PAYMENT STATUS", label_style),
                ""
            ],
            [
                Paragraph(f"{ticket.ticket_id}", val_style),
                Paragraph(f"✓ {booking.payment_status} (₹{int(booking.ticket_price)})", val_style),
                ""
            ],
            [
                Paragraph("EVENT DATE & TIME", label_style),
                Paragraph("TICKET STATUS", label_style),
                ""
            ],
            [
                Paragraph(f"{event_setting.event_date}<br/>{event_setting.event_time}", sub_val_style),
                Paragraph(f"● {ticket.ticket_status}", val_style),
                ""
            ],
            [
                Paragraph("VENUE LOCATION", label_style),
                Paragraph("SECURITY NOTICE", label_style),
                ""
            ],
            [
                Paragraph(f"<b>{event_setting.venue_name}</b><br/>{event_setting.venue_address}, {event_setting.venue_city}", sub_val_style),
                Paragraph("Scan this QR at the venue gate for swift check-in. Single-entry strictly enforced.", sub_val_style),
                ""
            ],
        ]

        main_table = Table(details_data, colWidths=[200, 180, 160])
        main_table.setStyle(TableStyle([
            ("SPAN", (2, 1), (2, 7)), # Span QR across details
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("ALIGN", (2, 1), (2, 7), "CENTER"),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F9FAFB")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#E5E7EB")),
            ("INNERGRID", (0, 0), (1, -1), 0.5, colors.HexColor("#F3F4F6")),
        ]))
        story.append(main_table)
        story.append(Spacer(1, 14))

        # Important Guidelines Box
        guidelines_header = Paragraph("<b>IMPORTANT VENUE INSTRUCTIONS</b>", ParagraphStyle("GH", fontName="Helvetica-Bold", fontSize=9, textColor=colors.HexColor("#B45309")))
        guidelines_text = Paragraph(
            "• Entry begins promptly at 05:30 PM (Turnstiles open 05:30 PM).<br/>"
            "• Event Timings: 06:00 PM onwards till 10:00 PM. Gates close at 10:00 PM.<br/>"
            "• Entry will be granted only after successful QR scanning at security.<br/>"
            "• Each QR code is uniquely encrypted and admits exactly one person once.<br/>"
            "• Traditional festive attire is celebrated and recommended.<br/>"
            "• Carry valid Government photo ID matching the attendee name.",
            sub_val_style
        )
        rules_table = Table([[guidelines_header], [guidelines_text]], colWidths=[540])
        rules_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFFBEB")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#FDE68A")),
            ("PADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(rules_table)
        story.append(Spacer(1, 14))

        # Footer with IST timestamp
        ist_created = (ticket.created_at + timedelta(hours=5, minutes=30)).strftime('%d-%b-%Y %I:%M:%S %p IST')
        story.append(Paragraph(
            f"Generated on {ist_created} • Garba Night 2026 Official E-Ticket System • Contact: {event_setting.contact_email}",
            footer_style
        ))

        doc.build(story)
        return buffer.getvalue()

    @staticmethod
    def generate_booking_bundle_pdf(booking: Booking, event_setting: EventSetting) -> bytes:
        """Generates a bundled multi-page PDF containing all tickets for a booking."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )
        story = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "EventTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=22,
            textColor=colors.HexColor("#D97706"),
            alignment=1,
            spaceAfter=4
        )
        tagline_style = ParagraphStyle(
            "EventTagline",
            parent=styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=10,
            textColor=colors.HexColor("#FCD34D"),
            alignment=1,
            spaceAfter=10
        )
        badge_style = ParagraphStyle(
            "BadgeStyle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=12,
            textColor=colors.white,
            alignment=1
        )
        label_style = ParagraphStyle(
            "LabelStyle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            textColor=colors.HexColor("#9CA3AF")
        )
        val_style = ParagraphStyle(
            "ValStyle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            textColor=colors.HexColor("#111827")
        )
        sub_val_style = ParagraphStyle(
            "SubValStyle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            textColor=colors.HexColor("#374151")
        )
        footer_style = ParagraphStyle(
            "FooterStyle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            textColor=colors.HexColor("#6B7280"),
            alignment=1
        )

        for index, ticket in enumerate(booking.tickets):
            if index > 0:
                story.append(PageBreak())

            header_data = [
                [Paragraph(f"✦ {event_setting.event_name.upper()} ✦", title_style)],
                [Paragraph(f"{event_setting.event_tagline}", tagline_style)],
                [Paragraph(f"OFFICIAL ENTRY PASS — PASS {index + 1} OF {len(booking.tickets)}", badge_style)]
            ]
            header_table = Table(header_data, colWidths=[540])
            header_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#1E1B4B")),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]))
            story.append(header_table)
            story.append(Spacer(1, 12))

            qr_img_bytes = qr_service.generate_qr_bytes(ticket.qr_token_raw)
            qr_stream = io.BytesIO(qr_img_bytes)
            qr_image = Image(qr_stream, width=2.1*inch, height=2.1*inch)

            details_data = [
                [Paragraph("PRIMARY BOOKER", label_style), Paragraph("BOOKING ID", label_style), ""],
                [Paragraph(f"{ticket.customer_name}", val_style), Paragraph(f"{booking.booking_id}", val_style), qr_image],
                [Paragraph("TICKET NUMBER", label_style), Paragraph("PAYMENT STATUS", label_style), ""],
                [Paragraph(f"{ticket.ticket_id}", val_style), Paragraph(f"✓ {booking.payment_status} (₹{int(booking.ticket_price)})", val_style), ""],
                [Paragraph("EVENT DATE & TIME", label_style), Paragraph("TICKET STATUS", label_style), ""],
                [Paragraph(f"{event_setting.event_date}<br/>{event_setting.event_time}", sub_val_style), Paragraph(f"● {ticket.ticket_status}", val_style), ""],
                [Paragraph("VENUE LOCATION", label_style), Paragraph("SECURITY INSTRUCTION", label_style), ""],
                [Paragraph(f"<b>{event_setting.venue_name}</b><br/>{event_setting.venue_address}, {event_setting.venue_city}", sub_val_style), Paragraph("Single-scan entry pass. Keep ready on your phone or printed.", sub_val_style), ""],
            ]

            main_table = Table(details_data, colWidths=[200, 180, 160])
            main_table.setStyle(TableStyle([
                ("SPAN", (2, 1), (2, 7)),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("ALIGN", (2, 1), (2, 7), "CENTER"),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F9FAFB")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#E5E7EB")),
            ]))
            story.append(main_table)
            story.append(Spacer(1, 12))

            rules_table = Table([[
                Paragraph("<b>EVENT NOTICE:</b> Entry starts at 05:30 PM • Event: 06:00 PM - 10:00 PM. Duplicate entries or re-scans are automatically rejected. Traditional dress code mandatory.", sub_val_style)
            ]], colWidths=[540])
            rules_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFFBEB")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#FDE68A")),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(rules_table)
            story.append(Spacer(1, 10))

            story.append(Paragraph(
                f"Pass {index + 1} of {len(booking.tickets)} • Booking #{booking.booking_id} • {event_setting.event_name} Official E-Ticket",
                footer_style
            ))

        doc.build(story)
        return buffer.getvalue()

ticket_service = TicketService()
