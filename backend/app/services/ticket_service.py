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
        Renders the official NAVRANG 2026 admission pass image matching the reference design:
        - Deep maroon/burgundy background with ornate gold border and Indian festive motifs
        - Heritage Productions × The Happy Circle collaboration header
        - Ornate 3D gold embossed NAVRANG DANDIYA 2026 central branding with crossed dandiya sticks
        - Scalloped royal ivory arch cartouche with dynamic Phase Name & Offer Type
        - Event details with Date, 06:30 PM - 10:00 PM (Gate Opening: 5:30 PM), and The Green Acres venue
        - Vertical perforated tear-off stub with dynamic ticket number, pure white QR card, and SCAN TO VERIFY
        - Clean sponsor footer strip (Location Partner: The Green Acres) without gray placeholder circles
        Returns high-quality JPEG bytes.
        """
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        clean_tpl = os.path.join(base_dir, "static", "navrang_ticket_template_clean.jpg")
        fallback_tpl = os.path.join(base_dir, "static", "navrang_ticket_template.jpg")

        if os.path.exists(clean_tpl):
            img = PILImage.open(clean_tpl).convert("RGB")
        elif os.path.exists(fallback_tpl):
            img = PILImage.open(fallback_tpl).convert("RGB")
        else:
            img = PILImage.new("RGB", (1024, 494), "#4A0E17")

        draw = ImageDraw.Draw(img)
        w, h = img.size

        # Resolve Phase Label and Offer Type dynamically
        offer_title = getattr(booking, "offer_title", "") or ""
        ticket_offer = getattr(ticket, "offer_title", "") or ""
        combined_offer = (ticket_offer or offer_title).lower()

        total_passes = booking.ticket_count if (booking and booking.ticket_count) else 1
        pass_idx = 1
        if booking and booking.tickets:
            for idx, t in enumerate(booking.tickets):
                if t.ticket_id == ticket.ticket_id:
                    pass_idx = idx + 1
                    break

        is_early = "early" in combined_offer
        is_phase1 = "phase 1" in combined_offer or "phase_1" in combined_offer

        if is_early:
            phase_label = "EARLY BIRD"
        elif is_phase1:
            phase_label = "PHASE 1"
        else:
            phase_label = "EARLY BIRD"

        if "group" in combined_offer or total_passes == 10:
            offer_label = "GROUP OF 10"
        elif "couple" in combined_offer or total_passes == 2:
            offer_label = "COUPLE ENTRY"
        elif "kid" in combined_offer or "child" in combined_offer:
            offer_label = "KIDS ENTRY"
        else:
            offer_label = "STAG ENTRY"

        # Fonts
        font_cart_sub = cls._get_font("georgia.ttf", 13)
        font_cart_phase = cls._get_font("georgiab.ttf", 20)
        font_cart_type = cls._get_font("arialbd.ttf", 10)

        font_dt_bold = cls._get_font("arialbd.ttf", 13)
        font_dt_sub = cls._get_font("arial.ttf", 11)
        font_dt_gate = cls._get_font("arialbd.ttf", 11)

        font_stub_sub = cls._get_font("georgia.ttf", 12)
        font_stub_phase = cls._get_font("georgiab.ttf", 15)
        font_stub_type = cls._get_font("arialbd.ttf", 9)
        font_stub_div = cls._get_font("georgia.ttf", 11)
        font_stub_lbl = cls._get_font("arialbd.ttf", 9)
        font_stub_id = cls._get_font("arialbd.ttf", 11)
        font_stub_scan = cls._get_font("arialbd.ttf", 9)
        font_sp_val = cls._get_font("arialbd.ttf", 10)

        # 1. Clean and draw Cartouche text (centered around x=675, y=166)
        cart_cx = 675
        draw.rounded_rectangle([605, 126, 745, 205], radius=8, fill=(255, 248, 232))

        b1 = draw.textbbox((0, 0), "ENTRY PASS", font=font_cart_sub)
        draw.text((cart_cx - (b1[2] - b1[0]) // 2, 134), "ENTRY PASS", fill=(70, 15, 25), font=font_cart_sub)

        b2 = draw.textbbox((0, 0), phase_label, font=font_cart_phase)
        draw.text((cart_cx - (b2[2] - b2[0]) // 2, 153), phase_label, fill=(70, 15, 25), font=font_cart_phase)

        b3 = draw.textbbox((0, 0), f"❖ {offer_label} ❖", font=font_cart_type)
        draw.text((cart_cx - (b3[2] - b3[0]) // 2, 182), f"❖ {offer_label} ❖", fill=(180, 83, 9), font=font_cart_type)

        # 2. Clean and draw Event Details text (preserving the 3 white icons at x=580..604)
        draw.rounded_rectangle([606, 236, 795, 355], radius=6, fill=(80, 19, 28))

        # Dynamic Event Date
        event_date_str = str(event_setting.event_date or "17 OCT 2026").upper()
        if "OCTOBER" in event_date_str:
            event_date_str = event_date_str.replace("OCTOBER", "OCT")
        draw.text((608, 242), event_date_str, fill=(255, 248, 232), font=font_dt_bold)

        # Synchronized Timings & Explicit Gate Opening 5:30 PM (as requested)
        draw.text((608, 268), "06:30 PM - 10:00 PM", fill=(255, 248, 232), font=font_dt_bold)
        draw.text((608, 286), "Gate Opening: 5:30 PM", fill=(251, 191, 36), font=font_dt_gate)

        # Configured Venue: The Green Acres, Mysuru (as requested)
        venue_name_str = (event_setting.venue_name or "The Green Acres").upper()
        venue_sub_str = f"{event_setting.venue_address or 'The Green Acres, Mysuru'}"
        draw.text((608, 310), venue_name_str, fill=(255, 248, 232), font=font_dt_bold)
        draw.text((608, 328), venue_sub_str[:32], fill=(243, 228, 178), font=font_dt_sub)

        # 3. Clean and draw Stub Area (x=848 to 1010)
        draw.rectangle([848, 28, 1010, 375], fill=(78, 20, 30))
        stub_cx = 928

        bs1 = draw.textbbox((0, 0), "ENTRY PASS", font=font_stub_sub)
        draw.text((stub_cx - (bs1[2] - bs1[0]) // 2, 34), "ENTRY PASS", fill=(255, 245, 230), font=font_stub_sub)

        bs2 = draw.textbbox((0, 0), phase_label, font=font_stub_phase)
        draw.text((stub_cx - (bs2[2] - bs2[0]) // 2, 50), phase_label, fill=(251, 191, 36), font=font_stub_phase)

        bs2b = draw.textbbox((0, 0), offer_label, font=font_stub_type)
        draw.text((stub_cx - (bs2b[2] - bs2b[0]) // 2, 69), offer_label, fill=(255, 245, 230), font=font_stub_type)

        bs3 = draw.textbbox((0, 0), "✦ ❖ ✦", font=font_stub_div)
        draw.text((stub_cx - (bs3[2] - bs3[0]) // 2, 83), "✦ ❖ ✦", fill=(212, 175, 55), font=font_stub_div)

        bs4 = draw.textbbox((0, 0), "TICKET NO.", font=font_stub_lbl)
        draw.text((stub_cx - (bs4[2] - bs4[0]) // 2, 100), "TICKET NO.", fill=(243, 228, 178), font=font_stub_lbl)

        tkt_no_str = getattr(ticket, "ticket_id", None) or f"{booking.booking_id}-01"
        bs5 = draw.textbbox((0, 0), tkt_no_str, font=font_stub_id)
        draw.text((stub_cx - (bs5[2] - bs5[0]) // 2, 114), tkt_no_str, fill=(255, 255, 255), font=font_stub_id)

        # Scannable White QR Code Card (High-Contrast, Pure White Quiet Zone)
        qr_token = getattr(ticket, "qr_token_raw", None) or getattr(ticket, "ticket_id", None) or getattr(booking, "booking_id", "NAV2026")
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=3, border=1)
        qr.add_data(qr_token)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="#000000", back_color="#FFFFFF").convert("RGB")
        qr_img = qr_img.resize((124, 124), PILImage.Resampling.LANCZOS)

        draw.rounded_rectangle([860, 136, 996, 272], radius=6, fill=(255, 255, 255))
        img.paste(qr_img, (866, 142))

        bs6 = draw.textbbox((0, 0), "SCAN TO VERIFY", font=font_stub_scan)
        draw.text((stub_cx - (bs6[2] - bs6[0]) // 2, 280), "SCAN TO VERIFY", fill=(255, 245, 230), font=font_stub_scan)

        if total_passes > 1:
            pass_order_str = f"PASS {pass_idx} OF {total_passes}"
            bs7 = draw.textbbox((0, 0), pass_order_str, font=font_stub_lbl)
            draw.text((stub_cx - (bs7[2] - bs7[0]) // 2, 296), pass_order_str, fill=(251, 191, 36), font=font_stub_lbl)

        # 4. Clean Sponsor Footer Strip (zero gray placeholder circles)
        draw.rectangle([35, 425, 975, 468], fill=(248, 241, 222))

        # Location Partner: The Green Acres
        b_loc = draw.textbbox((0, 0), "The Green Acres", font=font_sp_val)
        draw.text((150 - (b_loc[2] - b_loc[0]) // 2, 436), "The Green Acres", fill=(70, 15, 25), font=font_sp_val)

        # Main Sponsor: Heritage Productions
        b_main = draw.textbbox((0, 0), "HERITAGE PRODUCTIONS", font=font_sp_val)
        draw.text((370 - (b_main[2] - b_main[0]) // 2, 436), "HERITAGE PRODUCTIONS", fill=(70, 15, 25), font=font_sp_val)

        # Co-Sponsor: The Happy Circle
        b_co = draw.textbbox((0, 0), "THE HAPPY CIRCLE", font=font_sp_val)
        draw.text((580 - (b_co[2] - b_co[0]) // 2, 436), "THE HAPPY CIRCLE", fill=(70, 15, 25), font=font_sp_val)

        # Event Partners
        b_oth = draw.textbbox((0, 0), "OFFICIAL ADMISSION PASS • 2026", font=font_sp_val)
        draw.text((830 - (b_oth[2] - b_oth[0]) // 2, 436), "OFFICIAL ADMISSION PASS • 2026", fill=(70, 15, 25), font=font_sp_val)

        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=95)
        return buffer.getvalue()

    @classmethod
    def generate_single_ticket_pdf(cls, booking: Booking, ticket: Ticket, event_setting: EventSetting) -> bytes:
        """Generates a professional, print-ready PDF for a single ticket matching the official NAVRANG 2026 pass design."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=24,
            leftMargin=24,
            topMargin=24,
            bottomMargin=24
        )
        story = []

        # 1. Official NAVRANG 2026 Entry Pass Visual
        tkt_img_bytes = cls.generate_ticket_image_bytes(booking, ticket, event_setting)
        img_w = 7.8 * inch
        img_h = img_w * (494.0 / 1024.0)
        story.append(Image(io.BytesIO(tkt_img_bytes), width=img_w, height=img_h))
        story.append(Spacer(1, 14))

        # 2. Official Guidelines & Instructions Box
        styles = getSampleStyleSheet()
        inst_style = ParagraphStyle("IT", fontName="Helvetica", fontSize=8.5, leading=12.5, textColor=colors.HexColor("#334155"))

        notice_text = (
            "<b><font color='#78350F'>OFFICIAL ENTRY PASS GUIDELINES</font></b><br/>"
            "&bull; <b>Gate Opening:</b> Gates open promptly at <b>05:30 PM</b>. Please arrive early to avoid queue delays.<br/>"
            "&bull; <b>Event Timings:</b> 06:30 PM onwards till 10:00 PM. Turnstiles close at 10:00 PM.<br/>"
            "&bull; <b>Venue:</b> The Green Acres, Mysuru. Ample parking available on premise.<br/>"
            "&bull; <b>Entry Verification:</b> Present this physical or digital pass with the authentic QR code at security turnstiles.<br/>"
            "&bull; <b>One Pass per Attendee:</b> Each QR code is uniquely encrypted and allows exactly one entry.<br/>"
            "&bull; <b>Photo ID:</b> Please carry a government-issued photo ID matching the attendee name."
        )
        notice_p = Paragraph(notice_text, inst_style)

        notice_table = Table([[notice_p]], colWidths=[7.8 * inch])
        notice_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFFDF5")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#FDE68A")),
            ("PADDING", (0, 0), (-1, -1), 10),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(notice_table)
        story.append(Spacer(1, 10))

        footer_style = ParagraphStyle("FS", fontName="Helvetica", fontSize=7.5, textColor=colors.HexColor("#64748B"), alignment=1)
        story.append(Paragraph(
            f"Pass 1 of 1 &bull; Booking #{booking.booking_id} &bull; Ticket #{ticket.ticket_id} &bull; NAVRANG 2026 &times; THE HAPPY CIRCLE Official Pass",
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
            rightMargin=24,
            leftMargin=24,
            topMargin=24,
            bottomMargin=24
        )
        story = []
        styles = getSampleStyleSheet()
        inst_style = ParagraphStyle("IT_Bundle", fontName="Helvetica", fontSize=8.5, leading=12.5, textColor=colors.HexColor("#334155"))
        footer_style = ParagraphStyle("FS_Bundle", fontName="Helvetica", fontSize=7.5, textColor=colors.HexColor("#64748B"), alignment=1)

        notice_text = (
            "<b><font color='#78350F'>OFFICIAL ENTRY PASS GUIDELINES</font></b><br/>"
            "&bull; <b>Gate Opening:</b> Gates open promptly at <b>05:30 PM</b>. Please arrive early to avoid queue delays.<br/>"
            "&bull; <b>Event Timings:</b> 06:30 PM onwards till 10:00 PM. Turnstiles close at 10:00 PM.<br/>"
            "&bull; <b>Venue:</b> The Green Acres, Mysuru. Ample parking available on premise.<br/>"
            "&bull; <b>Entry Verification:</b> Present this physical or digital pass with the authentic QR code at security turnstiles.<br/>"
            "&bull; <b>One Pass per Attendee:</b> Each QR code is uniquely encrypted and allows exactly one entry.<br/>"
            "&bull; <b>Photo ID:</b> Please carry a government-issued photo ID matching the attendee name."
        )

        total_tickets = len(booking.tickets)
        for index, ticket in enumerate(booking.tickets):
            if index > 0:
                story.append(PageBreak())

            tkt_img_bytes = cls.generate_ticket_image_bytes(booking, ticket, event_setting)
            img_w = 7.8 * inch
            img_h = img_w * (494.0 / 1024.0)
            story.append(Image(io.BytesIO(tkt_img_bytes), width=img_w, height=img_h))
            story.append(Spacer(1, 14))

            notice_p = Paragraph(notice_text, inst_style)
            notice_table = Table([[notice_p]], colWidths=[7.8 * inch])
            notice_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFFDF5")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#FDE68A")),
                ("PADDING", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]))
            story.append(notice_table)
            story.append(Spacer(1, 10))

            story.append(Paragraph(
                f"Pass {index + 1} of {total_tickets} &bull; Booking #{booking.booking_id} &bull; Ticket #{ticket.ticket_id} &bull; NAVRANG 2026 &times; THE HAPPY CIRCLE Official Pass",
                footer_style
            ))

        doc.build(story)
        return buffer.getvalue()

ticket_service = TicketService()
