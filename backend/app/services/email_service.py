import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import urllib.request
import json
import re
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.config import settings
from app.models.booking import Booking
from app.models.event_setting import EventSetting
from app.services.qr_service import qr_service
from app.services.ticket_service import ticket_service
from app.utils.logger import app_logger

def format_ist_datetime(dt: Optional[datetime] = None) -> str:
    """Converts a UTC datetime to Indian Standard Time (IST, UTC+5:30) and formats it cleanly."""
    if not dt:
        dt = datetime.utcnow()
    ist_offset = timedelta(hours=5, minutes=30)
    ist_dt = dt + ist_offset
    return ist_dt.strftime("%d %b %Y, %I:%M:%S %p IST")

class EmailService:
    @staticmethod
    def get_smtp_config(db: Session) -> Dict[str, Any]:
        """Resolves SMTP and Owner notification settings from EventSetting in DB or .env fallback."""
        event_setting = db.query(EventSetting).first()
        if not event_setting:
            event_setting = EventSetting()

        # Database settings take precedence if configured, otherwise fallback to app settings (.env)
        smtp_username = (event_setting.smtp_username or "").strip() or settings.SMTP_USERNAME
        smtp_password = (event_setting.smtp_password or "").strip() or settings.SMTP_PASSWORD
        smtp_host = (event_setting.smtp_host or "").strip() or settings.SMTP_HOST or "smtp.gmail.com"
        smtp_port = event_setting.smtp_port or settings.SMTP_PORT or 587
        smtp_from_email = (event_setting.smtp_from_email or "").strip() or settings.FROM_EMAIL or "tickets@garbanight.in"
        smtp_from_name = (event_setting.smtp_from_name or "").strip() or settings.FROM_NAME or "GARBA NIGHT 2026"
        smtp_use_tls = event_setting.smtp_use_tls if hasattr(event_setting, "smtp_use_tls") else settings.SMTP_USE_TLS

        # Owner notification configuration
        owner_email = (
            getattr(event_setting, "owner_notification_email", None) or ""
        ).strip() or settings.OWNER_NOTIFICATION_EMAIL or "vinay18744@gmail.com"
        owner_phone = (
            getattr(event_setting, "owner_notification_phone", None) or ""
        ).strip() or settings.OWNER_NOTIFICATION_PHONE or "+91 98765 43210"
        owner_enabled = getattr(event_setting, "owner_notification_enabled", True)
        owner_webhook = getattr(event_setting, "owner_webhook_url", None) or settings.OWNER_WEBHOOK_URL

        return {
            "smtp_host": smtp_host,
            "smtp_port": smtp_port,
            "smtp_username": smtp_username if smtp_username else None,
            "smtp_password": smtp_password if smtp_password else None,
            "smtp_from_email": smtp_from_email,
            "smtp_from_name": smtp_from_name,
            "smtp_use_tls": smtp_use_tls,
            "owner_email": owner_email,
            "owner_phone": owner_phone,
            "owner_enabled": owner_enabled,
            "owner_webhook": owner_webhook,
        }

    @staticmethod
    def render_confirmation_html(booking: Booking, event_setting: EventSetting, qr_base64: str) -> str:
        primary_ticket = booking.tickets[0] if booking.tickets else None
        ticket_view_url = f"{settings.FRONTEND_URL}/ticket/{primary_ticket.qr_token_raw}" if primary_ticket else f"{settings.FRONTEND_URL}/success/{booking.booking_id}"
        pass_text = f"{booking.ticket_count} Official Admission Pass{'es' if booking.ticket_count > 1 else ''}"
        
        # We display the inline CID image; fallback to data URI if CID is not rendered by client
        qr_src = "cid:qrcode_ticket" if primary_ticket else qr_base64

        is_group = bool((getattr(booking, "group_discount", 0.0) or 0.0) > 0 or booking.ticket_count == 10)
        reg_amt = getattr(booking, "regular_amount", 0.0) or round(booking.ticket_count * booking.ticket_price, 2)
        disc_amt = getattr(booking, "group_discount", 0.0) or (599.0 if is_group else 0.0)
        subtotal_amt = booking.ticket_subtotal or (reg_amt - disc_amt)

        group_banner_html = ""
        if is_group:
            group_banner_html = f"""
              <div style="background: linear-gradient(135deg, rgba(212, 175, 55, 0.15) 0%, rgba(16, 185, 129, 0.15) 100%); border: 1px solid #d4af37; border-radius: 12px; padding: 16px 20px; margin-bottom: 22px; text-align: center;">
                <div style="font-size: 16px; font-weight: 900; color: #f3e4b2; letter-spacing: 1px; text-transform: uppercase;">
                  🎉 GROUP BOOKING CONFIRMED
                </div>
                <div style="font-size: 13px; font-weight: 800; color: #34d399; margin-top: 4px; letter-spacing: 0.5px;">
                  BUY 10, PAY FOR 9 • YOU SAVED ₹{disc_amt:,.2f}
                </div>
                <div style="font-size: 12px; color: #cbd5e1; margin-top: 6px;">
                  10 Tickets (9 Paid + 1 FREE Ticket) • All 10 tickets are 100% valid admission passes
                </div>
              </div>
            """

        price_rows_html = f"""
                      <tr>
                        <td style="padding: 6px 0; font-size: 13px; color: #94a3b8; width: 45%;">Admission Passes:</td>
                        <td style="padding: 6px 0; font-size: 13px; font-weight: 700; color: #f3e4b2; text-align: right;">{booking.ticket_count} Passes {'(BUY 10, PAY FOR 9)' if is_group else f'× ₹{booking.ticket_price:,.2f}'}</td>
                      </tr>
        """
        if is_group:
            price_rows_html += f"""
                      <tr>
                        <td style="padding: 6px 0; font-size: 13px; color: #94a3b8;">Regular Price:</td>
                        <td style="padding: 6px 0; font-size: 13px; font-weight: 600; color: #94a3b8; text-decoration: line-through; text-align: right;">₹{reg_amt:,.2f}</td>
                      </tr>
                      <tr>
                        <td style="padding: 6px 0; font-size: 13px; color: #34d399; font-weight: 700;">Group Discount (1 Free):</td>
                        <td style="padding: 6px 0; font-size: 13px; font-weight: 800; color: #34d399; text-align: right;">-₹{disc_amt:,.2f}</td>
                      </tr>
                      <tr>
                        <td style="padding: 6px 0; font-size: 13px; color: #94a3b8;">Ticket Amount (Subtotal):</td>
                        <td style="padding: 6px 0; font-size: 13px; font-weight: 700; color: #ffffff; text-align: right;">₹{subtotal_amt:,.2f}</td>
                      </tr>
            """
        else:
            price_rows_html += f"""
                      <tr>
                        <td style="padding: 6px 0; font-size: 13px; color: #94a3b8;">Ticket Subtotal:</td>
                        <td style="padding: 6px 0; font-size: 13px; font-weight: 700; color: #ffffff; text-align: right;">₹{subtotal_amt:,.2f}</td>
                      </tr>
            """

        price_rows_html += f"""
                      <tr>
                        <td style="padding: 6px 0; font-size: 13px; color: #94a3b8;">Payment Processing Fee:</td>
                        <td style="padding: 6px 0; font-size: 13px; color: #cbd5e1; text-align: right;">₹{(booking.payment_fee or 0.0):,.2f}</td>
                      </tr>
                      <tr>
                        <td style="padding: 6px 0; font-size: 13px; color: #94a3b8;">GST on Processing Fee (18%):</td>
                        <td style="padding: 6px 0; font-size: 13px; color: #cbd5e1; text-align: right;">₹{(booking.gst_amount or 0.0):,.2f}</td>
                      </tr>
                      <tr style="border-top: 1px solid #23293e;">
                        <td style="padding: 10px 0 6px; font-size: 14px; font-weight: 800; color: #f3e4b2;">TOTAL PAID:</td>
                        <td style="padding: 10px 0 6px; font-size: 16px; font-weight: 900; color: #34d399; text-align: right;">₹{booking.amount:,.2f} INR</td>
                      </tr>
        """
        if is_group:
            price_rows_html += f"""
                      <tr style="background: rgba(16, 185, 129, 0.08); border-radius: 6px;">
                        <td style="padding: 6px 8px; font-size: 12px; font-weight: 800; color: #34d399;">YOU SAVED:</td>
                        <td style="padding: 6px 8px; font-size: 13px; font-weight: 900; color: #34d399; text-align: right;">₹{disc_amt:,.2f}</td>
                      </tr>
            """

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Official Admission Pass • {event_setting.event_name}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #06070c; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #e2e8f0; -webkit-font-smoothing: antialiased;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color: #06070c; padding: 32px 12px;">
    <tr>
      <td align="center">
        <!-- Main Container -->
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width: 600px; background-color: #0d0f18; border: 1px solid #1f2335; border-top: 4px solid #d4af37; border-radius: 16px; overflow: hidden; box-shadow: 0 20px 45px rgba(0, 0, 0, 0.7);">
          
          <!-- Header Banner -->
          <tr>
            <td style="padding: 36px 28px 24px; text-align: center; background: radial-gradient(circle at 50% 0%, #171b2d 0%, #0d0f18 100%); border-bottom: 1px solid #1c2033;">
              <table role="presentation" cellspacing="0" cellpadding="0" border="0" align="center">
                <tr>
                  <td style="padding: 6px 14px; background: rgba(212, 175, 55, 0.1); border: 1px solid rgba(212, 175, 55, 0.3); border-radius: 9999px; text-align: center;">
                    <span style="font-size: 11px; font-weight: 800; letter-spacing: 2px; text-transform: uppercase; color: #f3e4b2;">
                      ✦ PREMIER CULTURAL GALA ✦
                    </span>
                  </td>
                </tr>
              </table>
              <h1 style="margin: 16px 0 4px; font-size: 28px; font-weight: 900; letter-spacing: 1.5px; color: #ffffff; text-transform: uppercase;">
                {event_setting.event_name}
              </h1>
              <p style="margin: 0; font-size: 12px; font-weight: 600; color: #94a3b8; letter-spacing: 1px; text-transform: uppercase;">
                Official Admission Pass & Electronic Tax Invoice
              </p>
            </td>
          </tr>

          <!-- Content Body -->
          <tr>
            <td style="padding: 28px 24px;">
              {group_banner_html}
              <p style="margin: 0 0 16px; font-size: 16px; font-weight: 700; color: #ffffff;">
                Dear {booking.customer_name},
              </p>
              <p style="margin: 0 0 24px; font-size: 14px; line-height: 1.6; color: #cbd5e1;">
                Your reservation for <strong style="color: #f3e4b2;">{event_setting.event_name}</strong> is officially confirmed. Your cryptographically secured digital pass and tax receipt details are provided below.
              </p>

              <!-- Digital Pass Card -->
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background: linear-gradient(145deg, #131724 0%, #0e111c 100%); border: 1px solid #282f48; border-radius: 14px; overflow: hidden; margin-bottom: 24px;">
                <tr>
                  <td style="padding: 20px; border-bottom: 1px solid #1f253a;">
                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                      <tr>
                        <td>
                          <span style="font-size: 10px; font-weight: 800; text-transform: uppercase; letter-spacing: 1.5px; color: #94a3b8;">Booking Reference</span>
                          <div style="font-size: 17px; font-family: monospace; font-weight: 800; color: #f3e4b2; margin-top: 2px;">
                            #{booking.booking_id}
                          </div>
                        </td>
                        <td align="right">
                          <span style="display: inline-block; padding: 4px 12px; background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.35); color: #34d399; font-size: 11px; font-weight: 800; border-radius: 9999px; text-transform: uppercase;">
                            ✓ {booking.payment_status}
                          </span>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>

                <tr>
                  <td style="padding: 16px 20px;">
                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                      <tr>
                        <td style="padding: 6px 0; font-size: 13px; color: #94a3b8; width: 45%;">Primary Attendee:</td>
                        <td style="padding: 6px 0; font-size: 13px; font-weight: 700; color: #ffffff; text-align: right;">{booking.customer_name}</td>
                      </tr>
                      {price_rows_html}
                      <tr>
                        <td style="padding: 4px 0; font-size: 11px; color: #94a3b8;">Payment Reference ID:</td>
                        <td style="padding: 4px 0; font-size: 11px; font-family: monospace; color: #60a5fa; text-align: right;">{booking.razorpay_payment_id or 'N/A'}</td>
                      </tr>
                      <tr>
                        <td style="padding: 4px 0; font-size: 11px; color: #94a3b8;">Registered Contact:</td>
                        <td style="padding: 4px 0; font-size: 11px; color: #cbd5e1; text-align: right;">{booking.phone}</td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>

              <!-- QR Code Admission Card -->
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background: #111422; border: 1px solid #23293e; border-radius: 14px; padding: 24px; text-align: center; margin-bottom: 24px;">
                <tr>
                  <td align="center">
                    <div style="font-size: 11px; font-weight: 800; letter-spacing: 1.5px; text-transform: uppercase; color: #d4af37; margin-bottom: 14px;">
                      OFFICIAL ENCRYPTED ADMISSION CODE
                    </div>
                    
                    <!-- White frame for QR to ensure 100% optical scanner contrast -->
                    <table role="presentation" cellspacing="0" cellpadding="0" border="0" align="center" style="background: #ffffff; padding: 12px; border-radius: 12px; border: 1px solid #cbd5e1; box-shadow: 0 4px 14px rgba(0,0,0,0.4);">
                      <tr>
                        <td align="center">
                          <img src="{qr_src}" alt="Entry QR Code" width="190" height="190" style="display: block; width: 190px; height: 190px; border: none; outline: none;" />
                        </td>
                      </tr>
                    </table>

                    <p style="margin: 14px 0 0; font-size: 12px; color: #94a3b8; line-height: 1.5;">
                      Scan this digital barcode at <strong style="color: #ffffff;">Turnstile Gate A</strong> for rapid admission.
                    </p>
                  </td>
                </tr>
              </table>

              <!-- Event Logistics Grid -->
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background: #0f121e; border-left: 3px solid #d4af37; border-radius: 0 10px 10px 0; padding: 18px 20px; margin-bottom: 24px;">
                <tr>
                  <td>
                    <div style="font-size: 11px; font-weight: 800; letter-spacing: 1.5px; text-transform: uppercase; color: #f3e4b2; margin-bottom: 8px;">
                      EVENT LOGISTICS & VENUE
                    </div>
                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="font-size: 13px; color: #cbd5e1; line-height: 1.7;">
                      <tr>
                        <td style="color: #94a3b8; width: 22%;">Event:</td>
                        <td style="color: #ffffff; font-weight: 600;">{event_setting.event_name}</td>
                      </tr>
                      <tr>
                        <td style="color: #94a3b8;">Date:</td>
                        <td style="color: #ffffff; font-weight: 600;">{event_setting.event_date}</td>
                      </tr>
                      <tr>
                        <td style="color: #94a3b8;">Timings:</td>
                        <td style="color: #ffffff; font-weight: 600;">Entry starts at 05:30 PM • Event: {event_setting.event_time}</td>
                      </tr>
                      <tr>
                        <td style="color: #94a3b8; vertical-align: top;">Venue:</td>
                        <td style="color: #ffffff; font-weight: 600;">{event_setting.venue_name}, {event_setting.venue_address}, {event_setting.venue_city}</td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>

              <!-- Attached PDF Notice -->
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background: rgba(212, 175, 55, 0.05); border: 1px solid rgba(212, 175, 55, 0.2); border-radius: 10px; padding: 14px 18px; margin-bottom: 26px;">
                <tr>
                  <td style="font-size: 13px; color: #e2e8f0; line-height: 1.6;">
                    📎 <strong style="color: #f3e4b2;">Official PDF Ticket Pass Attached:</strong> Your printable admission passes with anti-counterfeit holographic barcode and arena seating guide are attached to this email (<span style="font-family: monospace; color: #94a3b8;">{re.sub(r'[^a-zA-Z0-9]', '', event_setting.event_name)}_{booking.booking_id}_Tickets.pdf</span>).
                  </td>
                </tr>
              </table>

              <!-- CTA Button -->
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-bottom: 28px;">
                <tr>
                  <td align="center">
                    <a href="{ticket_view_url}" target="_blank" style="display: inline-block; background: linear-gradient(135deg, #d4af37 0%, #b89228 100%); color: #08090f; text-decoration: none; padding: 15px 36px; font-size: 14px; font-weight: 800; border-radius: 9999px; letter-spacing: 0.5px; box-shadow: 0 4px 18px rgba(212, 175, 55, 0.35);">
                      ACCESS LIVE DIGITAL PASS & PASSBOOK →
                    </a>
                  </td>
                </tr>
              </table>

              <!-- Entry Protocol -->
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="border-top: 1px solid #1c2033; padding-top: 20px;">
                <tr>
                  <td>
                    <div style="font-size: 11px; font-weight: 800; letter-spacing: 1.5px; text-transform: uppercase; color: #94a3b8; margin-bottom: 10px;">
                      IMPORTANT ENTRY PROTOCOLS
                    </div>
                    <ul style="margin: 0; padding-left: 18px; font-size: 12px; color: #94a3b8; line-height: 1.7;">
                      <li>Each digital QR code is cryptographically unique and permits exactly one admission.</li>
                      <li>Traditional festive attire (Chaniya Choli / Kurta Pajama / Kediyu) or smart cultural dress is encouraged.</li>
                      <li>Entry starts promptly at 05:30 PM. Gates close at 10:00 PM. Please arrive early to ensure seamless security processing.</li>
                      <li>All sales are non-refundable and non-transferable under official event guidelines.</li>
                    </ul>
                  </td>
                </tr>
              </table>

            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding: 24px; text-align: center; background-color: #080a10; border-top: 1px solid #181b29; font-size: 12px; color: #64748b; line-height: 1.6;">
              Questions regarding admission or logistics? Reach us directly at <a href="mailto:{event_setting.contact_email}" style="color: #94a3b8; text-decoration: underline;">{event_setting.contact_email}</a> or <span style="color: #94a3b8;">{event_setting.contact_phone}</span>.<br/>
              © 2026 {event_setting.event_name}. All rights reserved.
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    @staticmethod
    def render_owner_notification_html(
        booking: Booking,
        event_setting: EventSetting,
        remaining_capacity: int,
        total_capacity: int,
        total_sold_tickets: int = 0,
        total_revenue: float = 0.0,
        total_orders: int = 0,
        pending_orders: int = 0,
    ) -> str:
        admin_booking_url = f"{settings.FRONTEND_URL}/admin/bookings"
        sold_tickets = total_sold_tickets if total_sold_tickets > 0 else max(0, total_capacity - remaining_capacity)
        total_cap = max(1, total_capacity)
        occupancy_pct = round((sold_tickets / total_cap * 100), 1)
        bar_width = min(100, max(2, int(occupancy_pct)))
        clean_phone = re.sub(r'[^0-9]', '', booking.phone or '')
        wa_url = f"https://wa.me/{clean_phone}" if clean_phone else "#"
        booking_ist = format_ist_datetime(booking.created_at)
        dispatch_ist = format_ist_datetime(datetime.utcnow())

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Realtime Booking Dispatch & Inventory Snapshot • {event_setting.event_name}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #06070c; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #e2e8f0;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color: #06070c; padding: 28px 12px;">
    <tr>
      <td align="center">
        <!-- Main Card -->
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width: 620px; background-color: #0d0f18; border: 1px solid #1f2335; border-top: 4px solid #d4af37; border-radius: 16px; overflow: hidden; box-shadow: 0 20px 45px rgba(0, 0, 0, 0.7);">
          
          <!-- Alert Header -->
          <tr>
            <td style="padding: 26px 24px; text-align: center; background: radial-gradient(circle at 50% 0%, #171b2d 0%, #0d0f18 100%); border-bottom: 1px solid #1c2033;">
              <table role="presentation" cellspacing="0" cellpadding="0" border="0" align="center">
                <tr>
                  <td style="padding: 5px 14px; background: rgba(212, 175, 55, 0.12); border: 1px solid rgba(212, 175, 55, 0.35); border-radius: 9999px;">
                    <span style="font-size: 11px; font-weight: 800; letter-spacing: 1.5px; text-transform: uppercase; color: #f3e4b2;">
                      ⚡ EXECUTIVE DISPATCH ALERT • REALTIME INVENTORY
                    </span>
                  </td>
                </tr>
              </table>
              <h2 style="margin: 14px 0 4px; font-size: 22px; font-weight: 900; letter-spacing: 0.5px; color: #ffffff; text-transform: uppercase;">
                NEW TICKET BOOKING CONFIRMED
              </h2>
              <p style="margin: 0; font-size: 12px; color: #94a3b8;">
                {event_setting.event_name} • The Serenity Grove, Mysuru
              </p>
            </td>
          </tr>

          <!-- Realtime KPI Metric Grid (4 Cards) -->
          <tr>
            <td style="padding: 20px 24px 10px;">
              <div style="font-size: 11px; font-weight: 800; letter-spacing: 1.2px; text-transform: uppercase; color: #d4af37; margin-bottom: 12px;">
                📈 REALTIME SALES & INVENTORY SNAPSHOT
              </div>
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                <tr>
                  <!-- KPI 1: Live Tickets Sold -->
                  <td width="49%" style="padding: 14px; background: #131724; border: 1px solid #23293e; border-radius: 12px; text-align: left; vertical-align: top;">
                    <div style="font-size: 10px; font-weight: 800; text-transform: uppercase; color: #94a3b8; letter-spacing: 1px;">Total Tickets Sold</div>
                    <div style="font-size: 20px; font-weight: 900; color: #34d399; margin-top: 4px;">
                      {sold_tickets:,} <span style="font-size: 12px; font-weight: 600; color: #94a3b8;">Passes</span>
                    </div>
                    <div style="font-size: 11px; color: #a7f3d0; margin-top: 2px;">
                      ✓ {occupancy_pct}% of {total_capacity:,} Capacity
                    </div>
                  </td>
                  <td width="2%">&nbsp;</td>
                  <!-- KPI 2: Remaining Inventory -->
                  <td width="49%" style="padding: 14px; background: #131724; border: 1px solid #23293e; border-radius: 12px; text-align: left; vertical-align: top;">
                    <div style="font-size: 10px; font-weight: 800; text-transform: uppercase; color: #94a3b8; letter-spacing: 1px;">Remaining Passes</div>
                    <div style="font-size: 20px; font-weight: 900; color: #f3e4b2; margin-top: 4px;">
                      {remaining_capacity:,} <span style="font-size: 12px; font-weight: 600; color: #94a3b8;">Left</span>
                    </div>
                    <div style="font-size: 11px; color: #94a3b8; margin-top: 2px;">
                      Realtime Available Inventory
                    </div>
                  </td>
                </tr>
                <tr><td colspan="3" style="height: 10px;"></td></tr>
                <tr>
                  <!-- KPI 3: Gross Revenue -->
                  <td width="49%" style="padding: 14px; background: #131724; border: 1px solid #23293e; border-radius: 12px; text-align: left; vertical-align: top;">
                    <div style="font-size: 10px; font-weight: 800; text-transform: uppercase; color: #94a3b8; letter-spacing: 1px;">Total Revenue (Paid)</div>
                    <div style="font-size: 20px; font-weight: 900; color: #34d399; margin-top: 4px;">
                      ₹{int(total_revenue):,}
                    </div>
                    <div style="font-size: 11px; color: #94a3b8; margin-top: 2px;">
                      {total_orders} Confirmed Orders
                    </div>
                  </td>
                  <td width="2%">&nbsp;</td>
                  <!-- KPI 4: This Order Value -->
                  <td width="49%" style="padding: 14px; background: #131724; border: 1px solid #23293e; border-radius: 12px; text-align: left; vertical-align: top;">
                    <div style="font-size: 10px; font-weight: 800; text-transform: uppercase; color: #94a3b8; letter-spacing: 1px;">This Order</div>
                    <div style="font-size: 20px; font-weight: 900; color: #ffffff; margin-top: 4px;">
                      ₹{int(booking.amount):,}
                    </div>
                    <div style="font-size: 11px; color: #f3e4b2; margin-top: 2px;">
                      +{booking.ticket_count} Pass{'es' if booking.ticket_count > 1 else ''} booked
                    </div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Live Arena Capacity Progress Bar -->
          <tr>
            <td style="padding: 8px 24px 16px;">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background: #111422; border: 1px solid #23293e; border-radius: 12px; padding: 14px 16px;">
                <tr>
                  <td>
                    <div style="display: flex; justify-content: space-between; font-size: 12px; font-weight: 700; color: #cbd5e1; margin-bottom: 6px;">
                      <span>🏟️ Arena Capacity Progress</span>
                      <span style="color: #34d399;">{sold_tickets:,} / {total_capacity:,} Passes ({occupancy_pct}%)</span>
                    </div>
                    <!-- Outer progress track -->
                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background: #1c2236; border-radius: 9999px; height: 10px; overflow: hidden;">
                      <tr>
                        <td width="{bar_width}%" style="background: linear-gradient(90deg, #d4af37 0%, #34d399 100%); height: 10px; border-radius: 9999px;"></td>
                        <td width="{max(0, 100 - bar_width)}%"></td>
                      </tr>
                    </table>
                    <div style="font-size: 11px; color: #94a3b8; margin-top: 8px;">
                      ⚡ <strong>Inventory Summary:</strong> <span style="color: #34d399; font-weight: 700;">{sold_tickets:,} sold</span> • <span style="color: #f3e4b2; font-weight: 700;">{remaining_capacity:,} remaining</span> of {total_capacity:,} total tickets{f' • {pending_orders} order(s) pending review' if pending_orders else ''}.
                    </div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Attendee & Transaction Audit Table -->
          <tr>
            <td style="padding: 8px 24px 24px;">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background: #111422; border: 1px solid #23293e; border-radius: 14px; overflow: hidden;">
                <tr>
                  <td colspan="2" style="padding: 14px 18px; background: #15192b; border-bottom: 1px solid #23293e; font-size: 12px; font-weight: 800; text-transform: uppercase; letter-spacing: 1px; color: #d4af37;">
                    Transaction & Customer Audit Details
                  </td>
                </tr>
                <tr>
                  <td style="padding: 11px 18px; font-size: 13px; color: #94a3b8; border-bottom: 1px solid #1a1e30; width: 38%;">Booking ID:</td>
                  <td style="padding: 11px 18px; font-size: 13px; font-family: monospace; font-weight: 800; color: #f3e4b2; border-bottom: 1px solid #1a1e30; text-align: right;">#{booking.booking_id}</td>
                </tr>
                <tr>
                  <td style="padding: 11px 18px; font-size: 13px; color: #94a3b8; border-bottom: 1px solid #1a1e30;">Customer Name:</td>
                  <td style="padding: 11px 18px; font-size: 13px; font-weight: 700; color: #ffffff; border-bottom: 1px solid #1a1e30; text-align: right;">{booking.customer_name}</td>
                </tr>
                <tr>
                  <td style="padding: 11px 18px; font-size: 13px; color: #94a3b8; border-bottom: 1px solid #1a1e30;">Email Address:</td>
                  <td style="padding: 11px 18px; font-size: 13px; border-bottom: 1px solid #1a1e30; text-align: right;">
                    <a href="mailto:{booking.email}" style="color: #60a5fa; text-decoration: none;">{booking.email}</a>
                  </td>
                </tr>
                <tr>
                  <td style="padding: 11px 18px; font-size: 13px; color: #94a3b8; border-bottom: 1px solid #1a1e30;">Mobile Phone:</td>
                  <td style="padding: 11px 18px; font-size: 13px; border-bottom: 1px solid #1a1e30; text-align: right;">
                    <a href="tel:{booking.phone}" style="color: #60a5fa; text-decoration: none;">{booking.phone}</a>
                    {f' • <a href="{wa_url}" target="_blank" style="color: #34d399; font-weight: 700; text-decoration: none;">WhatsApp</a>' if clean_phone else ''}
                  </td>
                </tr>
                <tr>
                  <td style="padding: 11px 18px; font-size: 13px; color: #94a3b8; border-bottom: 1px solid #1a1e30;">Passes Purchased:</td>
                  <td style="padding: 11px 18px; font-size: 13px; font-weight: 700; color: #ffffff; border-bottom: 1px solid #1a1e30; text-align: right;">
                    {booking.ticket_count} Pass{'es' if booking.ticket_count > 1 else ''}
                  </td>
                </tr>
                <tr>
                  <td style="padding: 11px 18px; font-size: 13px; color: #94a3b8; border-bottom: 1px solid #1a1e30;">Total Amount Paid:</td>
                  <td style="padding: 11px 18px; font-size: 14px; font-weight: 800; color: #34d399; border-bottom: 1px solid #1a1e30; text-align: right;">
                    ₹{int(booking.amount):,}
                  </td>
                </tr>
                <tr>
                  <td style="padding: 11px 18px; font-size: 13px; color: #94a3b8; border-bottom: 1px solid #1a1e30;">Payment Status:</td>
                  <td style="padding: 11px 18px; font-size: 13px; border-bottom: 1px solid #1a1e30; text-align: right;">
                    <span style="color: #34d399; font-weight: 800;">✓ {booking.payment_status}</span>
                    <span style="color: #94a3b8; font-size: 11px;">({booking.payment_method})</span>
                  </td>
                </tr>
                {f'<tr><td style="padding: 11px 18px; font-size: 13px; color: #94a3b8; border-bottom: 1px solid #1a1e30;">UTR / Ref No:</td><td style="padding: 11px 18px; font-size: 13px; font-family: monospace; font-weight: 700; color: #fbbf24; border-bottom: 1px solid #1a1e30; text-align: right;">{booking.utr_number}</td></tr>' if booking.utr_number else ''}
                <tr>
                  <td style="padding: 11px 18px; font-size: 13px; color: #94a3b8; border-bottom: 1px solid #1a1e30;">Booking Timestamp:</td>
                  <td style="padding: 11px 18px; font-size: 13px; font-weight: 700; color: #f3e4b2; border-bottom: 1px solid #1a1e30; text-align: right;">
                    {booking_ist}
                  </td>
                </tr>
                <tr>
                  <td style="padding: 11px 18px; font-size: 13px; color: #94a3b8; border-bottom: 1px solid #1a1e30;">Dispatch Time:</td>
                  <td style="padding: 11px 18px; font-size: 12px; color: #94a3b8; border-bottom: 1px solid #1a1e30; text-align: right;">
                    {dispatch_ist}
                  </td>
                </tr>
                <tr>
                  <td style="padding: 11px 18px; font-size: 13px; color: #94a3b8;">Venue & Schedule:</td>
                  <td style="padding: 11px 18px; font-size: 12px; color: #cbd5e1; text-align: right;">
                    <strong>Entry: 05:30 PM</strong> | Event: <strong>{event_setting.event_time}</strong><br/>
                    {event_setting.venue_name}, {event_setting.venue_address}
                  </td>
                </tr>
              </table>

              <!-- CTA Button -->
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-top: 22px;">
                <tr>
                  <td align="center">
                    <a href="{admin_booking_url}" target="_blank" style="display: inline-block; background: linear-gradient(135deg, #d4af37 0%, #b89228 100%); color: #08090f; text-decoration: none; padding: 14px 34px; font-size: 13px; font-weight: 800; border-radius: 9999px; letter-spacing: 0.5px; box-shadow: 0 4px 18px rgba(212, 175, 55, 0.35);">
                      OPEN LIVE ADMIN BOOKINGS DASHBOARD →
                    </a>
                  </td>
                </tr>
              </table>

            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding: 18px 24px; text-align: center; background-color: #080a10; border-top: 1px solid #181b29; font-size: 12px; color: #64748b;">
              {event_setting.event_name} Dispatch Engine • Indian Standard Time (IST) Audit Trail
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


    @classmethod
    def send_confirmation_email(cls, booking_id: str, db: Session) -> bool:
        """Sends confirmation email to the ticket customer with attached PDF passes and inline QR code."""
        booking = db.query(Booking).filter(Booking.booking_id == booking_id).first()
        if not booking:
            app_logger.error(f"Cannot send customer email: Booking {booking_id} not found.")
            return False

        event_setting = db.query(EventSetting).first() or EventSetting()
        config = cls.get_smtp_config(db)

        # Check if SMTP is configured
        if not config["smtp_username"] or not config["smtp_password"]:
            app_logger.warning(
                f"[EMAIL NOTICE] Cannot dispatch email to customer {booking.email}: "
                f"SMTP credentials missing. Please set your Gmail App Password in Admin Settings or backend/.env."
            )
            booking.email_status = "NOT_CONFIGURED"
            booking.email_error = "SMTP credentials missing. Please configure your Gmail App Password in Admin Settings or backend/.env."
            db.commit()
            return False

        try:
            primary_ticket = booking.tickets[0] if booking.tickets else None
            qr_base64 = ""
            qr_bytes = None
            if primary_ticket:
                qr_base64 = qr_service.generate_qr_base64(primary_ticket.qr_token_raw)
                try:
                    qr_bytes = qr_service.generate_qr_bytes(primary_ticket.qr_token_raw)
                except Exception as qr_err:
                    app_logger.warning(f"Could not generate QR bytes for inline image: {qr_err}")

            html_content = cls.render_confirmation_html(booking, event_setting, qr_base64)

            # Use related multipart to allow inline images (CID) + attachments
            msg = MIMEMultipart("related")
            is_group = bool((getattr(booking, "group_discount", 0.0) or 0.0) > 0 or booking.ticket_count == 10)
            if is_group:
                msg["Subject"] = f"🎉 GROUP BOOKING CONFIRMED (BUY 10, PAY FOR 9) — {event_setting.event_name} (#{booking.booking_id})"
            else:
                msg["Subject"] = f"🎟️ {event_setting.event_name} — Official Admission Pass & Invoice (#{booking.booking_id})"
            msg["From"] = f"{config['smtp_from_name']} <{config['smtp_from_email']}>"
            msg["To"] = booking.email

            # Attach HTML body
            msg_alt = MIMEMultipart("alternative")
            msg_alt.attach(MIMEText(html_content, "html"))
            msg.attach(msg_alt)

            # Embed inline QR code image if bytes are available
            if qr_bytes:
                try:
                    qr_image = MIMEImage(qr_bytes, "png")
                    qr_image.add_header("Content-ID", "<qrcode_ticket>")
                    qr_image.add_header("Content-Disposition", "inline", filename="qrcode.png")
                    msg.attach(qr_image)
                except Exception as img_err:
                    app_logger.warning(f"Could not attach inline QR image: {img_err}")

            # Attach PDF ticket bundle
            try:
                pdf_bytes = ticket_service.generate_booking_bundle_pdf(booking, event_setting)
                event_slug = re.sub(r'[^a-zA-Z0-9]', '', event_setting.event_name) or "Tickets"
                pdf_filename = f"{event_slug}_{booking.booking_id}_Tickets.pdf"
                part = MIMEApplication(pdf_bytes, Name=pdf_filename)
                part["Content-Disposition"] = f'attachment; filename="{pdf_filename}"'
                msg.attach(part)
            except Exception as pdf_err:
                app_logger.warning(f"Could not attach PDF tickets: {pdf_err}")

            # Send via SMTP
            cls._dispatch_smtp_message(msg, config)

            app_logger.info(f"Confirmation email successfully sent via SMTP to customer {booking.email}")
            booking.email_status = "SENT"
            booking.email_sent_at = datetime.utcnow()
            booking.email_error = None
            db.commit()
            return True

        except Exception as e:
            err_msg = str(e)
            app_logger.error(f"Failed to send customer confirmation email for booking {booking_id}: {err_msg}")
            booking.email_status = "FAILED"
            booking.email_error = err_msg[:500]
            db.commit()
            return False

    @classmethod
    def send_owner_notification(cls, booking_id: str, db: Session) -> bool:
        """Sends immediate booking notification message to the event owner/organizer with realtime inventory."""
        booking = db.query(Booking).filter(Booking.booking_id == booking_id).first()
        if not booking:
            app_logger.error(f"Cannot send owner alert: Booking {booking_id} not found.")
            return False

        event_setting = db.query(EventSetting).first() or EventSetting()
        config = cls.get_smtp_config(db)

        # Calculate live realtime capacity and sales statistics across all confirmed bookings
        total_sold_tickets = db.query(func.coalesce(func.sum(Booking.ticket_count), 0)).filter(
            Booking.booking_status == "CONFIRMED",
            Booking.payment_status == "PAID"
        ).scalar() or 0
        total_capacity = event_setting.total_capacity or 1500
        remaining_capacity = max(0, total_capacity - total_sold_tickets)
        occupancy_pct = round((total_sold_tickets / total_capacity * 100), 1) if total_capacity > 0 else 0.0

        total_revenue = db.query(func.coalesce(func.sum(Booking.amount), 0.0)).filter(
            Booking.booking_status == "CONFIRMED",
            Booking.payment_status == "PAID"
        ).scalar() or 0.0

        total_orders = db.query(func.count(Booking.id)).filter(
            Booking.booking_status == "CONFIRMED",
            Booking.payment_status == "PAID"
        ).scalar() or 0

        pending_orders = db.query(func.count(Booking.id)).filter(
            Booking.payment_status.in_(["PENDING_VERIFICATION", "VERIFICATION_PENDING", "PENDING"])
        ).scalar() or 0

        booking_ist = format_ist_datetime(booking.created_at)
        now_ist = format_ist_datetime(datetime.utcnow())

        # 1. ALWAYS emit formatted owner alert log (works like SMS / WhatsApp message dispatch log)
        sms_text = (
            f"🎟️ {event_setting.event_name.upper()}: {booking.customer_name} booked {booking.ticket_count} ticket(s) "
            f"for INR {int(booking.amount):,}! Booking #{booking.booking_id}. "
            f"Phone: {booking.phone} | Email: {booking.email}. "
            f"Order Time: {booking_ist} | "
            f"📊 REALTIME INVENTORY: {total_sold_tickets}/{total_capacity} Sold ({occupancy_pct}%) | "
            f"{remaining_capacity} passes remaining | Revenue: INR {int(total_revenue):,} ({total_orders} orders)."
        )
        app_logger.info(
            f"\n"
            f"================================================================================\n"
            f"📢 [OWNER INSTANT NOTIFICATION MESSAGE • REALTIME INVENTORY]\n"
            f"Target Owner Email: {config['owner_email']} | Owner Phone: {config['owner_phone']}\n"
            f"Alert: {sms_text}\n"
            f"================================================================================"
        )

        # 2. Check if owner notification is enabled
        if not config["owner_enabled"]:
            app_logger.info("Owner notifications are disabled in settings.")
            return True

        # 3. Optional Webhook dispatch (Discord / Slack / Telegram)
        if config["owner_webhook"]:
            try:
                webhook_payload = json.dumps({
                    "content": f"🚨 **New Booking Alert!** {booking.customer_name} booked **{booking.ticket_count} ticket(s)** for **₹{int(booking.amount):,}**! (ID: `{booking.booking_id}`) [Time: {booking_ist}]\n📊 **Realtime Inventory:** {total_sold_tickets}/{total_capacity} sold ({occupancy_pct}% full) | **{remaining_capacity} passes left** | Total Revenue: **₹{int(total_revenue):,}**",
                    "booking_id": booking.booking_id,
                    "customer_name": booking.customer_name,
                    "email": booking.email,
                    "phone": booking.phone,
                    "tickets": booking.ticket_count,
                    "amount": booking.amount,
                    "timestamp_ist": booking_ist,
                    "total_sold_tickets": total_sold_tickets,
                    "remaining_tickets": remaining_capacity,
                    "total_revenue": total_revenue,
                    "occupancy_pct": occupancy_pct,
                    "total_orders": total_orders
                }).encode("utf-8")

                req = urllib.request.Request(
                    config["owner_webhook"],
                    data=webhook_payload,
                    headers={"Content-Type": "application/json", "User-Agent": "GarbaNight-Webhook/1.0"}
                )
                with urllib.request.urlopen(req, timeout=5) as response:
                    app_logger.info(f"Owner webhook alert dispatched successfully (HTTP {response.status}).")
            except Exception as hook_err:
                app_logger.warning(f"Owner webhook dispatch error: {hook_err}")

        # 4. Email Alert to Owner
        if not config["smtp_username"] or not config["smtp_password"]:
            app_logger.info(
                f"[OWNER EMAIL PENDING] Owner email alert to {config['owner_email']} awaiting SMTP configuration."
            )
            booking.owner_notified = False
            booking.owner_notify_error = "SMTP credentials missing in .env / Admin Settings"
            db.commit()
            return False

        try:
            owner_html = cls.render_owner_notification_html(
                booking=booking,
                event_setting=event_setting,
                remaining_capacity=remaining_capacity,
                total_capacity=total_capacity,
                total_sold_tickets=total_sold_tickets,
                total_revenue=total_revenue,
                total_orders=total_orders,
                pending_orders=pending_orders,
            )

            # Build list of all recipient emails
            recipients = []
            if config.get("owner_email"):
                for em in config["owner_email"].replace(";", ",").split(","):
                    c = em.strip()
                    if c and "@" in c and c.lower() not in [r.lower() for r in recipients]:
                        recipients.append(c)

            # Owner emails come exclusively from EventSetting / OWNER_NOTIFICATION_EMAIL env var.
            # Never hard-code personal email addresses in source code.

            for recipient in recipients:
                try:
                    msg = MIMEMultipart()
                    msg["Subject"] = f"⚡ {event_setting.event_name.upper()}: {booking.ticket_count} Pass{'es' if booking.ticket_count > 1 else ''} Booked by {booking.customer_name} (₹{int(booking.amount):,}) [Sold: {total_sold_tickets}/{total_capacity}]"
                    msg["From"] = f"{config['smtp_from_name']} Alerts <{config['smtp_from_email']}>"
                    msg["To"] = recipient

                    msg.attach(MIMEText(owner_html, "html"))

                    cls._dispatch_smtp_message(msg, config)
                    app_logger.info(f"Owner instant booking notification sent to {recipient}")
                except Exception as rec_err:
                    app_logger.error(f"Error dispatching owner alert to {recipient}: {rec_err}")

            booking.owner_notified = True
            booking.owner_notified_at = datetime.utcnow()
            booking.owner_notify_error = None
            db.commit()
            return True

        except Exception as e:
            err_msg = str(e)
            app_logger.error(f"Failed to send owner notification email: {err_msg}")
            booking.owner_notified = False
            booking.owner_notify_error = err_msg[:500]
            db.commit()
            return False

    @classmethod
    def send_payment_submission_alert(cls, booking_id: str, db: Session) -> bool:
        """Sends an immediate verification alert to owners when an attendee submits manual UPI payment proof (UTR)."""
        booking = db.query(Booking).filter(Booking.booking_id == booking_id).first()
        if not booking:
            return False

        event_setting = db.query(EventSetting).first() or EventSetting()
        config = cls.get_smtp_config(db)

        if not config["smtp_username"] or not config["smtp_password"]:
            app_logger.info(f"[PAYMENT VERIFICATION ALERT PENDING] SMTP not configured for booking {booking_id}")
            return False

        try:
            total_sold_tickets = db.query(func.coalesce(func.sum(Booking.ticket_count), 0)).filter(
                Booking.booking_status == "CONFIRMED",
                Booking.payment_status == "PAID"
            ).scalar() or 0
            total_capacity = event_setting.total_capacity or 1500
            remaining_capacity = max(0, total_capacity - total_sold_tickets)
            submission_ist = format_ist_datetime(booking.created_at)

            admin_verify_url = f"{settings.FRONTEND_URL}/admin/verification"
            alert_html = f"""<!DOCTYPE html>
<html>
<body style="margin: 0; padding: 24px; background-color: #06070c; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #e2e8f0;">
  <div style="max-width: 580px; margin: 0 auto; background-color: #0d0f18; border: 1px solid #1f2335; border-top: 4px solid #f59e0b; border-radius: 16px; padding: 28px; box-shadow: 0 20px 45px rgba(0, 0, 0, 0.7);">
    <div style="display: inline-block; padding: 4px 12px; background: rgba(245, 158, 11, 0.15); border: 1px solid rgba(245, 158, 11, 0.35); border-radius: 9999px; font-size: 11px; font-weight: 800; letter-spacing: 1px; color: #fbbf24; text-transform: uppercase;">
      ⚠️ PAYMENT VERIFICATION REQUIRED
    </div>
    <h2 style="color: #ffffff; margin: 16px 0 6px; font-size: 22px;">New UPI Payment Proof Submitted</h2>
    <p style="color: #94a3b8; font-size: 13px; margin: 0 0 18px;">
      An attendee has submitted payment proof for {event_setting.event_name}. Please review and verify to issue tickets.
    </p>

    <!-- Realtime Inventory Banner -->
    <div style="background: #0f1322; border: 1px solid #1e2640; border-radius: 10px; padding: 10px 14px; margin-bottom: 18px; font-size: 12px; color: #cbd5e1;">
      📊 <strong>Live Inventory:</strong> <span style="color: #34d399; font-weight: 700;">{total_sold_tickets} sold</span> of {total_capacity} capacity • <span style="color: #f3e4b2; font-weight: 700;">{remaining_capacity} passes remaining</span>
    </div>

    <div style="background: #131724; border: 1px solid #23293e; border-radius: 12px; padding: 18px; margin-bottom: 24px;">
      <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
        <tr><td style="color: #94a3b8; padding: 6px 0;">Customer Name:</td><td style="color: #ffffff; font-weight: bold; text-align: right;">{booking.customer_name}</td></tr>
        <tr><td style="color: #94a3b8; padding: 6px 0;">Phone:</td><td style="color: #ffffff; font-weight: bold; text-align: right;">{booking.phone}</td></tr>
        <tr><td style="color: #94a3b8; padding: 6px 0;">Email:</td><td style="color: #ffffff; font-weight: bold; text-align: right;">{booking.email}</td></tr>
        <tr><td style="color: #94a3b8; padding: 6px 0;">Booking ID:</td><td style="color: #f3e4b2; font-family: monospace; font-weight: bold; text-align: right;">#{booking.booking_id}</td></tr>
        <tr><td style="color: #94a3b8; padding: 6px 0;">Tickets:</td><td style="color: #ffffff; font-weight: bold; text-align: right;">{booking.ticket_count} Pass{'es' if booking.ticket_count > 1 else ''}</td></tr>
        <tr><td style="color: #94a3b8; padding: 6px 0;">Amount Due:</td><td style="color: #34d399; font-weight: bold; font-size: 16px; text-align: right;">₹{int(booking.amount):,}</td></tr>
        <tr><td style="color: #94a3b8; padding: 6px 0;">Submitted UTR:</td><td style="color: #fbbf24; font-family: monospace; font-weight: bold; font-size: 14px; text-align: right;">{booking.utr_number or 'Pending'}</td></tr>
        <tr><td style="color: #94a3b8; padding: 6px 0;">Submission Time:</td><td style="color: #f3e4b2; font-weight: bold; text-align: right;">{submission_ist}</td></tr>
        <tr><td style="color: #94a3b8; padding: 6px 0;">Venue & Timings:</td><td style="color: #cbd5e1; text-align: right;">The Serenity Grove, Mysuru • Entry: 05:30 PM</td></tr>
      </table>
    </div>
    <div style="text-align: center;">
      <a href="{admin_verify_url}" style="display: inline-block; padding: 12px 28px; background: linear-gradient(135deg, #d4af37 0%, #f3e4b2 100%); color: #08090f; text-decoration: none; font-weight: 800; font-size: 13px; border-radius: 9999px; text-transform: uppercase; letter-spacing: 0.5px;">
        Open Verification Console →
      </a>
    </div>
  </div>
</body>
</html>"""

            recipients = []
            if config.get("owner_email"):
                for em in config["owner_email"].replace(";", ",").split(","):
                    c = em.strip()
                    if c and "@" in c and c.lower() not in [r.lower() for r in recipients]:
                        recipients.append(c)

            # Owner emails come exclusively from EventSetting / OWNER_NOTIFICATION_EMAIL env var.
            # Never hard-code personal email addresses in source code.

            for recipient in recipients:
                try:
                    msg = MIMEMultipart()
                    msg["Subject"] = f"⚠️ [ACTION REQUIRED] Payment Verification for {booking.customer_name} (₹{int(booking.amount):,}) — UTR: {booking.utr_number or 'N/A'}"
                    msg["From"] = f"{config['smtp_from_name']} Alerts <{config['smtp_from_email']}>"
                    msg["To"] = recipient
                    msg.attach(MIMEText(alert_html, "html"))
                    cls._dispatch_smtp_message(msg, config)
                    app_logger.info(f"Payment submission verification alert sent to {recipient}")
                except Exception as alert_err:
                    app_logger.error(f"Error dispatching verification alert to {recipient}: {alert_err}")

            return True
        except Exception as e:
            app_logger.error(f"Failed to send payment verification alert: {e}")
            return False

    @classmethod
    def test_smtp_connection(cls, to_email: Optional[str], db: Session) -> Dict[str, Any]:
        """Tests SMTP credentials and sends a test email to verify real delivery."""
        config = cls.get_smtp_config(db)
        target_email = (to_email or "").strip() or config["owner_email"]

        if not config["smtp_username"] or not config["smtp_password"]:
            return {
                "success": False,
                "error_code": "MISSING_CREDENTIALS",
                "message": (
                    "SMTP credentials are not configured! Please enter your SMTP Username "
                    "(e.g., your Gmail address) and SMTP Password (16-character Google App Password) "
                    "in Admin Settings or backend/.env."
                ),
                "diagnostics": {
                    "host": config["smtp_host"],
                    "port": config["smtp_port"],
                    "username_present": bool(config["smtp_username"]),
                    "password_present": bool(config["smtp_password"])
                }
            }

        try:
            event_setting = db.query(EventSetting).first() or EventSetting()
            msg = MIMEMultipart()
            msg["Subject"] = f"✨ {event_setting.event_name} — SMTP Mail Delivery Verified"
            msg["From"] = f"{config['smtp_from_name']} <{config['smtp_from_email']}>"
            msg["To"] = target_email

            test_html = f"""<!DOCTYPE html>
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #06070c; color: #e2e8f0; padding: 32px 12px; margin: 0;">
  <div style="max-width: 520px; margin: 0 auto; background-color: #0d0f18; border: 1px solid #1f2335; border-top: 4px solid #d4af37; border-radius: 16px; padding: 28px; text-align: center; box-shadow: 0 15px 35px rgba(0,0,0,0.6);">
    <div style="display: inline-block; padding: 5px 14px; background: rgba(212, 175, 55, 0.1); border: 1px solid rgba(212, 175, 55, 0.3); border-radius: 9999px; font-size: 11px; font-weight: 800; letter-spacing: 1.5px; text-transform: uppercase; color: #f3e4b2; margin-bottom: 12px;">
      ✦ SYSTEM VERIFICATION ✦
    </div>
    <h2 style="color: #ffffff; margin: 0 0 8px; font-size: 22px; font-weight: 900; text-transform: uppercase;">
      SMTP Mail Delivery <span style="color: #34d399;">Active</span>
    </h2>
    <p style="font-size: 14px; color: #94a3b8; line-height: 1.6; margin: 0 0 20px;">
      This test message confirms that your SMTP mail server is operational and transmitting real electronic tickets, PDF passes, and executive booking dispatch alerts for <strong style="color: #f3e4b2;">{event_setting.event_name}</strong>.
    </p>
    <div style="background: #111422; border: 1px solid #23293e; padding: 16px; border-radius: 12px; font-size: 13px; text-align: left; margin: 20px 0; color: #94a3b8; line-height: 1.8;">
      <div><strong style="color: #cbd5e1;">Host:</strong> {config['smtp_host']}:{config['smtp_port']}</div>
      <div><strong style="color: #cbd5e1;">Sender:</strong> {config['smtp_from_name']} &lt;{config['smtp_from_email']}&gt;</div>
      <div><strong style="color: #cbd5e1;">Recipient:</strong> {target_email}</div>
      <div><strong style="color: #cbd5e1;">Timestamp:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</div>
    </div>
    <p style="font-size: 12px; color: #34d399; font-weight: bold; margin: 0;">
      ✓ Automated customer QR ticket emails & owner instant SMS/Email notifications are ready!
    </p>
  </div>
</body>
</html>"""
            msg.attach(MIMEText(test_html, "html"))

            cls._dispatch_smtp_message(msg, config)

            return {
                "success": True,
                "message": f"Test email successfully dispatched to {target_email}! Please check your inbox (and spam folder).",
                "diagnostics": {
                    "host": config["smtp_host"],
                    "port": config["smtp_port"],
                    "recipient": target_email,
                    "sender": config["smtp_from_email"]
                }
            }

        except smtplib.SMTPAuthenticationError as auth_err:
            return {
                "success": False,
                "error_code": "AUTH_FAILED",
                "message": (
                    "SMTP Authentication Failed! If you are using Gmail, standard account passwords are NOT accepted. "
                    "You MUST generate a 16-character 'App Password':\n"
                    "1. Go to https://myaccount.google.com/security\n"
                    "2. Enable 2-Step Verification if not active\n"
                    "3. Search for 'App passwords'\n"
                    "4. Create an App password (e.g. named 'GarbaNight') and paste the 16 characters here."
                ),
                "details": str(auth_err)
            }
        except Exception as e:
            return {
                "success": False,
                "error_code": "CONNECTION_FAILED",
                "message": f"Failed to connect or send email: {str(e)}",
                "details": str(e)
            }

    @staticmethod
    def _dispatch_smtp_message(msg: MIMEMultipart, config: Dict[str, Any]):
        """Internal helper to dispatch email over SMTP with TLS or SSL support."""
        host = config["smtp_host"]
        port = int(config["smtp_port"])
        username = config["smtp_username"]
        password = config["smtp_password"]
        use_tls = config.get("smtp_use_tls", True)

        if port == 465:
            # SSL Connection
            with smtplib.SMTP_SSL(host, port, timeout=12) as server:
                server.login(username, password)
                server.send_message(msg)
        else:
            # STARTTLS Connection (port 587 or 25)
            with smtplib.SMTP(host, port, timeout=12) as server:
                if use_tls:
                    server.starttls()
                if username and password:
                    server.login(username, password)
                server.send_message(msg)

email_service = EmailService()
