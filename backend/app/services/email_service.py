import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import urllib.request
import urllib.error
import json
import re
import base64
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.config import settings
from app.models.booking import Booking
from app.models.event_setting import EventSetting
from app.services.qr_service import qr_service
from app.services.ticket_service import ticket_service
from app.utils.logger import app_logger
from app.utils.validators import validate_email_format, is_placeholder_email

def format_ist_datetime(dt: Optional[datetime] = None) -> str:
    """Converts a UTC datetime to Indian Standard Time (IST, UTC+5:30) and formats it cleanly."""
    if not dt:
        dt = datetime.utcnow()
    ist_offset = timedelta(hours=5, minutes=30)
    ist_dt = dt + ist_offset
    return ist_dt.strftime("%d %b %Y, %I:%M:%S %p IST")

class EmailService:
    @classmethod
    def get_email_config(cls, db: Session) -> Dict[str, Any]:
        """Resolves Email provider, Resend API key, SMTP, and Owner notification settings from EventSetting in DB or .env fallback."""
        event_setting = db.query(EventSetting).first()
        if not event_setting:
            event_setting = EventSetting()

        # Resend API Key: environment variable takes precedence (Railway), then settings, then DB
        resend_api_key = (
            os.environ.get("RESEND_API_KEY", "").strip()
            or (settings.RESEND_API_KEY or "").strip()
            or (getattr(event_setting, "resend_api_key", None) or "").strip()
        )

        # Provider determination:
        # 1. Environment variable EMAIL_PROVIDER (e.g. Railway config)
        # 2. Database event_setting.email_provider
        # 3. Default to resend if resend_api_key is set
        # 4. Default to resend
        os_env_provider = os.environ.get("EMAIL_PROVIDER", "").strip().lower()
        db_provider = (getattr(event_setting, "email_provider", None) or "").strip().lower()
        settings_provider = (getattr(settings, "EMAIL_PROVIDER", "") or "").strip().lower()

        if os_env_provider in ("resend", "smtp", "console"):
            email_provider = os_env_provider
        elif db_provider in ("resend", "smtp", "console"):
            email_provider = db_provider
        elif settings_provider in ("resend", "smtp", "console"):
            email_provider = settings_provider
        elif resend_api_key:
            email_provider = "resend"
        else:
            email_provider = "resend"

        smtp_username = (
            os.environ.get("SMTP_USERNAME", "").strip()
            or (settings.SMTP_USERNAME or "").strip()
            or (event_setting.smtp_username or "").strip()
        )
        smtp_password = (
            os.environ.get("SMTP_PASSWORD", "").strip()
            or (settings.SMTP_PASSWORD or "").strip()
            or (event_setting.smtp_password or "").strip()
        )
        smtp_host = (
            os.environ.get("SMTP_HOST", "").strip()
            or (settings.SMTP_HOST or "").strip()
            or (event_setting.smtp_host or "").strip()
            or "smtp.gmail.com"
        )
        smtp_port = int(
            os.environ.get("SMTP_PORT", "").strip()
            or settings.SMTP_PORT
            or event_setting.smtp_port
            or 587
        )
        is_prod = (settings.ENVIRONMENT == "production")

        smtp_from_email = (
            os.environ.get("FROM_EMAIL", "").strip()
            or (settings.FROM_EMAIL or "").strip()
            or (event_setting.smtp_from_email or "").strip()
            or ("" if is_prod else "onboarding@resend.dev")
        )
        smtp_from_name = (
            os.environ.get("FROM_NAME", "").strip()
            or (settings.FROM_NAME or "").strip()
            or (event_setting.smtp_from_name or "").strip()
            or "NAVRANG 2026"
        )
        smtp_use_tls = getattr(event_setting, "smtp_use_tls", True) if hasattr(event_setting, "smtp_use_tls") else settings.SMTP_USE_TLS

        # Owner notification configuration (environment variable takes precedence, NO hardcoded fallback)
        owner_email = (
            os.environ.get("OWNER_NOTIFICATION_EMAIL", "").strip()
            or (settings.OWNER_NOTIFICATION_EMAIL or "").strip()
            or os.environ.get("ADMIN_NOTIFICATION_EMAIL", "").strip()
            or getattr(settings, "ADMIN_NOTIFICATION_EMAIL", "").strip()
            or (getattr(event_setting, "owner_notification_email", None) or "").strip()
        )
        owner_phone = (
            (getattr(event_setting, "owner_notification_phone", None) or "").strip()
            or (settings.OWNER_NOTIFICATION_PHONE or "").strip()
        )
        owner_enabled = getattr(event_setting, "owner_notification_enabled", True)
        owner_webhook = getattr(event_setting, "owner_webhook_url", None) or settings.OWNER_WEBHOOK_URL

        # Admin ticket confirmation notification email (server-side only, takes precedence from env, NO hardcoded fallback)
        admin_email = (
            os.environ.get("ADMIN_NOTIFICATION_EMAIL", "").strip()
            or getattr(settings, "ADMIN_NOTIFICATION_EMAIL", "").strip()
            or os.environ.get("OWNER_NOTIFICATION_EMAIL", "").strip()
            or getattr(settings, "OWNER_NOTIFICATION_EMAIL", "").strip()
            or (getattr(event_setting, "owner_notification_email", None) or "").strip()
        )

        return {
            "email_provider": email_provider,
            "resend_api_key": resend_api_key if resend_api_key else None,
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
            "admin_email": admin_email,
        }

    @classmethod
    def get_smtp_config(cls, db: Session) -> Dict[str, Any]:
        """Backward compatible helper resolving email and SMTP configuration."""
        return cls.get_email_config(db)

    @classmethod
    def _dispatch_resend_email(
        cls,
        to_emails: List[str],
        subject: str,
        html_content: str,
        config: Dict[str, Any],
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Dispatches email via Resend HTTPS REST API (Port 443) - completely bypasses cloud SMTP port blocks."""
        api_key = config.get("resend_api_key")
        if not api_key:
            raise ValueError(
                "Resend API Key is not configured. Please set RESEND_API_KEY in environment or Admin Settings."
            )

        from_name = config.get("smtp_from_name") or "NAVRANG 2026"
        from_email = (config.get("smtp_from_email") or "").strip()

        if settings.ENVIRONMENT == "production":
            if not from_email or "onboarding@resend.dev" in from_email.lower():
                raise ValueError(
                    "Production requires a configured and verified FROM_EMAIL (e.g. tickets@heritageproduction.online). "
                    "Cannot silently use onboarding@resend.dev in production. Please set FROM_EMAIL in Railway environment variables."
                )
        elif not from_email:
            from_email = "onboarding@resend.dev"

        from_header = f"{from_name} <{from_email}>"

        payload: Dict[str, Any] = {
            "from": from_header,
            "to": to_emails,
            "subject": subject,
            "html": html_content,
        }

        if attachments:
            resend_attachments = []
            for att in attachments:
                content = att["content_bytes"]
                if isinstance(content, bytes):
                    b64_content = base64.b64encode(content).decode("utf-8")
                else:
                    b64_content = content
                resend_attachments.append({
                    "filename": att["filename"],
                    "content": b64_content,
                })
            payload["attachments"] = resend_attachments

        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            "https://api.resend.com/emails",
            data=req_data,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "NAVRANG-Tickets/1.0",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                body = response.read().decode("utf-8")
                return {"success": True, "data": json.loads(body) if body else {}}
        except urllib.error.HTTPError as http_err:
            err_body = http_err.read().decode("utf-8", errors="ignore")
            try:
                err_json = json.loads(err_body)
                err_msg = err_json.get("message") or err_body
            except Exception:
                err_msg = err_body or str(http_err)

            # In production, do not silently fallback to onboarding@resend.dev! Fail clearly!
            if settings.ENVIRONMENT == "production":
                raise RuntimeError(f"Resend API Error (HTTP {http_err.code}): {err_msg}") from http_err

            # Auto-fallback: For non-production development/test only
            if ("domain" in err_msg.lower() or "not verified" in err_msg.lower()) and "onboarding@resend.dev" not in from_email:
                app_logger.warning(
                    f"Resend domain verification required for {from_email}. Falling back to onboarding@resend.dev for test dispatch."
                )
                payload["from"] = f"{from_name} <onboarding@resend.dev>"
                retry_req = urllib.request.Request(
                    "https://api.resend.com/emails",
                    data=json.dumps(payload).encode("utf-8"),
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                        "User-Agent": "NAVRANG-Tickets/1.0",
                    },
                    method="POST",
                )
                try:
                    with urllib.request.urlopen(retry_req, timeout=15) as fb_resp:
                        body = fb_resp.read().decode("utf-8")
                        return {"success": True, "data": json.loads(body) if body else {}, "fallback_used": True}
                except Exception as fb_err:
                    raise RuntimeError(f"Resend API Error: {err_msg}") from fb_err

            raise RuntimeError(f"Resend API Error (HTTP {http_err.code}): {err_msg}") from http_err
        except Exception as e:
            raise RuntimeError(f"Resend HTTP request failed: {str(e)}") from e

    @classmethod
    def _dispatch_smtp_flow(
        cls,
        to_emails: List[str],
        subject: str,
        html_content: str,
        config: Dict[str, Any],
        attachments: Optional[List[Dict[str, Any]]] = None,
        is_owner: bool = False,
        qr_bytes: Optional[bytes] = None,
    ) -> Dict[str, Any]:
        """Internal helper for standard SMTP message creation and delivery."""
        from_name = config.get("smtp_from_name") or "NAVRANG 2026"
        from_email = config.get("smtp_from_email") or "tickets@garbanight.in"

        for recipient in to_emails:
            msg = MIMEMultipart("related")
            msg["Subject"] = subject
            msg["From"] = f"{from_name} <{from_email}>"
            msg["To"] = recipient

            # Attach HTML
            msg_alt = MIMEMultipart("alternative")
            msg_alt.attach(MIMEText(html_content, "html"))
            msg.attach(msg_alt)

            # Embed inline QR code image if bytes available
            if qr_bytes:
                try:
                    qr_image = MIMEImage(qr_bytes, "png")
                    qr_image.add_header("Content-ID", "<qrcode_ticket>")
                    qr_image.add_header("Content-Disposition", "inline", filename="qrcode.png")
                    msg.attach(qr_image)
                except Exception as img_err:
                    app_logger.warning(f"Could not attach inline QR image: {img_err}")

            # Attach files (PDF, etc.)
            if attachments:
                for att in attachments:
                    try:
                        filename = att.get("filename", "document.pdf")
                        content = att.get("content_bytes")
                        if isinstance(content, str):
                            content = base64.b64decode(content)
                        part = MIMEApplication(content, Name=filename)
                        part["Content-Disposition"] = f'attachment; filename="{filename}"'
                        msg.attach(part)
                    except Exception as att_err:
                        app_logger.warning(f"Could not attach file {att.get('filename')}: {att_err}")

            cls._dispatch_smtp_message(msg, config)

        return {"success": True, "provider": "smtp", "to": to_emails}

    @classmethod
    def _dispatch_message(
        cls,
        to_emails: List[str],
        subject: str,
        html_content: str,
        config: Dict[str, Any],
        attachments: Optional[List[Dict[str, Any]]] = None,
        is_owner: bool = False,
        qr_bytes: Optional[bytes] = None,
    ) -> Dict[str, Any]:
        """Provider-aware message dispatcher: routes email through Resend, SMTP, or Console based on active provider configuration with automatic SMTP->Resend fallback."""
        provider = (config.get("email_provider") or "resend").lower().strip()
        log_prefix = "[OWNER EMAIL]" if is_owner else "[EMAIL]"
        msg_type = "booking notification" if is_owner else "customer confirmation"
        has_resend = bool(config.get("resend_api_key"))
        has_smtp = bool(config.get("smtp_username") and config.get("smtp_password"))

        # Validate recipient list and enforce placeholder protection
        allow_placeholders = getattr(settings, "ALLOW_PLACEHOLDER_EMAILS", False)
        clean_recipients: List[str] = []
        for raw_item in to_emails:
            for em in (raw_item or "").replace(";", ",").split(","):
                clean_em = em.strip().lower()
                if not clean_em:
                    continue
                if not validate_email_format(clean_em):
                    app_logger.warning(f"{log_prefix} Rejected malformed recipient email: '{clean_em}'")
                    continue
                if is_placeholder_email(clean_em) and not allow_placeholders:
                    app_logger.warning(f"{log_prefix} Blocked placeholder recipient email to prevent bounce: '{clean_em}'")
                    continue
                if clean_em not in clean_recipients:
                    clean_recipients.append(clean_em)

        if not clean_recipients:
            err = f"No deliverable recipient email address found. Refusing to send to placeholder/invalid address (given: {to_emails})."
            app_logger.error(f"{log_prefix} {err}")
            raise ValueError(err)

        to_emails = clean_recipients

        # -------------------------------------------------------------
        # 1. RESEND DISPATCH (Port 443 HTTPS REST API)
        # -------------------------------------------------------------
        if provider == "resend":
            if not has_resend:
                err = "Resend API Key is not configured. Please set RESEND_API_KEY in environment or Admin Settings."
                app_logger.error(f"{log_prefix} Resend {'owner email' if is_owner else 'customer email'} failed: {err}")
                raise ValueError(err)

            app_logger.info(f"{log_prefix} Sending {msg_type} via Resend to {to_emails}")
            try:
                res = cls._dispatch_resend_email(to_emails, subject, html_content, config, attachments)
                app_logger.info(f"{log_prefix} {msg_type.capitalize()} sent successfully")
                return res
            except Exception as e:
                err_str = str(e)
                app_logger.error(f"{log_prefix} Resend {'owner email' if is_owner else 'customer email'} failed: {err_str}")
                raise

        # -------------------------------------------------------------
        # 2. SMTP DISPATCH (Standard SMTP with Resend failover)
        # -------------------------------------------------------------
        elif provider == "smtp":
            if not has_smtp:
                if has_resend:
                    app_logger.warning(f"{log_prefix} SMTP credentials missing; auto-routing via Resend API.")
                    app_logger.info(f"{log_prefix} Sending {msg_type} via Resend to {to_emails}")
                    res = cls._dispatch_resend_email(to_emails, subject, html_content, config, attachments)
                    app_logger.info(f"{log_prefix} {msg_type.capitalize()} sent successfully to {to_emails}")
                    return res
                err = "SMTP credentials missing. Please set SMTP username/password or RESEND_API_KEY."
                app_logger.error(f"{log_prefix} SMTP {'owner email' if is_owner else 'customer email'} failed: {err}")
                raise ValueError(err)

            app_logger.info(f"{log_prefix} Sending {msg_type} via SMTP to {to_emails}")
            try:
                res = cls._dispatch_smtp_flow(to_emails, subject, html_content, config, attachments, is_owner, qr_bytes)
                app_logger.info(f"{log_prefix} {msg_type.capitalize()} sent successfully to {to_emails}")
                return res
            except Exception as e:
                err_str = str(e)
                app_logger.error(f"{log_prefix} SMTP {'owner email' if is_owner else 'customer email'} failed: {err_str}")
                if has_resend:
                    app_logger.warning(f"{log_prefix} Outbound SMTP failed ({err_str}); initiating failover to Resend API...")
                    try:
                        res = cls._dispatch_resend_email(to_emails, subject, html_content, config, attachments)
                        app_logger.info(f"{log_prefix} {msg_type.capitalize()} sent successfully via Resend API fallback to {to_emails}")
                        return res
                    except Exception as fb_err:
                        app_logger.error(f"{log_prefix} Resend API fallback also failed: {fb_err}")
                raise

        # -------------------------------------------------------------
        # 3. CONSOLE DISPATCH (Development / Offline test mode)
        # -------------------------------------------------------------
        elif provider == "console":
            app_logger.info(f"{log_prefix} Sending {msg_type} via Console to {to_emails}")
            att_names = [a.get("filename", "attachment") for a in (attachments or [])]
            app_logger.info(
                f"\n"
                f"--------------------------------------------------------------------------------\n"
                f"{log_prefix} [CONSOLE EMAIL LOG]\n"
                f"To: {', '.join(to_emails)}\n"
                f"From: {config.get('smtp_from_name')} <{config.get('smtp_from_email')}>\n"
                f"Subject: {subject}\n"
                f"Attachments: {att_names}\n"
                f"Body length: {len(html_content)} characters\n"
                f"--------------------------------------------------------------------------------"
            )
            app_logger.info(f"{log_prefix} {msg_type.capitalize()} sent successfully to {to_emails}")
            return {"success": True, "provider": "console", "to": to_emails, "subject": subject}

        else:
            raise ValueError(f"Unsupported EMAIL_PROVIDER: {provider}. Supported: resend, smtp, console.")

    @staticmethod
    def render_confirmation_html(booking: Booking, event_setting: EventSetting, qr_base64: str, provider: str = "resend") -> str:
        primary_ticket = booking.tickets[0] if booking.tickets else None
        ticket_view_url = f"{settings.FRONTEND_URL}/ticket/{primary_ticket.qr_token_raw}" if primary_ticket else f"{settings.FRONTEND_URL}/success/{booking.booking_id}"
        pass_text = f"{booking.ticket_count} Official Admission Pass{'es' if booking.ticket_count > 1 else ''}"
        
        # Resolve scannable QR image source:
        # Note: Gmail, Outlook.com, and Yahoo strip base64 data: URIs in email bodies.
        # We generate a high-contrast public CDN QR code URL that Gmail's image proxy renders immediately,
        # with fallback to CID for offline SMTP readers.
        raw_qr_token = primary_ticket.qr_token_raw if (primary_ticket and primary_ticket.qr_token_raw) else (getattr(booking, "booking_id", None) or "NAV2026")
        cdn_qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={raw_qr_token}&color=0f0c20&bgcolor=ffffff"

        if provider == "smtp":
            qr_src = "cid:qrcode_ticket" if (primary_ticket and primary_ticket.qr_token_raw) else cdn_qr_url
        else:
            qr_src = cdn_qr_url

        is_group = bool((getattr(booking, "group_discount", 0.0) or 0.0) > 0 or booking.ticket_count == 10)
        reg_amt = getattr(booking, "regular_amount", 0.0) or round(booking.ticket_count * booking.ticket_price, 2)
        disc_amt = getattr(booking, "group_discount", 0.0) or (599.0 if is_group else 0.0)
        subtotal_amt = booking.ticket_subtotal or (reg_amt - disc_amt)

        offer_title_display = getattr(booking, "offer_title", None)
        if not offer_title_display:
            if is_group:
                offer_title_display = "Early Bird — Group of 10" if booking.amount == 4999.0 else "Group Entry (10 Passes)"
            elif booking.ticket_count == 2:
                offer_title_display = "Early Bird — Couple Entry" if booking.amount == 999.0 else "Couple Entry (2 Passes)"
            elif getattr(booking, "child_name", None) or booking.ticket_price == 300.0:
                offer_title_display = "Kids (5–12 years)"
            else:
                offer_title_display = "Early Bird — Stag Entry" if booking.amount == 599.0 else "Stag Entry"

        child_row_html = ""
        if getattr(booking, "child_name", None):
            child_row_html = f"""
                      <tr>
                        <td style="padding: 6px 0; font-size: 13px; color: #94a3b8;">Child Attendee:</td>
                        <td style="padding: 6px 0; font-size: 13px; font-weight: 700; color: #34d399; text-align: right;">{booking.child_name} (Age: {getattr(booking, 'child_age', '') or '5–12'})</td>
                      </tr>
                      <tr>
                        <td colspan="2" style="padding: 4px 0; font-size: 11px; color: #fbbf24;">ℹ️ Aadhaar card / valid ID proof required at entry.</td>
                      </tr>
            """

        group_banner_html = ""
        if is_group:
            group_banner_html = f"""
              <div style="background: linear-gradient(135deg, rgba(212, 175, 55, 0.15) 0%, rgba(16, 185, 129, 0.15) 100%); border: 1px solid #d4af37; border-radius: 12px; padding: 16px 20px; margin-bottom: 22px; text-align: center;">
                <div style="font-size: 16px; font-weight: 900; color: #f3e4b2; letter-spacing: 1px; text-transform: uppercase;">
                  🎉 GROUP BOOKING CONFIRMED
                </div>
                <div style="font-size: 13px; font-weight: 800; color: #34d399; margin-top: 4px; letter-spacing: 0.5px;">
                  BEST VALUE • SAVE ₹991 • {offer_title_display.upper()}
                </div>
                <div style="font-size: 12px; color: #cbd5e1; margin-top: 6px;">
                  10 Official Admission Passes • All passes include individual high-speed QR check-in
                </div>
                <div style="font-size: 13px; font-weight: 700; color: #fde047; margin-top: 6px;">
                  ⚡ YOU SAVED ₹{disc_amt:,.0f} ON THIS BOOKING!
                </div>
              </div>
            """

        # Check for cart items breakdown
        cart_items_list = []
        if booking.items:
            for bi in booking.items:
                cart_items_list.append({
                    "title": bi.offer_title,
                    "quantity": bi.quantity,
                    "passes": bi.total_passes,
                    "line_total": bi.line_total
                })
        elif getattr(booking, "cart_items_json", None):
            try:
                raw_c = json.loads(booking.cart_items_json)
                for it in raw_c:
                    cart_items_list.append({
                        "title": it.get("offer_title", ""),
                        "quantity": it.get("quantity", 1),
                        "passes": it.get("total_passes", 1),
                        "line_total": it.get("line_total", 0.0)
                    })
            except Exception:
                pass

        cart_breakdown_html = ""
        if cart_items_list:
            cart_breakdown_html = """
                      <tr style="border-top: 1px solid #23293e;">
                        <td colspan="2" style="padding: 10px 0 4px; font-size: 11px; font-weight: 800; letter-spacing: 1px; color: #d4af37; text-transform: uppercase;">
                          TICKET ORDER BREAKDOWN:
                        </td>
                      </tr>
            """
            for itm in cart_items_list:
                cart_breakdown_html += f"""
                      <tr>
                        <td style="padding: 6px 0; font-size: 13px; color: #cbd5e1;">
                          <strong>{itm['quantity']} × {itm['title']}</strong><br/>
                          <span style="font-size: 11px; color: #94a3b8;">({itm['passes']} Admission Pass{'es' if itm['passes'] > 1 else ''})</span>
                        </td>
                        <td style="padding: 6px 0; font-size: 13px; font-weight: 800; color: #f3e4b2; text-align: right; vertical-align: top;">
                          ₹{itm['line_total']:,.2f}
                        </td>
                      </tr>
                """

        price_rows_html = f"""
                      <tr>
                        <td style="padding: 6px 0; font-size: 13px; color: #94a3b8; width: 45%;">Selected Offer:</td>
                        <td style="padding: 6px 0; font-size: 13px; font-weight: 800; color: #f3e4b2; text-align: right;">{offer_title_display}</td>
                      </tr>
                      <tr>
                        <td style="padding: 6px 0; font-size: 13px; color: #94a3b8;">Admission Passes:</td>
                        <td style="padding: 6px 0; font-size: 13px; font-weight: 700; color: #ffffff; text-align: right;">{booking.ticket_count} Pass{'es' if booking.ticket_count > 1 else ''}</td>
                      </tr>
                      {child_row_html}
                      {cart_breakdown_html}
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

        if (booking.payment_fee and booking.payment_fee > 0) or (booking.gst_amount and booking.gst_amount > 0):
            price_rows_html += f"""
                      <tr>
                        <td style="padding: 6px 0; font-size: 13px; color: #94a3b8;">Payment Processing Fee:</td>
                        <td style="padding: 6px 0; font-size: 13px; color: #cbd5e1; text-align: right;">₹{(booking.payment_fee or 0.0):,.2f}</td>
                      </tr>
                      <tr>
                        <td style="padding: 6px 0; font-size: 13px; color: #94a3b8;">GST on Processing Fee (18%):</td>
                        <td style="padding: 6px 0; font-size: 13px; color: #cbd5e1; text-align: right;">₹{(booking.gst_amount or 0.0):,.2f}</td>
                      </tr>
            """
        else:
            price_rows_html += f"""
                      <tr>
                        <td style="padding: 6px 0; font-size: 13px; color: #94a3b8;">Taxes & Fees:</td>
                        <td style="padding: 6px 0; font-size: 13px; font-weight: 700; color: #34d399; text-align: right;">Included</td>
                      </tr>
            """
        price_rows_html += f"""
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

        # Generate the official NAVRANG 2026 entry pass card matching the uploaded design
        primary_attendee_name = primary_ticket.customer_name if (primary_ticket and primary_ticket.customer_name) else booking.customer_name
        primary_ticket_id = primary_ticket.ticket_id if (primary_ticket and primary_ticket.ticket_id) else f"{booking.booking_id}-01"
        primary_price = getattr(primary_ticket, "ticket_price", None) or (booking.amount / max(1, booking.ticket_count)) if booking.amount else 599

        multi_pass_notice = ""
        if booking.ticket_count > 1:
            multi_pass_notice = f"""
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-top: 14px; margin-bottom: 24px;">
                <tr>
                  <td style="padding: 12px 16px; background: rgba(251, 191, 36, 0.1); border: 1px solid rgba(251, 191, 36, 0.3); border-radius: 8px; font-size: 12px; font-weight: 700; color: #f3e4b2; text-align: center;">
                    🎟️ <strong>Pass 1 of {booking.ticket_count} displayed above.</strong> Individual passes with unique QR codes for all {booking.ticket_count} attendees are included in the attached printable PDF passbook.
                  </td>
                </tr>
              </table>
            """

        official_pass_card_html = f"""
          <!-- Official NAVRANG 2026 Entry Pass Matching Uploaded Design -->
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background: #ffffff; border: 1px solid #cbd5e1; border-radius: 12px; overflow: hidden; margin-bottom: 16px; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
            <!-- 1. Deep Midnight Navy Header #1C1949 -->
            <tr>
              <td style="background-color: #1C1949; padding: 22px 18px 18px; text-align: center;">
                <div style="font-size: 24px; font-weight: 900; color: #EA580C; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 4px;">
                  &#10070; {event_setting.event_name.upper()} &#10070;
                </div>
                <div style="font-size: 11px; font-weight: 800; color: #FBBF24; letter-spacing: 1.5px; text-transform: uppercase; margin-bottom: 4px;">
                  IN COLLABORATION WITH THE HAPPY CIRCLE
                </div>
                <div style="font-size: 13px; font-style: italic; color: #FCD34D; font-family: Georgia, serif; margin-bottom: 12px;">
                  {event_setting.event_tagline or 'Celebrate. Dance. Connect.'}
                </div>
                <div style="font-size: 13px; font-weight: 800; color: #FFFFFF; letter-spacing: 1px; text-transform: uppercase;">
                  OFFICIAL ENTRY PASS — PASS 1 OF {booking.ticket_count}
                </div>
              </td>
            </tr>

            <!-- 2. 4-Column Ticket Metadata Grid -->
            <tr>
              <td style="padding: 0; background: #ffffff;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="border-collapse: collapse; border-bottom: 1px solid #E2E8F0;">
                  <tr>
                    <!-- Row 1: Attendee Name, Booking ID, Ticket Number, Pass Order -->
                    <td width="25%" style="padding: 10px 12px; border-right: 1px solid #E2E8F0; border-bottom: 1px solid #E2E8F0; vertical-align: top;">
                      <div style="font-size: 9px; font-weight: 700; color: #64748B; text-transform: uppercase; letter-spacing: 0.5px;">ATTENDEE NAME</div>
                      <div style="font-size: 13px; font-weight: 800; color: #0F172A; margin-top: 3px;">{primary_attendee_name}</div>
                    </td>
                    <td width="25%" style="padding: 10px 12px; border-right: 1px solid #E2E8F0; border-bottom: 1px solid #E2E8F0; vertical-align: top;">
                      <div style="font-size: 9px; font-weight: 700; color: #64748B; text-transform: uppercase; letter-spacing: 0.5px;">BOOKING ID</div>
                      <div style="font-size: 13px; font-weight: 800; color: #0F172A; font-family: monospace; margin-top: 3px;">{booking.booking_id}</div>
                    </td>
                    <td width="25%" style="padding: 10px 12px; border-right: 1px solid #E2E8F0; border-bottom: 1px solid #E2E8F0; vertical-align: top;">
                      <div style="font-size: 9px; font-weight: 700; color: #64748B; text-transform: uppercase; letter-spacing: 0.5px;">TICKET NUMBER</div>
                      <div style="font-size: 13px; font-weight: 800; color: #0F172A; font-family: monospace; margin-top: 3px;">{primary_ticket_id}</div>
                    </td>
                    <td width="25%" style="padding: 10px 12px; border-bottom: 1px solid #E2E8F0; vertical-align: top;">
                      <div style="font-size: 9px; font-weight: 700; color: #64748B; text-transform: uppercase; letter-spacing: 0.5px;">PASS ORDER</div>
                      <div style="font-size: 13px; font-weight: 800; color: #0F172A; margin-top: 3px;">Pass 1 of {booking.ticket_count}</div>
                    </td>
                  </tr>
                  <tr>
                    <!-- Row 2: Event Date & Time, Venue Location, Payment Status, Ticket Status -->
                    <td width="25%" style="padding: 10px 12px; border-right: 1px solid #E2E8F0; vertical-align: top;">
                      <div style="font-size: 9px; font-weight: 700; color: #64748B; text-transform: uppercase; letter-spacing: 0.5px;">EVENT DATE &amp; TIME</div>
                      <div style="font-size: 11px; font-weight: 700; color: #0F172A; margin-top: 3px;">{event_setting.event_date}</div>
                      <div style="font-size: 10px; color: #64748B;">06:30 PM - 10:00 PM</div>
                    </td>
                    <td width="25%" style="padding: 10px 12px; border-right: 1px solid #E2E8F0; vertical-align: top;">
                      <div style="font-size: 9px; font-weight: 700; color: #64748B; text-transform: uppercase; letter-spacing: 0.5px;">VENUE LOCATION</div>
                      <div style="font-size: 11px; font-weight: 800; color: #0F172A; margin-top: 3px;">{event_setting.venue_name}</div>
                      <div style="font-size: 10px; color: #64748B;">{event_setting.venue_address}, {event_setting.venue_city}</div>
                    </td>
                    <td width="25%" style="padding: 10px 12px; border-right: 1px solid #E2E8F0; vertical-align: top;">
                      <div style="font-size: 9px; font-weight: 700; color: #64748B; text-transform: uppercase; letter-spacing: 0.5px;">PAYMENT STATUS</div>
                      <div style="font-size: 13px; font-weight: 800; color: #0F172A; margin-top: 3px;">&#10003; PAID (&#8377;{int(primary_price)})</div>
                    </td>
                    <td width="25%" style="padding: 10px 12px; vertical-align: top;">
                      <div style="font-size: 9px; font-weight: 700; color: #64748B; text-transform: uppercase; letter-spacing: 0.5px;">TICKET STATUS</div>
                      <div style="font-size: 13px; font-weight: 800; color: #0F172A; margin-top: 3px;">&#9679; VALID</div>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>

            <!-- 3. Important Venue Instructions Box with Integrated QR Code -->
            <tr>
              <td style="padding: 16px 18px; background: #ffffff;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background: #FFFDF5; border: 1px solid #FDE68A; border-radius: 8px; padding: 14px 16px;">
                  <tr>
                    <!-- Left: Instructions -->
                    <td style="vertical-align: middle; padding-right: 14px;">
                      <div style="font-size: 11px; font-weight: 800; color: #B45309; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;">
                        IMPORTANT VENUE INSTRUCTIONS
                      </div>
                      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="font-size: 11px; color: #334155; line-height: 1.55;">
                        <tr><td style="padding: 2px 0;">&bull; Gates open promptly at 06:30 PM. Show this barcode or digital pass at turnstiles.</td></tr>
                        <tr><td style="padding: 2px 0;">&bull; Event Timings: 06:30 PM onwards till 10:00 PM. Gates close at 10:00 PM.</td></tr>
                        <tr><td style="padding: 2px 0;">&bull; Entry will be granted only after successful QR scanning at security.</td></tr>
                        <tr><td style="padding: 2px 0;">&bull; Each QR code is uniquely encrypted and admits exactly one person once.</td></tr>
                        <tr><td style="padding: 2px 0;">&bull; Traditional festive attire is celebrated and recommended.</td></tr>
                        <tr><td style="padding: 2px 0;">&bull; Carry valid Government photo ID matching the attendee name.</td></tr>
                      </table>
                    </td>
                    <!-- Right: High-Contrast QR Code Card -->
                    <td width="150" align="center" style="vertical-align: middle;">
                      <table role="presentation" cellspacing="0" cellpadding="0" border="0" align="center" style="background: #ffffff; padding: 8px; border-radius: 8px; border: 1px solid #CBD5E1; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
                        <tr>
                          <td align="center">
                            <img src="{qr_src}" alt="Entry QR Code" width="130" height="130" style="display: block; width: 130px; height: 130px; border: none;" />
                          </td>
                        </tr>
                        <tr>
                          <td align="center" style="padding-top: 6px; font-size: 10px; font-weight: 800; color: #B45309; text-transform: uppercase; letter-spacing: 0.5px;">
                            Scan at Security
                          </td>
                        </tr>
                      </table>
                    </td>
                  </tr>
                </table>

                <!-- Footer Info Line -->
                <div style="font-size: 10px; color: #64748B; text-align: center; margin-top: 12px;">
                  Pass 1 of {booking.ticket_count} &bull; Booking #{booking.booking_id} &bull; {event_setting.event_name} &times; THE HAPPY CIRCLE Official E-Ticket
                </div>
              </td>
            </tr>
          </table>
          {multi_pass_notice}
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
              <div style="font-size: 11px; font-weight: 800; letter-spacing: 1.5px; color: #fbbf24; text-transform: uppercase; margin-bottom: 6px;">
                IN COLLABORATION WITH THE HAPPY CIRCLE
              </div>
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

              {official_pass_card_html}

              <!-- Booking Receipt & Tax Invoice Details -->
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
                        <td style="color: #ffffff; font-weight: 600;">Gates open at 06:30 PM • Event: {event_setting.event_time}</td>
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
                      <li>Entry starts promptly at 06:30 PM. Gates close at 10:00 PM. Please arrive early to ensure seamless security processing.</li>
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
        offer_title_display = getattr(booking, "offer_title", None) or (
            "Early Bird — Group of 10" if booking.ticket_count == 10
            else "Early Bird — Couple Entry" if booking.ticket_count == 2
            else "Kids (5–12 years)" if getattr(booking, "child_name", None) or booking.ticket_price == 300.0
            else "Early Bird — Stag Entry"
        )
        child_alert_row = ""
        if getattr(booking, "child_name", None):
            child_alert_row = f"""
                <tr>
                  <td style="padding: 11px 18px; font-size: 13px; color: #94a3b8; border-bottom: 1px solid #1a1e30;">Child Attendee:</td>
                  <td style="padding: 11px 18px; font-size: 13px; font-weight: 700; color: #34d399; border-bottom: 1px solid #1a1e30; text-align: right;">{booking.child_name} (Age: {getattr(booking, 'child_age', '') or '5-12'})</td>
                </tr>
            """

        owner_cart_breakdown_html = ""
        cart_items = []
        if booking.items:
            for bi in booking.items:
                cart_items.append({
                    "title": bi.offer_title,
                    "quantity": bi.quantity,
                    "passes": bi.total_passes,
                    "line_total": bi.line_total
                })
        elif getattr(booking, "cart_items_json", None):
            try:
                raw_c = json.loads(booking.cart_items_json)
                for it in raw_c:
                    cart_items.append({
                        "title": it.get("offer_title", ""),
                        "quantity": it.get("quantity", 1),
                        "passes": it.get("total_passes", 1),
                        "line_total": it.get("line_total", 0.0)
                    })
            except Exception:
                pass

        if cart_items:
            owner_cart_breakdown_html = """
                <tr>
                  <td colspan="2" style="padding: 10px 18px 4px; font-size: 11px; font-weight: 800; letter-spacing: 1px; color: #d4af37; text-transform: uppercase; border-bottom: 1px solid #1a1e30; background: #0f121d;">
                    Cart Items Breakdown:
                  </td>
                </tr>
            """
            for itm in cart_items:
                owner_cart_breakdown_html += f"""
                <tr>
                  <td style="padding: 8px 18px; font-size: 13px; color: #cbd5e1; border-bottom: 1px solid #1a1e30;">
                    {itm['quantity']} × {itm['title']} ({itm['passes']} Passes)
                  </td>
                  <td style="padding: 8px 18px; font-size: 13px; font-weight: 800; color: #f3e4b2; border-bottom: 1px solid #1a1e30; text-align: right;">
                    ₹{itm['line_total']:,.2f}
                  </td>
                </tr>
                """

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
                {event_setting.event_name} • {event_setting.venue_name}, {event_setting.venue_city}
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
                  <td style="padding: 11px 18px; font-size: 13px; color: #94a3b8; border-bottom: 1px solid #1a1e30;">Offer Type:</td>
                  <td style="padding: 11px 18px; font-size: 13px; font-weight: 800; color: #f3e4b2; border-bottom: 1px solid #1a1e30; text-align: right;">
                    {offer_title_display}
                  </td>
                </tr>
                {owner_cart_breakdown_html}
                {child_alert_row}
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
                {f'<tr><td style="padding: 11px 18px; font-size: 13px; color: #94a3b8; border-bottom: 1px solid #1a1e30;">Razorpay Payment ID:</td><td style="padding: 11px 18px; font-size: 13px; font-family: monospace; font-weight: 700; color: #60a5fa; border-bottom: 1px solid #1a1e30; text-align: right;">{booking.razorpay_payment_id}</td></tr>' if getattr(booking, "razorpay_payment_id", None) else ''}
                {f'<tr><td style="padding: 11px 18px; font-size: 13px; color: #94a3b8; border-bottom: 1px solid #1a1e30;">Razorpay Order ID:</td><td style="padding: 11px 18px; font-size: 13px; font-family: monospace; font-weight: 700; color: #94a3b8; border-bottom: 1px solid #1a1e30; text-align: right;">{booking.razorpay_order_id}</td></tr>' if getattr(booking, "razorpay_order_id", None) else ''}
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
                    <strong>Gates Open: 06:30 PM</strong> | Event: <strong>{event_setting.event_time}</strong><br/>
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
    def send_confirmation_email(cls, booking_id: str, db: Session, send_to_admin: bool = True) -> bool:
        """Sends confirmation email with attached PDF passes and inline QR code to the booker and optionally admin."""
        booking = db.query(Booking).filter(Booking.booking_id == booking_id).first()
        if not booking:
            app_logger.error(f"[EMAIL] Cannot send confirmation: Booking {booking_id} not found.")
            return False

        # Step 1: Retrieve customer email strictly from the booking record (backend source of truth)
        raw_email = getattr(booking, "email", None)
        customer_email = (raw_email or "").strip().lower()

        # Step 2: Validate customer email presence and syntax
        allow_placeholders = getattr(settings, "ALLOW_PLACEHOLDER_EMAILS", False)
        customer_valid = True
        customer_err = ""
        if not customer_email or not validate_email_format(customer_email):
            customer_valid = False
            customer_err = f"Customer email is missing or has an invalid format: '{raw_email or ''}'."
        elif is_placeholder_email(customer_email) and not allow_placeholders:
            customer_valid = False
            customer_err = (
                f"Customer email address is a placeholder ('{customer_email}'). "
                f"Email delivery skipped to prevent provider bounce (example.com does not accept email)."
            )

        event_setting = db.query(EventSetting).first() or EventSetting()
        config = cls.get_email_config(db)
        provider = (config.get("email_provider") or "resend").lower().strip()
        raw_admin = (config.get("admin_email") or "").strip().lower()
        admin_recipients: List[str] = []
        if send_to_admin and raw_admin:
            for em in raw_admin.replace(";", ",").split(","):
                c = em.strip()
                if c and validate_email_format(c) and c not in admin_recipients:
                    admin_recipients.append(c)
        admin_valid = bool(admin_recipients)
        admin_email = admin_recipients[0] if admin_recipients else ""

        # Step 3: Verify provider credentials before attempting dispatch
        has_credentials = False
        if provider == "resend":
            has_credentials = bool(config.get("resend_api_key"))
        elif provider == "smtp":
            has_credentials = bool(config.get("smtp_username") and config.get("smtp_password"))
        elif provider == "console":
            has_credentials = True

        if not has_credentials:
            err_msg = "Email provider credentials are not configured"
            app_logger.warning(
                f"[EMAIL] Confirmation email delivery skipped for booking {booking.booking_id}: {err_msg} (provider={provider})"
            )
            booking.email_status = "NOT_CONFIGURED"
            booking.email_error = err_msg
            if send_to_admin:
                booking.admin_email_status = "NOT_CONFIGURED"
                booking.admin_email_error = err_msg
            db.commit()
            return False

        if not customer_valid and not admin_valid:
            app_logger.error(f"[EMAIL] Confirmation email delivery skipped for booking {booking.booking_id}: {customer_err}")
            booking.email_status = "FAILED"
            booking.email_error = customer_err[:500]
            if send_to_admin:
                booking.admin_email_status = "FAILED"
                booking.admin_email_error = "Admin email invalid or not configured"
            db.commit()
            return False

        app_logger.info(
            f"[EMAIL] Attempt: booking_id={booking.booking_id} customer={customer_email} admin={admin_email if send_to_admin else 'N/A'} provider={provider}"
        )

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

            html_content = cls.render_confirmation_html(booking, event_setting, qr_base64, provider=provider)
            is_group = bool((getattr(booking, "group_discount", 0.0) or 0.0) > 0 or booking.ticket_count == 10)
            if is_group:
                subject = f"🎉 GROUP BOOKING CONFIRMED (GROUP OF 10 — SAVE ₹991) — {event_setting.event_name} (#{booking.booking_id})"
            else:
                subject = f"🎟️ {event_setting.event_name} — Official Admission Pass & Invoice (#{booking.booking_id})"

            # Generate PDF bundle
            pdf_bytes = ticket_service.generate_booking_bundle_pdf(booking, event_setting)
            event_slug = re.sub(r'[^a-zA-Z0-9]', '', event_setting.event_name) or "Tickets"
            pdf_filename = f"{event_slug}_{booking.booking_id}_Tickets.pdf"
            attachments = [{"filename": pdf_filename, "content_bytes": pdf_bytes}]

            # Case 1: Customer email is invalid but admin is valid (deliver to admin only)
            if not customer_valid and admin_valid:
                booking.email_status = "FAILED"
                booking.email_error = customer_err[:500]
                app_logger.error(f"[EMAIL] Customer email failed: {customer_email} - {customer_err}")
                try:
                    cls._dispatch_message(
                        to_emails=[admin_email],
                        subject=subject,
                        html_content=html_content,
                        config=config,
                        attachments=attachments,
                        is_owner=False,
                        qr_bytes=qr_bytes,
                    )
                    booking.admin_email_status = "SENT"
                    booking.admin_email_sent_at = datetime.utcnow()
                    booking.admin_email_error = None
                    app_logger.info(f"[EMAIL] Admin email sent: {admin_email}")
                except Exception as a_err:
                    booking.admin_email_status = "FAILED"
                    booking.admin_email_error = str(a_err)[:500]
                    app_logger.error(f"[EMAIL] Admin email failed: {admin_email} - {a_err}")
                db.commit()
                return False

            # Case 2: Booker email equals admin email (deduplicate to avoid duplicate delivery)
            if send_to_admin and customer_email == admin_email:
                try:
                    cls._dispatch_message(
                        to_emails=[customer_email],
                        subject=subject,
                        html_content=html_content,
                        config=config,
                        attachments=attachments,
                        is_owner=False,
                        qr_bytes=qr_bytes,
                    )
                    now = datetime.utcnow()
                    booking.email_status = "SENT"
                    booking.email_sent_at = now
                    booking.email_error = None
                    booking.admin_email_status = "SENT"
                    booking.admin_email_sent_at = now
                    booking.admin_email_error = None
                    db.commit()
                    app_logger.info(f"[EMAIL] Customer email sent: {customer_email}")
                    app_logger.info(f"[EMAIL] Admin email sent: {customer_email} (deduplicated: booker is admin)")
                    return True
                except Exception as e:
                    err_str = str(e)
                    booking.email_status = "FAILED"
                    booking.email_error = err_str[:500]
                    booking.admin_email_status = "FAILED"
                    booking.admin_email_error = err_str[:500]
                    db.commit()
                    app_logger.error(f"[EMAIL] Customer email failed: {customer_email} - {err_str[:200]}")
                    app_logger.error(f"[EMAIL] Admin email failed: {admin_email} - {err_str[:200]}")
                    return False

            # Case 3: Manual resend to booker only (send_to_admin=False)
            if not send_to_admin:
                try:
                    cls._dispatch_message(
                        to_emails=[customer_email],
                        subject=subject,
                        html_content=html_content,
                        config=config,
                        attachments=attachments,
                        is_owner=False,
                        qr_bytes=qr_bytes,
                    )
                    booking.email_status = "SENT"
                    booking.email_sent_at = datetime.utcnow()
                    booking.email_error = None
                    db.commit()
                    app_logger.info(f"[EMAIL] Customer email sent: {customer_email}")
                    return True
                except Exception as e:
                    err_str = str(e)
                    booking.email_status = "FAILED"
                    booking.email_error = err_str[:500]
                    db.commit()
                    app_logger.error(f"[EMAIL] Customer email failed: {customer_email} - {err_str[:200]}")
                    return False

            # Case 4: Dual recipient automatic confirmation [customer_email, admin_email]
            recipient_list = [customer_email] + [a for a in admin_recipients if a != customer_email]
            try:
                cls._dispatch_message(
                    to_emails=recipient_list,
                    subject=subject,
                    html_content=html_content,
                    config=config,
                    attachments=attachments,
                    is_owner=False,
                    qr_bytes=qr_bytes,
                )
                now = datetime.utcnow()
                booking.email_status = "SENT"
                booking.email_sent_at = now
                booking.email_error = None
                booking.admin_email_status = "SENT"
                booking.admin_email_sent_at = now
                booking.admin_email_error = None
                db.commit()
                app_logger.info(f"[EMAIL] Customer email sent: {customer_email}")
                app_logger.info(f"[EMAIL] Admin email sent: {admin_email}")
                return True
            except Exception as combined_err:
                app_logger.warning(
                    f"[EMAIL] Combined dispatch failed ({combined_err}); attempting separate dispatches for customer and admin..."
                )
                cust_ok = False
                try:
                    cls._dispatch_message(
                        to_emails=[customer_email],
                        subject=subject,
                        html_content=html_content,
                        config=config,
                        attachments=attachments,
                        is_owner=False,
                        qr_bytes=qr_bytes,
                    )
                    booking.email_status = "SENT"
                    booking.email_sent_at = datetime.utcnow()
                    booking.email_error = None
                    cust_ok = True
                    app_logger.info(f"[EMAIL] Customer email sent: {customer_email}")
                except Exception as c_err:
                    booking.email_status = "FAILED"
                    booking.email_error = str(c_err)[:500]
                    app_logger.error(f"[EMAIL] Customer email failed: {customer_email} - {c_err}")

                admin_ok = False
                try:
                    cls._dispatch_message(
                        to_emails=[admin_email],
                        subject=subject,
                        html_content=html_content,
                        config=config,
                        attachments=attachments,
                        is_owner=False,
                        qr_bytes=qr_bytes,
                    )
                    booking.admin_email_status = "SENT"
                    booking.admin_email_sent_at = datetime.utcnow()
                    booking.admin_email_error = None
                    admin_ok = True
                    app_logger.info(f"[EMAIL] Admin email sent: {admin_email}")
                except Exception as a_err:
                    booking.admin_email_status = "FAILED"
                    booking.admin_email_error = str(a_err)[:500]
                    app_logger.error(f"[EMAIL] Admin email failed: {admin_email} - {a_err}")

                db.commit()
                return cust_ok

        except Exception as e:
            err_msg = str(e)
            booking.email_status = "FAILED"
            booking.email_error = err_msg[:500]
            if send_to_admin:
                booking.admin_email_status = "FAILED"
                booking.admin_email_error = err_msg[:500]
            db.commit()
            app_logger.error(
                f"[EMAIL] Failure: booking_id={booking.booking_id} email_status=FAILED error={err_msg[:200]}"
            )
            return False


    @classmethod
    def send_owner_notification(cls, booking_id: str, db: Session) -> bool:
        """Sends immediate booking notification message to the event owner/organizer with realtime inventory."""
        booking = db.query(Booking).filter(Booking.booking_id == booking_id).first()
        if not booking:
            app_logger.error(f"[OWNER EMAIL] Cannot send owner alert: Booking {booking_id} not found.")
            return False

        event_setting = db.query(EventSetting).first() or EventSetting()
        config = cls.get_email_config(db)

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
            f"Target Owner Email: {config.get('owner_email') or '(not set)'} | Owner Phone: {config.get('owner_phone') or '(not set)'}\n"
            f"Alert: {sms_text}\n"
            f"================================================================================"
        )

        # 2. Check if owner notification is enabled
        if not config.get("owner_enabled", True):
            app_logger.info("[OWNER EMAIL] Owner notifications are disabled in settings.")
            return True

        # 3. Optional Webhook dispatch (Discord / Slack / Telegram)
        if config.get("owner_webhook"):
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
                    headers={"Content-Type": "application/json", "User-Agent": "NAVRANG-Webhook/1.0"}
                )
                with urllib.request.urlopen(req, timeout=5) as response:
                    app_logger.info(f"Owner webhook alert dispatched successfully (HTTP {response.status}).")
            except Exception as hook_err:
                app_logger.warning(f"Owner webhook dispatch error: {hook_err}")

        # 4. Check recipient owner email(s)
        recipients = []
        if config.get("owner_email"):
            for em in config["owner_email"].replace(";", ",").split(","):
                c = em.strip()
                if c and "@" in c and c.lower() not in [r.lower() for r in recipients]:
                    recipients.append(c)

        if not recipients:
            app_logger.warning("[OWNER EMAIL] Owner notification skipped: OWNER_NOTIFICATION_EMAIL is not configured.")
            booking.owner_notified = False
            booking.owner_notify_error = "OWNER_NOTIFICATION_EMAIL is not configured."
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

            subject = f"⚡ {event_setting.event_name.upper()}: {booking.ticket_count} Pass{'es' if booking.ticket_count > 1 else ''} Booked by {booking.customer_name} (₹{int(booking.amount):,}) [Sold: {total_sold_tickets}/{total_capacity}]"

            cls._dispatch_message(
                to_emails=recipients,
                subject=subject,
                html_content=owner_html,
                config=config,
                is_owner=True,
            )

            booking.owner_notified = True
            booking.owner_notified_at = datetime.utcnow()
            booking.owner_notify_error = None
            db.commit()
            return True

        except Exception as e:
            err_msg = str(e)
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
        config = cls.get_email_config(db)

        recipients = []
        if config.get("owner_email"):
            for em in config["owner_email"].replace(";", ",").split(","):
                c = em.strip()
                if c and "@" in c and c.lower() not in [r.lower() for r in recipients]:
                    recipients.append(c)

        if not recipients:
            app_logger.info(f"[PAYMENT VERIFICATION ALERT PENDING] OWNER_NOTIFICATION_EMAIL not configured for booking {booking_id}")
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
        <tr><td style="color: #94a3b8; padding: 6px 0;">Venue & Timings:</td><td style="color: #cbd5e1; text-align: right;">{event_setting.venue_name}, {event_setting.venue_city} • {event_setting.event_time}</td></tr>
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

            subject = f"⚠️ [ACTION REQUIRED] Payment Verification for {booking.customer_name} (₹{int(booking.amount):,}) — UTR: {booking.utr_number or 'N/A'}"
            cls._dispatch_message(
                to_emails=recipients,
                subject=subject,
                html_content=alert_html,
                config=config,
                is_owner=True,
            )
            return True
        except Exception as e:
            app_logger.error(f"Failed to send payment verification alert: {e}")
            return False

    @classmethod
    def test_email_connection(cls, to_email: Optional[str], db: Session) -> Dict[str, Any]:
        """Tests email delivery via currently selected email provider (Resend API, SMTP, or Console)."""
        config = cls.get_email_config(db)
        target_email = (to_email or "").strip() or config.get("owner_email") or "test@example.com"
        event_setting = db.query(EventSetting).first() or EventSetting()
        provider = config.get("email_provider", "resend").lower()
        sender = f"{config['smtp_from_name']} <{config['smtp_from_email']}>"

        # -------------------------------------------------------------
        # RESEND TEST
        # -------------------------------------------------------------
        if provider == "resend":
            if not config.get("resend_api_key"):
                return {
                    "success": False,
                    "provider": "resend",
                    "recipient": target_email,
                    "sender": config["smtp_from_email"],
                    "error": "MISSING_RESEND_KEY",
                    "message": (
                        "Resend API Key is missing!\n\n"
                        "To send emails via Resend:\n"
                        "1. Go to https://resend.com and sign up.\n"
                        "2. Create an API Key (starts with re_).\n"
                        "3. Set RESEND_API_KEY in Railway or Admin Settings.\n"
                    ),
                    "diagnostics": {
                        "provider": "resend",
                        "resend_key_present": False,
                    }
                }

            try:
                test_html = f"""<!DOCTYPE html>
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #06070c; color: #e2e8f0; padding: 32px 12px; margin: 0;">
  <div style="max-width: 520px; margin: 0 auto; background-color: #0d0f18; border: 1px solid #1f2335; border-top: 4px solid #d4af37; border-radius: 16px; padding: 28px; text-align: center; box-shadow: 0 15px 35px rgba(0,0,0,0.6);">
    <div style="display: inline-block; padding: 5px 14px; background: rgba(212, 175, 55, 0.1); border: 1px solid rgba(212, 175, 55, 0.3); border-radius: 9999px; font-size: 11px; font-weight: 800; letter-spacing: 1.5px; text-transform: uppercase; color: #f3e4b2; margin-bottom: 12px;">
      ✦ SYSTEM VERIFICATION ✦
    </div>
    <h2 style="color: #ffffff; margin: 0 0 8px; font-size: 22px; font-weight: 900; text-transform: uppercase;">
      Email Delivery <span style="color: #34d399;">Active</span>
    </h2>
    <p style="font-size: 14px; color: #94a3b8; line-height: 1.6; margin: 0 0 20px;">
      This test message confirms that your email engine is operational via <strong style="color: #34d399;">Resend API (HTTPS Port 443)</strong> for <strong style="color: #f3e4b2;">{event_setting.event_name}</strong>.
    </p>
    <div style="background: #111422; border: 1px solid #23293e; padding: 16px; border-radius: 12px; font-size: 13px; text-align: left; margin: 20px 0; color: #94a3b8; line-height: 1.8;">
      <div><strong style="color: #cbd5e1;">Transport:</strong> Resend REST API (HTTPS / Port 443)</div>
      <div><strong style="color: #cbd5e1;">Sender:</strong> {sender}</div>
      <div><strong style="color: #cbd5e1;">Recipient:</strong> {target_email}</div>
      <div><strong style="color: #cbd5e1;">Timestamp:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</div>
    </div>
    <p style="font-size: 12px; color: #34d399; font-weight: bold; margin: 0;">
      ✓ Automated customer QR ticket emails & owner alerts are ready!
    </p>
  </div>
</body>
</html>"""
                subject = f"✨ {event_setting.event_name} — Email Delivery Verified (Resend API)"
                res = cls._dispatch_resend_email([target_email], subject, test_html, config)
                return {
                    "success": True,
                    "provider": "resend",
                    "recipient": target_email,
                    "sender": config["smtp_from_email"],
                    "error": None,
                    "message": f"Test email successfully dispatched via Resend API to {target_email}! Please check your inbox (and spam folder).",
                    "diagnostics": {
                        "provider": "resend",
                        "port": 443,
                        "recipient": target_email,
                        "sender": config["smtp_from_email"],
                        "details": res.get("data", {})
                    }
                }
            except Exception as resend_err:
                err_msg = str(resend_err)
                return {
                    "success": False,
                    "provider": "resend",
                    "recipient": target_email,
                    "sender": config["smtp_from_email"],
                    "error": err_msg,
                    "message": f"Resend API dispatch failed: {err_msg}",
                    "diagnostics": {
                        "provider": "resend",
                        "recipient": target_email,
                        "sender": config["smtp_from_email"],
                        "success": False
                    }
                }

        # -------------------------------------------------------------
        # SMTP TEST
        # -------------------------------------------------------------
        elif provider == "smtp":
            if not config.get("smtp_username") or not config.get("smtp_password"):
                return {
                    "success": False,
                    "provider": "smtp",
                    "recipient": target_email,
                    "sender": config["smtp_from_email"],
                    "error": "MISSING_CREDENTIALS",
                    "message": (
                        "SMTP credentials are not configured! Please configure Resend API Key (recommended for Railway) "
                        "or enter your SMTP Username & App Password in Admin Settings."
                    ),
                    "diagnostics": {
                        "host": config["smtp_host"],
                        "port": config["smtp_port"],
                        "username_present": bool(config.get("smtp_username")),
                        "password_present": bool(config.get("smtp_password"))
                    }
                }

            try:
                msg = MIMEMultipart()
                msg["Subject"] = f"✨ {event_setting.event_name} — SMTP Mail Delivery Verified"
                msg["From"] = f"{config['smtp_from_name']} <{config['smtp_from_email']}>"
                msg["To"] = target_email

                test_html = f"""<!DOCTYPE html>
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #06070c; color: #e2e8f0; padding: 32px 12px; margin: 0;">
  <div style="max-width: 520px; margin: 0 auto; background-color: #0d0f18; border: 1px solid #1f2335; border-top: 4px solid #d4af37; border-radius: 16px; padding: 28px; text-align: center; box-shadow: 0 15px 35px rgba(0,0,0,0.6);">
    <h2 style="color: #ffffff; margin: 0 0 8px; font-size: 22px; font-weight: 900;">SMTP Mail Delivery Active</h2>
    <p style="font-size: 14px; color: #94a3b8;">This test confirms that your SMTP mail server is operational for {event_setting.event_name}.</p>
    <div style="background: #111422; border: 1px solid #23293e; padding: 16px; border-radius: 12px; font-size: 13px; text-align: left; margin: 20px 0;">
      <div><strong>Host:</strong> {config['smtp_host']}:{config['smtp_port']}</div>
      <div><strong>Sender:</strong> {config['smtp_from_name']} &lt;{config['smtp_from_email']}&gt;</div>
      <div><strong>Recipient:</strong> {target_email}</div>
    </div>
  </div>
</body>
</html>"""
                msg.attach(MIMEText(test_html, "html"))
                cls._dispatch_smtp_message(msg, config)

                return {
                    "success": True,
                    "provider": "smtp",
                    "recipient": target_email,
                    "sender": config["smtp_from_email"],
                    "error": None,
                    "message": f"Test email successfully dispatched to {target_email}! Please check your inbox.",
                    "diagnostics": {
                        "host": config["smtp_host"],
                        "port": config["smtp_port"],
                        "recipient": target_email,
                        "sender": config["smtp_from_email"]
                    }
                }
            except Exception as e:
                err_str = str(e)
                return {
                    "success": False,
                    "provider": "smtp",
                    "recipient": target_email,
                    "sender": config["smtp_from_email"],
                    "error": err_str,
                    "message": f"Failed to connect or send email: {err_str}",
                    "diagnostics": {
                        "host": config["smtp_host"],
                        "port": config["smtp_port"],
                        "recipient": target_email,
                        "sender": config["smtp_from_email"]
                    }
                }

        # -------------------------------------------------------------
        # CONSOLE TEST
        # -------------------------------------------------------------
        elif provider == "console":
            app_logger.info(f"[EMAIL] [TEST] Console mode test email to {target_email} from {sender}")
            return {
                "success": True,
                "provider": "console",
                "recipient": target_email,
                "sender": config["smtp_from_email"],
                "error": None,
                "message": f"Test email logged to console (EMAIL_PROVIDER=console) for recipient {target_email}.",
                "diagnostics": {
                    "provider": "console",
                    "recipient": target_email,
                    "sender": config["smtp_from_email"]
                }
            }

        return {
            "success": False,
            "provider": provider,
            "recipient": target_email,
            "sender": config["smtp_from_email"],
            "error": f"Unknown provider: {provider}",
            "message": f"Unknown email provider: {provider}"
        }

    @classmethod
    def test_connection(cls, to_email: Optional[str], db: Session) -> Dict[str, Any]:
        """Backward compatible alias for test_email_connection."""
        return cls.test_email_connection(to_email, db)

    @classmethod
    def test_smtp_connection(cls, to_email: Optional[str], db: Session) -> Dict[str, Any]:
        """Backward compatible alias for test_email_connection."""
        return cls.test_email_connection(to_email, db)

    @staticmethod
    def _dispatch_smtp_message(msg: MIMEMultipart, config: Dict[str, Any]):
        """Internal helper to dispatch email over SMTP with TLS or SSL support and detailed cloud error diagnostics."""
        host = config["smtp_host"]
        port = int(config["smtp_port"])
        username = config["smtp_username"]
        password = config["smtp_password"]
        use_tls = config.get("smtp_use_tls", True)

        try:
            if port == 465:
                # SSL Connection
                with smtplib.SMTP_SSL(host, port, timeout=12) as server:
                    if username and password:
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
        except (OSError, smtplib.SMTPConnectError) as conn_err:
            err_str = str(conn_err)
            if "101" in err_str or "unreachable" in err_str.lower() or "timed out" in err_str.lower() or "110" in err_str:
                raise RuntimeError(
                    f"Outbound SMTP network connection failed ({err_str}). "
                    f"Cloud platforms like Railway block outbound SMTP ports (587 & 465) at the firewall level. "
                    f"To deliver emails on Railway, switch Email Provider to 'Resend' in Admin Settings and enter a free Resend API key (https://resend.com) which operates over HTTPS port 443 without any firewall restrictions."
                ) from conn_err
            raise

email_service = EmailService()
