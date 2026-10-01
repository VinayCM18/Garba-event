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
        assert payload["to"] == ["testbooker@garbanight.in"]
        assert "NAVRANG 2026" in payload["from"]
        assert "GN-2026-CONF01" in payload["subject"]
        assert len(payload["attachments"]) == 1
        assert payload["attachments"][0]["filename"].endswith(".pdf")

    # Verify DB state
    db.refresh(booking)
    assert booking.email_status == "SENT"
    assert booking.email_sent_at is not None
    assert booking.email_error is None
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
        mock_smtp.assert_called_once()

    db.refresh(booking)
    assert booking.email_status == "SENT"
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

        # Verify the email was sent to the REAL customer email, not booker@example.com
        mock_urlopen.assert_called_once()
        req = mock_urlopen.call_args[0][0]
        payload = json.loads(req.data.decode("utf-8"))
        assert payload["to"] == [real_email], f"Expected [{real_email}], got {payload['to']}"
        assert "booker@example.com" not in str(payload["to"])

    db.refresh(booking)
    assert booking.email_status == "SENT"
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
