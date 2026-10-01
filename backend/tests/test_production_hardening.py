import pytest
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app, init_db_defaults
from app.config import settings
from app.database import Base, get_db, sync_database_schema
from app.models.user import User
from app.models.event_setting import EventSetting
from app.models.ticket_phase import TicketPhase
from app.models.booking import Booking
from app.models.ticket import Ticket
from app.models.payment import Payment
from app.utils.security import get_password_hash, verify_password, create_access_token
from app.services.booking_service import BookingService
from app.services.payment_service import payment_service

TEST_HARDENING_DB = "./test_hardening.db"
engine = create_engine(f"sqlite:///{TEST_HARDENING_DB}", connect_args={"check_same_thread": False})
SessionTesting = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="module", autouse=True)
def setup_hardening_env():
    os.environ["RAZORPAY_MODE"] = "TEST"
    os.environ["RAZORPAY_KEY_ID"] = "rzp_test_hardening_key"
    os.environ["RAZORPAY_KEY_SECRET"] = "rzp_test_hardening_secret"
    os.environ["RAZORPAY_WEBHOOK_SECRET"] = "rzp_test_hardening_whsec"
    os.environ["JWT_SECRET"] = "test_jwt_secret_at_least_32_characters_long_for_security"
    os.environ["QR_SECRET_SALT"] = "test_qr_salt_at_least_32_characters_long_for_security"
    os.environ["PAYMENT_RESERVATION_MINUTES"] = "15"

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = SessionTesting()
    # Ensure default event setting
    setting = EventSetting(
        event_name="NAVRANG 2026",
        ticket_price=599.0,
        total_capacity=50,
        max_per_booking=10,
        booking_open=True
    )
    db.add(setting)

    # Add Phases
    p_early = TicketPhase(
        phase_code="EARLY_BIRD",
        name="Early Bird",
        price=599.0,
        total_inventory=10,
        sold_count=0,
        status="ACTIVE",
        group_offer_eligible=True
    )
    p_locked = TicketPhase(
        phase_code="PHASE_1",
        name="Phase 1",
        price=799.0,
        total_inventory=20,
        sold_count=0,
        status="LOCKED",
        group_offer_eligible=False
    )
    p_soldout = TicketPhase(
        phase_code="PHASE_2",
        name="Phase 2",
        price=899.0,
        total_inventory=5,
        sold_count=5,
        status="SOLD_OUT",
        group_offer_eligible=False
    )
    db.add_all([p_early, p_locked, p_soldout])

    # Add Admin and Staff Users
    admin = User(
        email="superadmin@garbanight.in",
        name="Admin",
        password_hash=get_password_hash("SuperAdmin@2026"),
        role="SUPER_ADMIN",
        is_active=True
    )
    staff = User(
        email="scanner@garbanight.in",
        name="Staff Scanner",
        password_hash=get_password_hash("StaffScan@2026"),
        role="CHECKIN_STAFF",
        is_active=True
    )
    db.add_all([admin, staff])
    db.commit()
    db.close()

    yield

    Base.metadata.drop_all(bind=engine)
    if os.path.exists(TEST_HARDENING_DB):
        try:
            os.remove(TEST_HARDENING_DB)
        except Exception:
            pass

@pytest.fixture
def db():
    session = SessionTesting()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture
def client(db):
    def override_db():
        try:
            yield db
        finally:
            pass
    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ==============================================================================
# 1. RAZORPAY LIVE/TEST VALIDATION TESTS
# ==============================================================================

def test_razorpay_mode_and_key_combinations(db):
    provider = payment_service.get_provider(db)
    
    # 1. TEST mode + rzp_test_ -> PASS
    with patch.dict(os.environ, {"RAZORPAY_MODE": "TEST", "RAZORPAY_KEY_ID": "rzp_test_valid123"}):
        key_id, key_secret, webhook_secret, mode = provider._get_credentials(db)
        assert key_id.startswith("rzp_test_")

    # 2. TEST mode + rzp_live_ -> FAIL (must raise HTTPException)
    with patch.dict(os.environ, {"RAZORPAY_MODE": "TEST", "RAZORPAY_KEY_ID": "rzp_live_invalid_for_test"}):
        with pytest.raises(Exception) as exc:
            provider._get_credentials(db)
        assert "Do NOT use live keys in TEST mode" in str(exc.value)

    # 3. LIVE mode + rzp_test_ -> FAIL
    with patch.dict(os.environ, {"RAZORPAY_MODE": "LIVE", "RAZORPAY_KEY_ID": "rzp_test_invalid_for_live", "RAZORPAY_KEY_SECRET": "sec"}):
        with pytest.raises(Exception) as exc:
            provider._get_credentials(db)
        assert "Do NOT use test keys in LIVE mode" in str(exc.value)

    # 4. LIVE mode + rzp_live_ -> PASS
    with patch.dict(os.environ, {"RAZORPAY_MODE": "LIVE", "RAZORPAY_KEY_ID": "rzp_live_valid123", "RAZORPAY_KEY_SECRET": "sec"}):
        key_id, key_secret, webhook_secret, mode = provider._get_credentials(db)
        assert key_id.startswith("rzp_live_")


# ==============================================================================
# 2. INVENTORY & OVERSELL PROTECTION TESTS
# ==============================================================================

def test_phase_restrictions_and_oversell_protection(client, db):
    # Locked phase cannot be purchased
    res_locked = client.post("/api/payments/create-order", json={
        "customer_name": "Test User",
        "email": "user@test.com",
        "phone": "9998887770",
        "ticket_count": 2,
        "ticket_phase": "PHASE_1"
    })
    assert res_locked.status_code == 400
    assert "currently locked" in res_locked.json()["detail"]

    # Sold out phase cannot be purchased
    res_soldout = client.post("/api/payments/create-order", json={
        "customer_name": "Test User",
        "email": "user@test.com",
        "phone": "9998887770",
        "ticket_count": 1,
        "ticket_phase": "PHASE_2"
    })
    assert res_soldout.status_code == 400
    assert "sold_out" in res_soldout.json()["detail"].lower()

    # Active phase (inventory=10) can be booked up to 10
    with patch("razorpay.Client") as mock_rzp:
        mock_instance = MagicMock()
        mock_instance.order.create.return_value = {
            "id": "order_early_mock",
            "amount": 599000,
            "currency": "INR",
            "status": "created"
        }
        mock_rzp.return_value = mock_instance

        # Request 10 tickets (group offer)
        res_ok = client.post("/api/payments/create-order", json={
            "customer_name": "Group Buyer",
            "email": "group@test.com",
            "phone": "9998887771",
            "ticket_count": 10,
            "ticket_phase": "EARLY_BIRD"
        })
        assert res_ok.status_code == 200
        booking_data = res_ok.json()
        assert booking_data["ticket_count"] == 10
        assert booking_data["ticket_subtotal"] in (4999.0, 5391.0) # Group of 10 Authoritative Offer or legacy Buy 10 Pay For 9

        # Now all 10 tickets in EARLY_BIRD are reserved! An 11th ticket must be rejected!
        res_exceeded = client.post("/api/payments/create-order", json={
            "customer_name": "Late Buyer",
            "email": "late@test.com",
            "phone": "9998887772",
            "ticket_count": 1,
            "ticket_phase": "EARLY_BIRD"
        })
        assert res_exceeded.status_code == 400
        assert "remaining in Early Bird" in res_exceeded.json()["detail"]


def test_reservation_timeout_releases_inventory(db):
    # Find the pending booking created in previous test
    pending_booking = db.query(Booking).filter(Booking.email == "group@test.com").first()
    assert pending_booking is not None
    assert pending_booking.reservation_expires_at is not None

    # Simulate reservation expiration (set expiry in the past)
    pending_booking.reservation_expires_at = datetime.utcnow() - timedelta(minutes=5)
    db.commit()

    # Now check phase capacity again: expired reservation should NOT block new booking
    avail, rem, phase_obj = BookingService.check_phase_capacity(db, requested_tickets=2, phase_code="EARLY_BIRD")
    assert avail is True
    assert rem >= 2


# ==============================================================================
# 3. RBAC & SENSITIVE ENDPOINTS PROTECTION
# ==============================================================================

def test_staff_cannot_access_admin_endpoints(client, db):
    # Login as Staff
    staff_user = db.query(User).filter(User.role == "CHECKIN_STAFF").first()
    staff_token = create_access_token({"sub": str(staff_user.id), "role": staff_user.role, "email": staff_user.email})
    staff_headers = {"Authorization": f"Bearer {staff_token}"}

    # Staff trying to access /api/admin/settings -> 403 Forbidden
    res_settings = client.get("/api/admin/settings", headers=staff_headers)
    assert res_settings.status_code == 403

    # Staff trying to access /api/admin/audit-logs -> 403 Forbidden
    res_logs = client.get("/api/admin/audit-logs", headers=staff_headers)
    assert res_logs.status_code == 403

    # Unauthenticated calling /api/qr/verify -> 401 Unauthorized
    res_unauth_qr = client.post("/api/qr/verify", json={"qr_token": "some_random_token"})
    assert res_unauth_qr.status_code == 401

    # Staff calling /api/qr/verify -> 200 OK (with valid/invalid status)
    res_auth_qr = client.post("/api/qr/verify", json={"qr_token": "nonexistent_token"}, headers=staff_headers)
    assert res_auth_qr.status_code == 200
    assert res_auth_qr.json()["valid"] is False


def test_public_cannot_enumerate_private_tickets(client, db):
    # Unauthenticated lookup by booking_id alone without contact -> must be rejected
    res_no_contact = client.get("/api/bookings/status/lookup?booking_id=GN-2026-99999")
    assert res_no_contact.status_code == 400
    assert "Verification required" in res_no_contact.json()["detail"]

    # Seed a real ticket in DB
    dummy_booking = Booking(
        booking_id="GN-2026-PRIVACY",
        customer_name="Privacy Tester",
        email="privacy@example.com",
        phone="9988776655",
        ticket_count=1,
        ticket_price=599.0,
        amount=599.0,
        payment_status="PAID",
        booking_status="CONFIRMED"
    )
    db.add(dummy_booking)
    db.commit()

    dummy_ticket = Ticket(
        ticket_id="GN26-TKT-PRIVACY-01",
        booking_id=dummy_booking.id,
        customer_name=dummy_booking.customer_name,
        event_name="NAVRANG 2026",
        qr_token_hash="sample_hash",
        qr_token_raw="sample_raw_token_12345",
        ticket_status="VALID",
        checkin_status=False
    )
    db.add(dummy_ticket)
    db.commit()

    # Public single ticket PDF without secret token -> 403 Forbidden
    res_pdf_no_token = client.get(f"/api/tickets/{dummy_ticket.ticket_id}/pdf")
    assert res_pdf_no_token.status_code == 403
    assert "Secure ticket access token required" in res_pdf_no_token.json()["detail"]

    # Public single ticket PDF with correct secret token -> 200 OK
    res_pdf_valid = client.get(f"/api/tickets/{dummy_ticket.ticket_id}/pdf?token={dummy_ticket.qr_token_raw}")
    assert res_pdf_valid.status_code == 200


# ==============================================================================
# 4. STARTUP USER SEEDING NEVER OVERWRITES PASSWORDS
# ==============================================================================

def test_startup_seeding_does_not_overwrite_passwords(db):
    # Change the admin password to a custom password
    admin = db.query(User).filter(User.role == "SUPER_ADMIN").first()
    custom_password = "MyCustomNewSecretPassword123!"
    admin.password_hash = get_password_hash(custom_password)
    db.commit()

    # Re-run init_db_defaults (simulating app restart)
    with patch("app.main.SessionLocal", SessionTesting):
        init_db_defaults()

    # Verify that the custom password was NOT overwritten
    admin_after = db.query(User).filter(User.role == "SUPER_ADMIN").first()
    assert verify_password(custom_password, admin_after.password_hash) is True


# ==============================================================================
# 5. EMAIL FAILURE DOES NOT ROLLBACK CONFIRMED BOOKINGS
# ==============================================================================

def test_email_failure_does_not_cancel_confirmed_booking(client, db):
    # Create and confirm booking with mocked failing email service
    booking = Booking(
        booking_id="GN-2026-TESTFAIL",
        customer_name="Resilient Customer",
        email="resilient@example.com",
        phone="9988776655",
        ticket_count=1,
        ticket_price=599.0,
        amount=599.0,
        payment_status="PENDING",
        booking_status="PENDING"
    )
    db.add(booking)
    db.commit()

    # Mock EmailService to raise an unhandled exception
    with patch("app.services.email_service.EmailService.send_confirmation_email", side_effect=Exception("SMTP Connection Refused")):
        # Confirm booking and generate tickets
        confirmed_booking = BookingService.confirm_booking_and_generate_tickets(
            booking_id=booking.booking_id,
            razorpay_payment_id="pay_email_fail_123",
            db=db
        )
        assert confirmed_booking.booking_status == "CONFIRMED"
        assert confirmed_booking.payment_status in ["PAID", "CAPTURED"]
        assert len(confirmed_booking.tickets) == 1

        # Check DB directly to ensure booking wasn't rolled back
        db.refresh(booking)
        assert booking.booking_status == "CONFIRMED"
        assert len(booking.tickets) == 1
