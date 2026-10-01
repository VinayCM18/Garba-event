import pytest
import os
import sys
import json
import base64
from datetime import datetime
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import Base
from app.config import settings
from app.models.booking import Booking
from app.models.ticket import Ticket
from app.models.event_setting import EventSetting
from app.services.email_service import EmailService
from app.services.booking_service import booking_service

TEST_DB_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(autouse=True)
def init_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSession()
    # Create or update event settings
    setting = EventSetting(
        event_name="NAVRANG 2026",
        event_tagline="The Premier Cultural Gala & Dance Experience",
        event_date="October 17, 2026",
        event_time="07:00 PM - 10:00 PM",
        venue_name="Green Acres",
        venue_address="Green Acres, Mysuru",
        venue_city="Mysuru",
        ticket_price=599.0,
        total_capacity=1500,
        max_per_booking=10,
        booking_open=True,
        email_provider="resend",
        resend_api_key="re_mock_test_key_12345",
        smtp_from_email="tickets@garbanight.in",
        smtp_from_name="NAVRANG 2026",
        owner_notification_email="testadmin@garbanight.in",
        owner_notification_phone="+91 98765 43210",
        owner_notification_enabled=True,
    )
    db.add(setting)
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)


def create_sample_booking(db, booking_id="GN-2026-TEST01", ticket_count=2, payment_status="PAID"):
    booking = Booking(
        booking_id=booking_id,
        customer_name="Test Booker",
        email="testbooker@garbanight.in",
        phone="+91 99999 88888",
        ticket_count=ticket_count,
        ticket_price=599.0,
        regular_amount=round(599.0 * ticket_count, 2),
        group_discount=0.0,
        ticket_subtotal=round(599.0 * ticket_count, 2),
        amount=round(599.0 * ticket_count, 2),
        currency="INR",
        payment_method="RAZORPAY",
        razorpay_order_id="order_test_123",
        razorpay_payment_id="pay_test_456",
        payment_status=payment_status,
        booking_status="CONFIRMED" if payment_status == "PAID" else "PAYMENT_PENDING",
        email_status="PENDING",
        owner_notified=False,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)

    for i in range(ticket_count):
        ticket = Ticket(
            booking_id=booking.id,
            ticket_id=f"TKT-{booking_id}-{i+1:02d}",
            customer_name="Test Booker",
            event_name="NAVRANG 2026",
            qr_token_raw=f"RAW_QR_TOKEN_{booking_id}_{i+1}",
            qr_token_hash=f"HASH_{booking_id}_{i+1}",
            ticket_status="VALID",
        )
        db.add(ticket)
    db.commit()
    db.refresh(booking)
    return booking


# ---------------------------------------------------------------------------
# 1. Resend Provider Configuration
# ---------------------------------------------------------------------------
def test_resend_provider_configuration():
    db = TestingSession()
    with patch.dict(os.environ, {"OWNER_NOTIFICATION_EMAIL": ""}, clear=False), \
         patch.object(settings, "OWNER_NOTIFICATION_EMAIL", ""):
        config = EmailService.get_email_config(db)
    db.close()

    assert config["email_provider"] == "resend"
    assert config["resend_api_key"] == "re_mock_test_key_12345"
    assert config["smtp_from_name"] == "NAVRANG 2026"
    assert config["smtp_from_email"] == "tickets@garbanight.in"
    assert config["owner_email"] == "testadmin@garbanight.in"


# ---------------------------------------------------------------------------
# 2. Customer Confirmation Email Success via Resend
# ---------------------------------------------------------------------------
def test_customer_confirmation_email_resend_success():
    db = TestingSession()
    booking = create_sample_booking(db, "GN-2026-CONF01")

    # Mock urllib.request.urlopen returning HTTP 200 with Resend email ID
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({"id": "resend_msg_abc123"}).encode("utf-8")
    mock_response.__enter__.return_value = mock_response

    with patch("urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
        success = EmailService.send_confirmation_email(booking.booking_id, db)
        assert success is True

        # Verify urllib call arguments
        mock_urlopen.assert_called_once()
        req = mock_urlopen.call_args[0][0]
        assert req.full_url == "https://api.resend.com/emails"
        assert req.get_header("Authorization") == "Bearer re_mock_test_key_12345"

        payload = json.loads(req.data.decode("utf-8"))
        assert "testbooker@garbanight.in" in payload["to"]
        assert "samaymadhyastha2005@gmail.com" in payload["to"]
        assert len(payload["to"]) == 2
        assert "NAVRANG 2026" in payload["from"]
        assert "GN-2026-CONF01" in payload["subject"]
        assert len(payload["attachments"]) == 1
        assert payload["attachments"][0]["filename"].endswith(".pdf")

    # Verify DB state
    db.refresh(booking)
    assert booking.email_status == "SENT"
    assert booking.admin_email_status == "SENT"
    assert booking.email_sent_at is not None
    assert booking.admin_email_sent_at is not None
    assert booking.email_error is None
    assert booking.admin_email_error is None
    db.close()


# ---------------------------------------------------------------------------
# 3. Owner Notification Email Success via Resend
# ---------------------------------------------------------------------------
def test_owner_notification_email_resend_success():
    db = TestingSession()
    booking = create_sample_booking(db, "GN-2026-OWNER01")

    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({"id": "resend_owner_msg_xyz789"}).encode("utf-8")
    mock_response.__enter__.return_value = mock_response

    with patch.dict(os.environ, {"OWNER_NOTIFICATION_EMAIL": ""}, clear=False), \
         patch.object(settings, "OWNER_NOTIFICATION_EMAIL", ""), \
         patch("urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
        success = EmailService.send_owner_notification(booking.booking_id, db)
        assert success is True

        mock_urlopen.assert_called_once()
        req = mock_urlopen.call_args[0][0]
        payload = json.loads(req.data.decode("utf-8"))
        assert payload["to"] == ["testadmin@garbanight.in"]
        assert "GN-2026-OWNER01" in payload["html"]
        assert "Test Booker" in payload["html"]

    db.refresh(booking)
    assert booking.owner_notified is True
    assert booking.owner_notified_at is not None
    assert booking.owner_notify_error is None
    db.close()


# ---------------------------------------------------------------------------
# 4. Email Provider Failure Handling
# ---------------------------------------------------------------------------
def test_email_provider_failure_handling():
    db = TestingSession()
    booking = create_sample_booking(db, "GN-2026-FAIL01")

    # Mock an HTTP error from Resend (e.g. rate limit 429)
    import urllib.error
    mock_err_body = json.dumps({"statusCode": 429, "message": "Too many requests"}).encode("utf-8")
    http_error = urllib.error.HTTPError(
        url="https://api.resend.com/emails",
        code=429,
        msg="Too many requests",
        hdrs={},
        fp=MagicMock(read=lambda: mock_err_body)
    )

    with patch("urllib.request.urlopen", side_effect=http_error):
        success = EmailService.send_confirmation_email(booking.booking_id, db)
        assert success is False

    db.refresh(booking)
    assert booking.email_status == "FAILED"
    assert "Too many requests" in (booking.email_error or "")
    db.close()


# ---------------------------------------------------------------------------
# 5. Missing RESEND_API_KEY
# ---------------------------------------------------------------------------
def test_missing_resend_api_key():
    db = TestingSession()
    setting = db.query(EventSetting).first()
    setting.resend_api_key = ""
    db.commit()

    booking = create_sample_booking(db, "GN-2026-NOKEY01")

    with patch.object(settings, "RESEND_API_KEY", ""):
        success = EmailService.send_confirmation_email(booking.booking_id, db)
        assert success is False

    db.refresh(booking)
    assert booking.email_status in ("FAILED", "NOT_CONFIGURED")
    assert "not configured" in (booking.email_error or "").lower()
    db.close()


# ---------------------------------------------------------------------------
# 6. Payment Remains Successful Even When Email Fails
# ---------------------------------------------------------------------------
def test_payment_remains_successful_when_email_fails():
    """Confirms booking and verifies that if email fails, payment status is unaffected."""
    db = TestingSession()
    booking = create_sample_booking(db, "GN-2026-PAYSAFE", payment_status="PAID")

    with patch.object(EmailService, "_dispatch_message", side_effect=RuntimeError("Simulated network timeout")):
        # Dispatch customer email
        cust_success = EmailService.send_confirmation_email(booking.booking_id, db)
        assert cust_success is False

        # Dispatch owner notification
        owner_success = EmailService.send_owner_notification(booking.booking_id, db)
        assert owner_success is False

    db.refresh(booking)
    # Payment and booking MUST remain CONFIRMED / PAID!
    assert booking.payment_status == "PAID"
    assert booking.booking_status == "CONFIRMED"
    assert booking.email_status == "FAILED"
    assert "Simulated network timeout" in (booking.email_error or "")
    assert booking.owner_notified is False
    assert "Simulated network timeout" in (booking.owner_notify_error or "")
    assert len(booking.tickets) == 2
    db.close()


# ---------------------------------------------------------------------------
# 7. SMTP Fallback Works
# ---------------------------------------------------------------------------
def test_smtp_fallback_dispatch():
    db = TestingSession()
    setting = db.query(EventSetting).first()
    setting.email_provider = "smtp"
    setting.smtp_username = "smtp_user@garbanight.in"
    setting.smtp_password = "smtp_password123"
    db.commit()

    booking = create_sample_booking(db, "GN-2026-SMTP01")

    with patch.object(EmailService, "_dispatch_smtp_message") as mock_smtp:
        success = EmailService.send_confirmation_email(booking.booking_id, db)
        assert success is True
        # Called for both booker and admin recipient
        assert mock_smtp.call_count == 2

    db.refresh(booking)
    assert booking.email_status == "SENT"
    assert booking.admin_email_status == "SENT"
    db.close()


# ---------------------------------------------------------------------------
# 8. Console Provider Works
# ---------------------------------------------------------------------------
def test_console_provider_dispatch():
    db = TestingSession()
    setting = db.query(EventSetting).first()
    setting.email_provider = "console"
    db.commit()

    booking = create_sample_booking(db, "GN-2026-CONSOLE01")

    success = EmailService.send_confirmation_email(booking.booking_id, db)
    assert success is True

    db.refresh(booking)
    assert booking.email_status == "SENT"
    assert booking.email_error is None

    owner_success = EmailService.send_owner_notification(booking.booking_id, db)
    assert owner_success is True
    db.refresh(booking)
    assert booking.owner_notified is True
    db.close()


# ---------------------------------------------------------------------------
# 9. Provider-Neutral Test Connection Endpoint
# ---------------------------------------------------------------------------
def test_test_email_connection_resend_and_console():
    db = TestingSession()
    setting = db.query(EventSetting).first()
    setting.email_provider = "resend"
    setting.resend_api_key = "re_test_key"
    db.commit()

    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({"id": "resend_test_123"}).encode("utf-8")
    mock_response.__enter__.return_value = mock_response

    with patch("urllib.request.urlopen", return_value=mock_response):
        res = EmailService.test_email_connection("tester@garbanight.in", db)
        assert res["success"] is True
        assert res["provider"] == "resend"
        assert res["recipient"] == "tester@garbanight.in"
        assert "re_test_key" not in str(res)  # NEVER leaks key

    # Test console mode
    setting.email_provider = "console"
    db.commit()
    res_console = EmailService.test_email_connection("tester@garbanight.in", db)
    assert res_console["success"] is True
    assert res_console["provider"] == "console"
    db.close()


# ---------------------------------------------------------------------------
# 10. Placeholder Email Protection (booker@example.com MUST be blocked)
# ---------------------------------------------------------------------------
def test_placeholder_email_is_blocked():
    """Verifies that booker@example.com is never used as a customer email recipient."""
    db = TestingSession()
    # Create a booking with a placeholder email
    booking = Booking(
        booking_id="GN-2026-PLACEHOLDER",
        customer_name="Placeholder Booker",
        email="booker@example.com",
        phone="+91 99999 88888",
        ticket_count=1,
        ticket_price=599.0,
        regular_amount=599.0,
        group_discount=0.0,
        ticket_subtotal=599.0,
        amount=599.0,
        currency="INR",
        payment_method="RAZORPAY",
        payment_status="PAID",
        booking_status="CONFIRMED",
        email_status="PENDING",
        owner_notified=False,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)

    for i in range(1):
        ticket = Ticket(
            booking_id=booking.id,
            ticket_id=f"TKT-PLACEHOLDER-{i+1:02d}",
            customer_name="Placeholder Booker",
            event_name="NAVRANG 2026",
            qr_token_raw=f"RAW_QR_TOKEN_PLACEHOLDER_{i+1}",
            qr_token_hash=f"HASH_PLACEHOLDER_{i+1}",
            ticket_status="VALID",
        )
        db.add(ticket)
    db.commit()
    db.refresh(booking)

    success = EmailService.send_confirmation_email(booking.booking_id, db)
    assert success is False, "Sending to booker@example.com must be blocked"

    db.refresh(booking)
    assert booking.email_status == "FAILED"
    assert "placeholder" in (booking.email_error or "").lower()
    assert "booker@example.com" in (booking.email_error or "")
    db.close()


# ---------------------------------------------------------------------------
# 11. Missing Customer Email Causes Controlled Failure
# ---------------------------------------------------------------------------
def test_missing_customer_email_controlled_failure():
    """Verifies that a booking with no customer email fails gracefully."""
    db = TestingSession()
    booking = Booking(
        booking_id="GN-2026-NOEMAIL",
        customer_name="No Email Customer",
        email="",
        phone="+91 99999 77777",
        ticket_count=1,
        ticket_price=599.0,
        regular_amount=599.0,
        group_discount=0.0,
        ticket_subtotal=599.0,
        amount=599.0,
        currency="INR",
        payment_method="RAZORPAY",
        payment_status="PAID",
        booking_status="CONFIRMED",
        email_status="PENDING",
        owner_notified=False,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)

    success = EmailService.send_confirmation_email(booking.booking_id, db)
    assert success is False, "Sending with empty email must fail"

    db.refresh(booking)
    assert booking.email_status == "FAILED"
    assert "missing" in (booking.email_error or "").lower() or "invalid" in (booking.email_error or "").lower()
    db.close()


# ---------------------------------------------------------------------------
# 12. Real Customer Email Uses booking.email (Backend Source of Truth)
# ---------------------------------------------------------------------------
def test_real_customer_email_from_booking_record():
    """Confirms that the confirmation email recipient is the booking's stored email, not a placeholder."""
    db = TestingSession()
    real_email = "customer@gmail.com"
    booking = Booking(
        booking_id="GN-2026-REAL01",
        customer_name="Real Customer",
        email=real_email,
        phone="+91 98765 43210",
        ticket_count=2,
        ticket_price=599.0,
        regular_amount=1198.0,
        group_discount=0.0,
        ticket_subtotal=1198.0,
        amount=1198.0,
        currency="INR",
        payment_method="RAZORPAY",
        payment_status="PAID",
        booking_status="CONFIRMED",
        email_status="PENDING",
        owner_notified=False,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)

    for i in range(2):
        ticket = Ticket(
            booking_id=booking.id,
            ticket_id=f"TKT-REAL01-{i+1:02d}",
            customer_name="Real Customer",
            event_name="NAVRANG 2026",
            qr_token_raw=f"RAW_QR_TOKEN_REAL01_{i+1}",
            qr_token_hash=f"HASH_REAL01_{i+1}",
            ticket_status="VALID",
        )
        db.add(ticket)
    db.commit()
    db.refresh(booking)

    setting = db.query(EventSetting).first()
    setting.email_provider = "resend"
    setting.resend_api_key = "re_mock_test_key_12345"
    db.commit()

    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({"id": "resend_real_customer"}).encode("utf-8")
    mock_response.__enter__.return_value = mock_response

    with patch("urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
        success = EmailService.send_confirmation_email(booking.booking_id, db)
        assert success is True

        # Verify the email was sent to the REAL customer email and admin email, not a placeholder
        mock_urlopen.assert_called_once()
        req = mock_urlopen.call_args[0][0]
        payload = json.loads(req.data.decode("utf-8"))
        assert real_email in payload["to"]
        assert "samaymadhyastha2005@gmail.com" in payload["to"]
        assert "booker@example.com" not in str(payload["to"])

    db.refresh(booking)
    assert booking.email_status == "SENT"
    assert booking.admin_email_status == "SENT"
    assert booking.email_sent_at is not None
    db.close()


# ---------------------------------------------------------------------------
# 13. Owner Notification Uses OWNER_NOTIFICATION_EMAIL, Not Customer Email
# ---------------------------------------------------------------------------
def test_owner_notification_uses_owner_email():
    """Confirms owner notification goes to OWNER_NOTIFICATION_EMAIL, not the customer."""
    db = TestingSession()
    booking = Booking(
        booking_id="GN-2026-OWNERCHK",
        customer_name="Owner Check Customer",
        email="customer_real@gmail.com",
        phone="+91 99999 11111",
        ticket_count=1,
        ticket_price=599.0,
        regular_amount=599.0,
        group_discount=0.0,
        ticket_subtotal=599.0,
        amount=599.0,
        currency="INR",
        payment_method="RAZORPAY",
        payment_status="PAID",
        booking_status="CONFIRMED",
        email_status="PENDING",
        owner_notified=False,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)

    setting = db.query(EventSetting).first()
    setting.email_provider = "resend"
    setting.resend_api_key = "re_mock_test_key_12345"
    db.commit()

    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({"id": "resend_owner_check"}).encode("utf-8")
    mock_response.__enter__.return_value = mock_response

    with patch.dict(os.environ, {"OWNER_NOTIFICATION_EMAIL": ""}, clear=False), \
         patch.object(settings, "OWNER_NOTIFICATION_EMAIL", ""), \
         patch("urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
        success = EmailService.send_owner_notification(booking.booking_id, db)
        assert success is True

        mock_urlopen.assert_called_once()
        req = mock_urlopen.call_args[0][0]
        payload = json.loads(req.data.decode("utf-8"))

        # Owner email must be the configured owner, NOT the customer
        owner_email = setting.owner_notification_email
        assert payload["to"] == [owner_email]
        assert "customer_real@gmail.com" not in payload["to"]
        assert "booker@example.com" not in str(payload["to"])

    db.refresh(booking)
    assert booking.owner_notified is True
    db.close()


# ---------------------------------------------------------------------------
# 14. Dual Recipient Automatic Confirmation (Booker + Admin)
# ---------------------------------------------------------------------------
def test_dual_email_dispatch_booker_and_admin():
    """Verifies that automatic confirmation sends identical email with PDF and QR to both booker and Samaymadhyastha2005@gmail.com."""
    db = TestingSession()
    booking = create_sample_booking(db, "GN-2026-DUAL01", ticket_count=2)

    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({"id": "resend_dual_msg_123"}).encode("utf-8")
    mock_response.__enter__.return_value = mock_response

    with patch("urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
        success = EmailService.send_confirmation_email(booking.booking_id, db, send_to_admin=True)
        assert success is True

        mock_urlopen.assert_called_once()
        req = mock_urlopen.call_args[0][0]
        payload = json.loads(req.data.decode("utf-8"))

        # Both booker and admin must be in recipient list
        assert len(payload["to"]) == 2
        assert "testbooker@garbanight.in" in payload["to"]
        assert "samaymadhyastha2005@gmail.com" in payload["to"]

        # Content must contain Booking ID, passes, pricing, and PDF attachment
        assert "GN-2026-DUAL01" in payload["subject"]
        assert "GN-2026-DUAL01" in payload["html"]
        assert "2 Pass" in payload["html"]
        assert "₹1,198.00" in payload["html"] or "1198" in payload["html"]
        assert len(payload["attachments"]) == 1
        assert payload["attachments"][0]["filename"].endswith(".pdf")

    db.refresh(booking)
    assert booking.email_status == "SENT"
    assert booking.admin_email_status == "SENT"
    assert booking.email_sent_at is not None
    assert booking.admin_email_sent_at is not None
    db.close()


# ---------------------------------------------------------------------------
# 15. Admin Email Environment Variable Configuration Takes Precedence
# ---------------------------------------------------------------------------
def test_admin_email_env_var_override():
    """Verifies ADMIN_NOTIFICATION_EMAIL environment variable takes precedence."""
    db = TestingSession()
    booking = create_sample_booking(db, "GN-2026-ENV01")

    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({"id": "resend_env_msg"}).encode("utf-8")
    mock_response.__enter__.return_value = mock_response

    custom_admin = "custom_event_admin@garbanight.in"
    with patch.dict(os.environ, {"ADMIN_NOTIFICATION_EMAIL": custom_admin}), \
         patch("urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
        success = EmailService.send_confirmation_email(booking.booking_id, db, send_to_admin=True)
        assert success is True

        req = mock_urlopen.call_args[0][0]
        payload = json.loads(req.data.decode("utf-8"))
        assert custom_admin in payload["to"]
        assert "testbooker@garbanight.in" in payload["to"]

    db.refresh(booking)
    assert booking.admin_email_status == "SENT"
    db.close()


# ---------------------------------------------------------------------------
# 16. Deduplication When Booker Email Equals Admin Email
# ---------------------------------------------------------------------------
def test_deduplication_when_booker_is_admin():
    """Verifies that if the booker email is Samaymadhyastha2005@gmail.com, only one email is dispatched."""
    db = TestingSession()
    booking = create_sample_booking(db, "GN-2026-ADMINBOOK")
    booking.email = "Samaymadhyastha2005@gmail.com"
    db.commit()
    db.refresh(booking)

    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({"id": "resend_dedup_msg"}).encode("utf-8")
    mock_response.__enter__.return_value = mock_response

    with patch("urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
        success = EmailService.send_confirmation_email(booking.booking_id, db, send_to_admin=True)
        assert success is True

        mock_urlopen.assert_called_once()
        req = mock_urlopen.call_args[0][0]
        payload = json.loads(req.data.decode("utf-8"))

        # Exactly 1 recipient to avoid duplicate delivery to the admin
        assert payload["to"] == ["samaymadhyastha2005@gmail.com"]

    db.refresh(booking)
    assert booking.email_status == "SENT"
    assert booking.admin_email_status == "SENT"
    db.close()


# ---------------------------------------------------------------------------
# 17. Manual Resend ("EMAIL TICKET" Button) Sends ONLY to Booker
# ---------------------------------------------------------------------------
def test_manual_resend_sends_only_to_booker():
    """Verifies that when send_to_admin=False, the email is strictly sent to the booker, not admin."""
    db = TestingSession()
    booking = create_sample_booking(db, "GN-2026-RESEND01")

    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({"id": "resend_manual_msg"}).encode("utf-8")
    mock_response.__enter__.return_value = mock_response

    with patch("urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
        success = EmailService.send_confirmation_email(booking.booking_id, db, send_to_admin=False)
        assert success is True

        mock_urlopen.assert_called_once()
        req = mock_urlopen.call_args[0][0]
        payload = json.loads(req.data.decode("utf-8"))

        # Strictly the booker's email
        assert payload["to"] == ["testbooker@garbanight.in"]
        assert "samaymadhyastha2005@gmail.com" not in payload["to"]

    db.refresh(booking)
    assert booking.email_status == "SENT"
    db.close()


# ---------------------------------------------------------------------------
# 18. Recipient-Level Delivery Status Tracking on Partial Failure
# ---------------------------------------------------------------------------
def test_recipient_level_status_tracking():
    """Verifies that if customer email succeeds and admin email fails, delivery statuses reflect accurately."""
    db = TestingSession()
    booking = create_sample_booking(db, "GN-2026-PARTIAL01")

    # Combined dispatch fails; separate customer succeeds, admin fails
    def mock_dispatch(to_emails, subject, html_content, config, attachments, is_owner=False, qr_bytes=None):
        if len(to_emails) > 1:
            raise RuntimeError("Combined batch dispatch simulated failure")
        if "testbooker@garbanight.in" in to_emails:
            return {"success": True, "to": to_emails}
        if "samaymadhyastha2005@gmail.com" in to_emails:
            raise RuntimeError("Admin mailbox rejected message")
        return {"success": True}

    with patch.object(EmailService, "_dispatch_message", side_effect=mock_dispatch):
        success = EmailService.send_confirmation_email(booking.booking_id, db, send_to_admin=True)
        assert success is True

    db.refresh(booking)
    assert booking.email_status == "SENT"
    assert booking.admin_email_status == "FAILED"
    assert "Admin mailbox rejected" in (booking.admin_email_error or "")
    # Confirmed booking and payment are NEVER reversed on email failure
    assert booking.booking_status == "CONFIRMED"
    assert booking.payment_status == "PAID"
    db.close()

