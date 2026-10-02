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
        - Vertical perforated tear-off stub with dynamic ticket number, pure white QR card, and event admission details
        - Single unified footer statement ("An event by Heritage Production, curated by The Happy Circle in association with Wedeos Entertainment")
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
            img = PILImage.new("RGB", (1024, 506), "#4A0E17")

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
        font_georgia_12 = cls._get_font("georgia.ttf", 12)
        font_georgiab_15 = cls._get_font("georgiab.ttf", 15)
        font_arial_10 = cls._get_font("arial.ttf", 10)
        font_arialbd_9 = cls._get_font("arialbd.ttf", 9)
        font_arialbd_10 = cls._get_font("arialbd.ttf", 10)
        font_arialbd_11 = cls._get_font("arialbd.ttf", 11)
        font_arialbd_12 = cls._get_font("arialbd.ttf", 12)
        font_footer = cls._get_font("georgiab.ttf", 13)
        font_footer_sub = cls._get_font("georgiab.ttf", 11)

        # 1. Clean and draw Middle Decorative Card (Attendee & Inclusions - zero duplication)
        draw.rectangle([545, 90, 825, 400], fill=(68, 14, 22))
        draw.rounded_rectangle([565, 125, 805, 365], radius=14, fill=(58, 12, 20), outline=(212, 175, 55, 140), width=1)

        mid_cx = 685
        draw.text((mid_cx - 55, 145), "❖ FESTIVAL PERKS ❖", fill=(251, 191, 36), font=font_arialbd_9)
        draw.text((mid_cx - 65, 170), "LIVE GUJARATI DHOL", fill=(255, 248, 232), font=font_georgiab_15)
        draw.text((mid_cx - 75, 195), "DJ Night • Dandiya Raas • 360° Booth", fill=(243, 228, 178), font=font_arial_10)
        draw.text((mid_cx - 85, 215), "Complimentary Food Voucher Included", fill=(251, 191, 36), font=font_arialbd_9)

        # Divider line inside badge
        draw.line([(585, 242), (785, 242)], fill=(212, 175, 55, 100), width=1)

        # Attendee info
        cust_name = getattr(ticket, "customer_name", None) or getattr(booking, "customer_name", "Valued Guest")
        draw.text((mid_cx - 45, 255), "PASS HOLDER", fill=(243, 228, 178), font=font_arialbd_9)
        draw.text((mid_cx - 40, 275), str(cust_name)[:20], fill=(255, 255, 255), font=font_arialbd_12)
        draw.text((mid_cx - 45, 305), "✓ ADMIT 1 PERSON", fill=(52, 211, 153), font=font_arialbd_10)
        draw.text((mid_cx - 40, 330), "NON-TRANSFERABLE", fill=(243, 228, 178), font=font_arial_10)

        # Perforation seam line at x=825
        for y_dash in range(28, 400, 10):
            draw.line([(825, y_dash), (825, y_dash + 5)], fill=(212, 175, 55), width=2)
        draw.ellipse([818, 18, 832, 32], fill=(6, 7, 12))
        draw.ellipse([818, 396, 832, 410], fill=(6, 7, 12))

        # 2. Clean and draw Authoritative Right-Side Ticket Stub (Renders EXACTLY ONCE)
        draw.rectangle([826, 25, 1012, 400], fill=(53, 10, 17))
        stub_cx = 918
        y_cur = 28

        # A. ENTRY PASS
        bs1 = draw.textbbox((0, 0), "ENTRY PASS", font=font_georgia_12)
        draw.text((stub_cx - (bs1[2] - bs1[0]) // 2, y_cur), "ENTRY PASS", fill=(255, 245, 230), font=font_georgia_12)
        y_cur += 16

        # B. Phase Label (EARLY BIRD / PHASE 1)
        bs2 = draw.textbbox((0, 0), phase_label, font=font_georgiab_15)
        draw.text((stub_cx - (bs2[2] - bs2[0]) // 2, y_cur), phase_label, fill=(251, 191, 36), font=font_georgiab_15)
        y_cur += 18

        # C. Offer Label (STAG ENTRY, COUPLE, GROUP OF 10)
        bs2b = draw.textbbox((0, 0), offer_label, font=font_arialbd_10)
        draw.text((stub_cx - (bs2b[2] - bs2b[0]) // 2, y_cur), offer_label, fill=(255, 245, 230), font=font_arialbd_10)
        y_cur += 15

        # D. TICKET NO.
        bs4 = draw.textbbox((0, 0), "TICKET NO.", font=font_arialbd_9)
        draw.text((stub_cx - (bs4[2] - bs4[0]) // 2, y_cur), "TICKET NO.", fill=(243, 228, 178), font=font_arialbd_9)
        y_cur += 12

        # E. Unique Ticket ID
        tkt_no_str = getattr(ticket, "ticket_id", None) or f"{booking.booking_id}-01"
        bs5 = draw.textbbox((0, 0), tkt_no_str, font=font_arialbd_10)
        draw.text((stub_cx - (bs5[2] - bs5[0]) // 2, y_cur), tkt_no_str, fill=(255, 255, 255), font=font_arialbd_10)
        y_cur += 16

        # F. Scannable Pure White QR Code Card (High-Contrast, Pure White Quiet Zone)
        qr_token = getattr(ticket, "qr_token_raw", None) or getattr(ticket, "ticket_id", None) or getattr(booking, "booking_id", "NAV2026")
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=3, border=1)
        qr.add_data(qr_token)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="#000000", back_color="#FFFFFF").convert("RGB")
        qr_img = qr_img.resize((102, 102), PILImage.Resampling.LANCZOS)

        draw.rounded_rectangle([stub_cx - 55, y_cur, stub_cx + 55, y_cur + 110], radius=6, fill=(255, 255, 255))
        img.paste(qr_img, (stub_cx - 51, y_cur + 4))
        y_cur += 114

        # G. SCAN TO VERIFY
        bs6 = draw.textbbox((0, 0), "SCAN TO VERIFY", font=font_arialbd_9)
        draw.text((stub_cx - (bs6[2] - bs6[0]) // 2, y_cur), "SCAN TO VERIFY", fill=(255, 245, 230), font=font_arialbd_9)
        y_cur += 16

        # H. Dynamic Event Date
        event_date_str = str(event_setting.event_date or "17 OCT 2026").upper()
        if "OCTOBER" in event_date_str:
            event_date_str = event_date_str.replace("OCTOBER", "OCT")
        b_dt = draw.textbbox((0, 0), event_date_str, font=font_arialbd_11)
        draw.text((stub_cx - (b_dt[2] - b_dt[0]) // 2, y_cur), event_date_str, fill=(255, 248, 232), font=font_arialbd_11)
        y_cur += 15

        # I. Event Timings (06:30 PM - 10:00 PM)
        b_tm = draw.textbbox((0, 0), "06:30 PM - 10:00 PM", font=font_arial_10)
        draw.text((stub_cx - (b_tm[2] - b_tm[0]) // 2, y_cur), "06:30 PM - 10:00 PM", fill=(255, 248, 232), font=font_arial_10)
        y_cur += 13

        # J. Gate Opening Time (05:30 PM)
        b_gate = draw.textbbox((0, 0), "Gate Opening: 05:30 PM", font=font_arialbd_9)
        draw.text((stub_cx - (b_gate[2] - b_gate[0]) // 2, y_cur), "Gate Opening: 05:30 PM", fill=(251, 191, 36), font=font_arialbd_9)
        y_cur += 15

        # K. Authoritative Venue: THE GREEN ACRES, Mysuru
        venue_name_str = (event_setting.venue_name or "The Green Acres").upper()
        b_vn = draw.textbbox((0, 0), venue_name_str, font=font_arialbd_11)
        draw.text((stub_cx - (b_vn[2] - b_vn[0]) // 2, y_cur), venue_name_str, fill=(255, 248, 232), font=font_arialbd_11)
        y_cur += 13

        b_cty = draw.textbbox((0, 0), "Mysuru", font=font_arial_10)
        draw.text((stub_cx - (b_cty[2] - b_cty[0]) // 2, y_cur), "Mysuru", fill=(243, 228, 178), font=font_arial_10)

        # L. Multi-pass Counter (if applicable)
        if total_passes > 1:
            pass_order_str = f"PASS {pass_idx} OF {total_passes}"
            b_cnt = draw.textbbox((0, 0), pass_order_str, font=font_arialbd_9)
            draw.text((stub_cx - (b_cnt[2] - b_cnt[0]) // 2, y_cur + 13), pass_order_str, fill=(251, 191, 36), font=font_arialbd_9)

        # 3. Clean Single Unified Footer Banner (Zero sponsor boxes/circles/labels)
        draw.rounded_rectangle([18, 400, 1006, 488], radius=10, fill=(250, 243, 224), outline=(212, 175, 55), width=2)

        footer_l1 = "An event by Heritage Production,"
        footer_l2 = "curated by The Happy Circle in association with Wedeos Entertainment"

        b_f1 = draw.textbbox((0, 0), footer_l1, font=font_footer)
        draw.text((512 - (b_f1[2] - b_f1[0]) // 2, 420), footer_l1, fill=(70, 15, 25), font=font_footer)

        b_f2 = draw.textbbox((0, 0), footer_l2, font=font_footer_sub)
        draw.text((512 - (b_f2[2] - b_f2[0]) // 2, 444), footer_l2, fill=(120, 53, 15), font=font_footer_sub)

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
