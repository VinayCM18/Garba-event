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
        Renders the official NAVRANG 2026 Dandiya festive ticket pass with dynamic data:
        - Real cryptographically signed QR code inlaid on the stub
        - Dynamic ticket ID / booking ID
        - Dynamic Offer/Phase name (EARLY BIRD, PHASE 1, GROUP OF 10, COUPLE ENTRY, KIDS PASS)
        - Dynamic attendee name
        - Event logistics
        Returns JPEG bytes (1024x506).
        """
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        template_path = os.path.join(base_dir, "static", "navrang_ticket_template.jpg")

        if not os.path.exists(template_path):
            template_path = os.path.abspath(os.path.join("app", "static", "navrang_ticket_template.jpg"))

        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Navrang ticket template not found at {template_path}")

        img = PILImage.open(template_path).convert("RGB")
        draw = ImageDraw.Draw(img)

        # 1. Dynamic QR Code
        qr_payload = getattr(ticket, "qr_token_raw", None) or getattr(booking, "booking_id", "NAV2026")
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=4,
            border=1,
        )
        qr.add_data(qr_payload)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="#150406", back_color="#ffffff").convert("RGB")
        qr_img = qr_img.resize((112, 114), PILImage.Resampling.LANCZOS)
        img.paste(qr_img, (868, 218))

        # Color palette matching official template
        stub_bg = (79, 22, 29)          # Deep Royal Crimson
        plaque_bg = (240, 232, 212)     # Parchment Ivory
        maroon_text = (74, 14, 23)      # Regal Maroon
        gold_text = (243, 228, 178)     # Festive Warm Gold
        gold_accent = (212, 175, 55)    # Bright Gold
        white_text = (255, 255, 255)

        # Resolve Phase and Offer Labels
        offer_id = getattr(booking, "offer_id", None) or ""
        offer_title = getattr(booking, "offer_title", None) or ""
        if not offer_title and offer_id:
            off_def = get_offer_by_id(offer_id)
            if off_def:
                offer_title = off_def.get("title", "")

        off_lower = f"{offer_id} {offer_title}".lower()
        if "group" in off_lower:
            plaque_label = "GROUP OF 10"
            stub_label = "GROUP OF 10"
        elif "couple" in off_lower:
            plaque_label = "COUPLE ENTRY"
            stub_label = "COUPLE PASS"
        elif "kid" in off_lower:
            plaque_label = "KIDS (5-12)"
            stub_label = "KIDS PASS"
        elif "phase 1" in off_lower or "phase_1" in off_lower:
            plaque_label = "PHASE 1"
            stub_label = "PHASE 1"
        else:
            plaque_label = "EARLY BIRD"
            stub_label = "EARLY BIRD"

        # Fonts
        plaque_f_size = 22 if len(plaque_label) <= 10 else 18
        font_plaque = cls._get_font("georgiab.ttf", plaque_f_size)
        stub_f_size = 14 if len(stub_label) <= 10 else 12
        font_stub_phase = cls._get_font("georgiab.ttf", stub_f_size)
        font_attendee = cls._get_font("arialbd.ttf", 10)
        font_tkt_id = cls._get_font("arialbd.ttf", 11)

        # 2. Stub Phase Label
        draw.rectangle([(845, 105), (985, 127)], fill=stub_bg)
        bbox = draw.textbbox((0, 0), stub_label, font=font_stub_phase)
        tw = bbox[2] - bbox[0]
        draw.text((915 - tw // 2, 108), stub_label, fill=gold_text, font=font_stub_phase)

        # 3. Stub Attendee Name
        cust_name = getattr(ticket, "customer_name", None) or getattr(booking, "customer_name", "ATTENDEE")
        cust_name_clean = cust_name.upper().strip()
        if len(cust_name_clean) > 17:
            cust_name_clean = cust_name_clean[:15] + ".."
        draw.rectangle([(845, 134), (985, 156)], fill=stub_bg)
        bbox = draw.textbbox((0, 0), cust_name_clean, font=font_attendee)
        tw = bbox[2] - bbox[0]
        draw.text((915 - tw // 2, 138), cust_name_clean, fill=gold_accent, font=font_attendee)

        # 4. Stub Ticket No.
        tkt_no = getattr(ticket, "ticket_id", None) or getattr(booking, "booking_id", "NAV2026-0001")
        clean_tkt = tkt_no.strip()
        if len(clean_tkt) > 16:
            clean_tkt = clean_tkt[:16]
        draw.rectangle([(845, 182), (985, 206)], fill=stub_bg)
        bbox = draw.textbbox((0, 0), clean_tkt, font=font_tkt_id)
        tw = bbox[2] - bbox[0]
        draw.text((915 - tw // 2, 186), clean_tkt, fill=white_text, font=font_tkt_id)

        # 5. Plaque Offer / Phase Label
        draw.rectangle([(605, 168), (765, 206)], fill=plaque_bg)
        bbox = draw.textbbox((0, 0), plaque_label, font=font_plaque)
        tw = bbox[2] - bbox[0]
        draw.text((686 - tw // 2, 172), plaque_label, fill=maroon_text, font=font_plaque)

        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=95)
        return buffer.getvalue()

    @classmethod
    def generate_single_ticket_pdf(cls, booking: Booking, ticket: Ticket, event_setting: EventSetting) -> bytes:
        """Generates a professional, print-ready PDF for a single ticket with official festive ticket pass."""
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
            textColor=colors.HexColor("#FCD34D"),
            alignment=1,
            spaceAfter=12
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
            textColor=colors.HexColor("#6B7280")
        )
        val_style = ParagraphStyle(
            "ValStyle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
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

        # Header Box Table (Fallback)
        header_data = [
            [Paragraph(f"✦ {event_setting.event_name.upper()} ✦", title_style)],
            [Paragraph("IN COLLABORATION WITH THE HAPPY CIRCLE", collab_style)],
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

        # Try rendering official festive ticket pass image at the top of the PDF
        try:
            tkt_img_bytes = cls.generate_ticket_image_bytes(booking, ticket, event_setting)
            img_w = 7.5 * inch
            img_h = img_w * (506.0 / 1024.0)
            story.append(Image(io.BytesIO(tkt_img_bytes), width=img_w, height=img_h))
            story.append(Spacer(1, 14))
        except Exception:
            story.append(header_table)
            story.append(Spacer(1, 14))

        # Ticket Metadata Grid
        details_data = [
            [
                Paragraph("ATTENDEE NAME", label_style),
                Paragraph("BOOKING ID", label_style),
                Paragraph("TICKET NUMBER", label_style),
                Paragraph("PAYMENT STATUS", label_style),
            ],
            [
                Paragraph(f"{ticket.customer_name}", val_style),
                Paragraph(f"{booking.booking_id}", val_style),
                Paragraph(f"{ticket.ticket_id}", val_style),
                Paragraph(f"✓ {booking.payment_status} (₹{int(booking.ticket_price)})", val_style),
            ],
            [
                Paragraph("EVENT DATE & TIME", label_style),
                Paragraph("VENUE LOCATION", label_style),
                Paragraph("TICKET STATUS", label_style),
                Paragraph("SECURITY NOTICE", label_style),
            ],
            [
                Paragraph(f"{event_setting.event_date}<br/>{event_setting.event_time}", sub_val_style),
                Paragraph(f"<b>{event_setting.venue_name}</b><br/>{event_setting.venue_address}, {event_setting.venue_city}", sub_val_style),
                Paragraph(f"● {ticket.ticket_status}", val_style),
                Paragraph("Turnstile barcode verified. Single-entry strictly enforced.", sub_val_style),
            ],
        ]

        main_table = Table(details_data, colWidths=[135, 135, 135, 135])
        main_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F9FAFB")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#E5E7EB")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#F3F4F6")),
        ]))
        story.append(main_table)
        story.append(Spacer(1, 12))

        # Important Guidelines Box
        guidelines_header = Paragraph("<b>IMPORTANT VENUE INSTRUCTIONS</b>", ParagraphStyle("GH", fontName="Helvetica-Bold", fontSize=9, textColor=colors.HexColor("#B45309")))
        guidelines_text = Paragraph(
            "• Gates open promptly at 06:30 PM. Show this barcode or printable pass at turnstiles.<br/>"
            "• Event Timings: 07:00 PM onwards till 10:00 PM. Gates close at 10:00 PM.<br/>"
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
            ("PADDING", (0, 0), (-1, -1), 7),
        ]))
        story.append(rules_table)
        story.append(Spacer(1, 12))

        # Footer with IST timestamp
        ist_created = (ticket.created_at + timedelta(hours=5, minutes=30)).strftime('%d-%b-%Y %I:%M:%S %p IST')
        story.append(Paragraph(
            f"Generated on {ist_created} • NAVRANG 2026 Official E-Ticket System • In collaboration with THE HAPPY CIRCLE • Contact: {event_setting.contact_email}",
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
            fontSize=8,
            textColor=colors.HexColor("#6B7280")
        )
        val_style = ParagraphStyle(
            "ValStyle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
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

            collab_style = ParagraphStyle(
                "EventCollabBundle",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=9,
                textColor=colors.HexColor("#FBBF24"), # Radiant Gold
                alignment=1,
                spaceAfter=3
            )
            header_data = [
                [Paragraph(f"✦ {event_setting.event_name.upper()} ✦", title_style)],
                [Paragraph("IN COLLABORATION WITH THE HAPPY CIRCLE", collab_style)],
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

            # Try rendering official festive ticket pass image at the top of the PDF page
            try:
                tkt_img_bytes = cls.generate_ticket_image_bytes(booking, ticket, event_setting)
                img_w = 7.5 * inch
                img_h = img_w * (506.0 / 1024.0)
                story.append(Image(io.BytesIO(tkt_img_bytes), width=img_w, height=img_h))
                story.append(Spacer(1, 14))
            except Exception:
                story.append(header_table)
                story.append(Spacer(1, 14))

            # Ticket Metadata Grid
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
                    Paragraph(f"Pass {index + 1} of {len(booking.tickets)}", val_style),
                ],
                [
                    Paragraph("EVENT DATE & TIME", label_style),
                    Paragraph("VENUE LOCATION", label_style),
                    Paragraph("PAYMENT STATUS", label_style),
                    Paragraph("TICKET STATUS", label_style),
                ],
                [
                    Paragraph(f"{event_setting.event_date}<br/>{event_setting.event_time}", sub_val_style),
                    Paragraph(f"<b>{event_setting.venue_name}</b><br/>{event_setting.venue_address}, {event_setting.venue_city}", sub_val_style),
                    Paragraph(f"✓ {booking.payment_status} (₹{int(booking.ticket_price)})", val_style),
                    Paragraph(f"● {ticket.ticket_status}", val_style),
                ],
            ]

            main_table = Table(details_data, colWidths=[135, 135, 135, 135])
            main_table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F9FAFB")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#E5E7EB")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#F3F4F6")),
            ]))
            story.append(main_table)
            story.append(Spacer(1, 12))

            # Important Guidelines Box
            guidelines_header = Paragraph("<b>IMPORTANT VENUE INSTRUCTIONS</b>", ParagraphStyle("GH", fontName="Helvetica-Bold", fontSize=9, textColor=colors.HexColor("#B45309")))
            guidelines_text = Paragraph(
                "• Gates open promptly at 06:30 PM. Show this barcode or digital pass at turnstiles.<br/>"
                "• Event Timings: 07:00 PM onwards till 10:00 PM. Gates close at 10:00 PM.<br/>"
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
                ("PADDING", (0, 0), (-1, -1), 7),
            ]))
            story.append(rules_table)
            story.append(Spacer(1, 10))

            story.append(Paragraph(
                f"Pass {index + 1} of {len(booking.tickets)} • Booking #{booking.booking_id} • {event_setting.event_name} × THE HAPPY CIRCLE Official E-Ticket",
                footer_style
            ))

        doc.build(story)
        return buffer.getvalue()

ticket_service = TicketService()
