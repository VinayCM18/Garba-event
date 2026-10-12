import pytest
import os
import sys
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.config import settings
from app.database import Base, get_db
from app.models.user import User
from app.models.event_setting import EventSetting
from app.models.ticket_phase import TicketPhase
from app.models.booking import Booking
from app.models.ticket import Ticket
from app.models.checkin import CheckIn
from app.utils.security import get_password_hash, create_access_token, generate_secure_token, hash_qr_token
from app.services.qr_service import qr_service

TEST_QR_DB = "./test_qr_verification.db"
engine = create_engine(f"sqlite:///{TEST_QR_DB}", connect_args={"check_same_thread": False})
SessionTesting = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="module", autouse=True)
def setup_qr_test_env():
    os.environ["JWT_SECRET"] = "test_qr_jwt_secret_at_least_32_characters_long"
    os.environ["QR_SECRET_SALT"] = "test_qr_salt_at_least_32_characters_long"

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionTesting()

    # Event setting
    setting = EventSetting(
        event_name="NAVRANG 2026",
        ticket_price=799.0,
        total_capacity=1500,
        max_per_booking=10,
        booking_open=True
    )
    db.add(setting)

    # Ticket phases: EARLY_BIRD is SOLD_OUT; PHASE_1 is ACTIVE
    eb_phase = TicketPhase(
        phase_code="EARLY_BIRD",
        name="EARLY BIRD",
        price=599.0,
        status="SOLD_OUT",
        badge_text="SOLD OUT",
        total_inventory=100,
        sold_count=100,
        display_order=1
    )
    p1_phase = TicketPhase(
        phase_code="PHASE_1",
        name="PHASE 1",
        price=799.0,
        status="ACTIVE",
        badge_text="AVAILABLE NOW",
        total_inventory=500,
        sold_count=10,
        display_order=2
    )
    db.add_all([eb_phase, p1_phase])

    # Staff user (CHECKIN_STAFF)
    staff_user = User(
        email="gate_staff@navrang.in",
        name="Gate Turnstile Officer",
        role="CHECKIN_STAFF",
        password_hash=get_password_hash("StaffGate@2026"),
        is_active=True
    )
    # Admin user (ADMIN)
    admin_user = User(
        email="admin_scanner@navrang.in",
        name="Operations Admin",
        role="ADMIN",
        password_hash=get_password_hash("AdminPass@2026"),
        is_active=True
    )
    # Customer user (unprivileged role)
    customer_user = User(
        email="customer_guest@navrang.in",
        name="Guest Attendee",
        role="CUSTOMER",
        password_hash=get_password_hash("GuestPass@2026"),
        is_active=True
    )
    db.add_all([staff_user, admin_user, customer_user])
    db.commit()

    # 1. Confirmed Phase 1 Booking with Ticket
    b1 = Booking(
        booking_id="GN-2026-000101",
        customer_name="Pooja Sharma",
        email="pooja@example.com",
        phone="9876543210",
        ticket_count=1,
        ticket_price=799.0,
        amount=799.0,
        ticket_phase="PHASE_1",
        booking_status="CONFIRMED",
        payment_status="PAID"
    )
    db.add(b1)
    db.commit()
    db.refresh(b1)

    raw_token_1 = generate_secure_token(prefix="GN26")
    t1 = Ticket(
        ticket_id="GN26-TKT-000101-01",
        booking_id=b1.id,
        customer_name="Pooja Sharma",
        event_name="NAVRANG 2026",
        qr_token_raw=raw_token_1,
        qr_token_hash=hash_qr_token(raw_token_1),
        ticket_status="VALID",
        checkin_status=False
    )
    db.add(t1)

    # 2. Confirmed Early Bird Booking with Ticket (Early Bird sales closed!)
    b2 = Booking(
        booking_id="GN-2026-000102",
        customer_name="Aarav Patel",
        email="aarav@example.com",
        phone="9812345678",
        ticket_count=1,
        ticket_price=599.0,
        amount=599.0,
        ticket_phase="EARLY_BIRD",
        booking_status="CONFIRMED",
        payment_status="PAID"
    )
    db.add(b2)
    db.commit()
    db.refresh(b2)

    raw_token_2 = generate_secure_token(prefix="GN26")
    t2 = Ticket(
        ticket_id="GN26-TKT-000102-01",
        booking_id=b2.id,
        customer_name="Aarav Patel",
        event_name="NAVRANG 2026",
        qr_token_raw=raw_token_2,
        qr_token_hash=hash_qr_token(raw_token_2),
        ticket_status="VALID",
        checkin_status=False
    )
    db.add(t2)

    # 3. Already Checked-in Ticket
    b3 = Booking(
        booking_id="GN-2026-000103",
        customer_name="Vikram Mehta",
        email="vikram@example.com",
        phone="9876500000",
        ticket_count=1,
        ticket_price=799.0,
        amount=799.0,
        ticket_phase="PHASE_1",
        booking_status="CONFIRMED",
        payment_status="PAID"
    )
    db.add(b3)
    db.commit()
    db.refresh(b3)

    raw_token_3 = generate_secure_token(prefix="GN26")
    t3 = Ticket(
        ticket_id="GN26-TKT-000103-01",
        booking_id=b3.id,
        customer_name="Vikram Mehta",
        event_name="NAVRANG 2026",
        qr_token_raw=raw_token_3,
        qr_token_hash=hash_qr_token(raw_token_3),
        ticket_status="USED",
        checkin_status=True,
        checked_in_at=datetime.utcnow() - timedelta(minutes=45)
    )
    db.add(t3)

    # 4. Cancelled Ticket
    b4 = Booking(
        booking_id="GN-2026-000104",
        customer_name="Sneha Rao",
        email="sneha@example.com",
        phone="9876511111",
        ticket_count=1,
        ticket_price=799.0,
        amount=799.0,
        ticket_phase="PHASE_1",
        booking_status="CANCELLED",
        payment_status="REFUNDED"
    )
    db.add(b4)
    db.commit()
    db.refresh(b4)

    raw_token_4 = generate_secure_token(prefix="GN26")
    t4 = Ticket(
        ticket_id="GN26-TKT-000104-01",
        booking_id=b4.id,
        customer_name="Sneha Rao",
        event_name="NAVRANG 2026",
        qr_token_raw=raw_token_4,
        qr_token_hash=hash_qr_token(raw_token_4),
        ticket_status="CANCELLED",
        checkin_status=False
    )
    db.add(t4)
    db.commit()
    db.close()

    yield

    Base.metadata.drop_all(bind=engine)
    if os.path.exists(TEST_QR_DB):
        try:
            os.remove(TEST_QR_DB)
        except Exception:
            pass


@pytest.fixture
def client():
    def override_db():
        session = SessionTesting()
        try:
            yield session
        finally:
            session.close()
    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def get_token(role: str, user_id: int, email: str) -> str:
    return create_access_token(
        data={"sub": str(user_id), "email": email, "role": role},
        expires_delta=timedelta(hours=2)
    )


# ---------------------------------------------------------------------------
# TEST 1: Valid Confirmed Ticket (Raw Token, Full URL, URL with trailing slash, Ticket ID)
# ---------------------------------------------------------------------------
def test_valid_confirmed_ticket_verification(client):
    db = SessionTesting()
    staff = db.query(User).filter(User.role == "CHECKIN_STAFF").first()
    t1 = db.query(Ticket).filter(Ticket.ticket_id == "GN26-TKT-000101-01").first()
    db.close()

    headers = {"Authorization": f"Bearer {get_token('CHECKIN_STAFF', staff.id, staff.email)}"}

    # 1a. Verify by raw token via /api/staff/ticket/verify
    res = client.post("/api/staff/ticket/verify", json={"qr_token": t1.qr_token_raw}, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is True
    assert data["status"] == "VALID"
    assert data["ticket_id"] == "GN26-TKT-000101-01"
    assert data["customer_name"] == "Pooja Sharma"
    assert data["qr_token_raw"] == t1.qr_token_raw

    # 1b. Verify by raw token via /api/qr/verify (Admin endpoint)
    res_admin = client.post("/api/qr/verify", json={"qr_token": t1.qr_token_raw}, headers=headers)
    assert res_admin.status_code == 200
    data_admin = res_admin.json()
    assert data_admin["valid"] is True
    assert data_admin["status"] == "VALID"
    assert data_admin["qr_token_raw"] == t1.qr_token_raw

    # 1c. Verify by full web address URL with trailing slash
    url_with_slash = f"https://www.heritageproduction.online/ticket/{t1.qr_token_raw}/"
    res_url = client.post("/api/staff/ticket/verify", json={"qr_token": url_with_slash}, headers=headers)
    assert res_url.status_code == 200
    assert res_url.json()["valid"] is True
    assert res_url.json()["status"] == "VALID"

    # 1d. Verify by Ticket ID (e.g. staff manual entry)
    res_id = client.post("/api/staff/ticket/verify", json={"qr_token": "GN26-TKT-000101-01"}, headers=headers)
    assert res_id.status_code == 200
    assert res_id.json()["valid"] is True
    assert res_id.json()["status"] == "VALID"


# ---------------------------------------------------------------------------
# TEST 2: Invalid QR Code
# ---------------------------------------------------------------------------
def test_invalid_qr_code_verification(client):
    db = SessionTesting()
    staff = db.query(User).filter(User.role == "CHECKIN_STAFF").first()
    db.close()

    headers = {"Authorization": f"Bearer {get_token('CHECKIN_STAFF', staff.id, staff.email)}"}

    res = client.post("/api/staff/ticket/verify", json={"qr_token": "GN26_completely_bogus_token_xyz"}, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is False
    assert data["status"] == "INVALID"
    assert "No ticket found" in data["message"]

    res_admin = client.post("/api/qr/verify", json={"qr_token": "RANDOM_INVALID_PAYLOAD"}, headers=headers)
    assert res_admin.status_code == 200
    assert res_admin.json()["valid"] is False
    assert res_admin.json()["status"] == "INVALID"


# ---------------------------------------------------------------------------
# TEST 3: Already-Checked-In Ticket
# ---------------------------------------------------------------------------
def test_already_checked_in_ticket_returns_used(client):
    db = SessionTesting()
    staff = db.query(User).filter(User.role == "CHECKIN_STAFF").first()
    t3 = db.query(Ticket).filter(Ticket.ticket_id == "GN26-TKT-000103-01").first()
    db.close()

    headers = {"Authorization": f"Bearer {get_token('CHECKIN_STAFF', staff.id, staff.email)}"}

    res = client.post("/api/staff/ticket/verify", json={"qr_token": t3.qr_token_raw}, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is False
    assert data["status"] == "USED"
    assert data["checkin_status"] is True
    assert "Already Checked In" in data["message"]


# ---------------------------------------------------------------------------
# TEST 4: Early Bird Ticket from Existing Confirmed Booking
# ---------------------------------------------------------------------------
def test_early_bird_ticket_remains_valid_even_when_sales_closed(client):
    db = SessionTesting()
    staff = db.query(User).filter(User.role == "CHECKIN_STAFF").first()
    t2 = db.query(Ticket).filter(Ticket.ticket_id == "GN26-TKT-000102-01").first()
    # Ensure EARLY_BIRD phase is strictly marked as SOLD_OUT
    eb_phase = db.query(TicketPhase).filter(TicketPhase.phase_code == "EARLY_BIRD").first()
    assert eb_phase.status == "SOLD_OUT"
    db.close()

    headers = {"Authorization": f"Bearer {get_token('CHECKIN_STAFF', staff.id, staff.email)}"}

    res = client.post("/api/staff/ticket/verify", json={"qr_token": t2.qr_token_raw}, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is True
    assert data["status"] == "VALID"
    assert data["ticket_id"] == "GN26-TKT-000102-01"
    assert data["customer_name"] == "Aarav Patel"


# ---------------------------------------------------------------------------
# TEST 5: Unauthenticated Request (Returns 401 Unauthorized)
# ---------------------------------------------------------------------------
def test_unauthenticated_verification_request(client):
    # Calling without Authorization header
    res_staff = client.post("/api/staff/ticket/verify", json={"qr_token": "some_token"})
    assert res_staff.status_code == 401
    assert "Authentication required" in res_staff.json()["detail"]

    res_admin = client.post("/api/qr/verify", json={"qr_token": "some_token"})
    assert res_admin.status_code == 401
    assert "Authentication required" in res_admin.json()["detail"]


# ---------------------------------------------------------------------------
# TEST 6: Authorized Staff Request (Role Checking)
# ---------------------------------------------------------------------------
def test_authorized_staff_and_forbidden_customer(client):
    db = SessionTesting()
    staff = db.query(User).filter(User.role == "CHECKIN_STAFF").first()
    admin = db.query(User).filter(User.role == "ADMIN").first()
    guest = db.query(User).filter(User.role == "CUSTOMER").first()
    t1 = db.query(Ticket).filter(Ticket.ticket_id == "GN26-TKT-000101-01").first()
    db.close()

    staff_headers = {"Authorization": f"Bearer {get_token('CHECKIN_STAFF', staff.id, staff.email)}"}
    admin_headers = {"Authorization": f"Bearer {get_token('ADMIN', admin.id, admin.email)}"}
    guest_headers = {"Authorization": f"Bearer {get_token('CUSTOMER', guest.id, guest.email)}"}

    # Staff passes
    res_staff = client.post("/api/staff/ticket/verify", json={"qr_token": t1.qr_token_raw}, headers=staff_headers)
    assert res_staff.status_code == 200
    assert res_staff.json()["status"] == "VALID"

    # Admin passes
    res_admin = client.post("/api/qr/verify", json={"qr_token": t1.qr_token_raw}, headers=admin_headers)
    assert res_admin.status_code == 200
    assert res_admin.json()["status"] == "VALID"

    # Customer/Guest receives 403 Forbidden
    res_guest = client.post("/api/staff/ticket/verify", json={"qr_token": t1.qr_token_raw}, headers=guest_headers)
    assert res_guest.status_code == 403
    assert "Access denied" in res_guest.json()["detail"]


# ---------------------------------------------------------------------------
# TEST 7: Missing or Malformed QR Payload
# ---------------------------------------------------------------------------
def test_missing_or_malformed_qr_payload(client):
    db = SessionTesting()
    staff = db.query(User).filter(User.role == "CHECKIN_STAFF").first()
    db.close()

    headers = {"Authorization": f"Bearer {get_token('CHECKIN_STAFF', staff.id, staff.email)}"}

    # Missing field -> 422 Unprocessable Entity
    res_missing = client.post("/api/staff/ticket/verify", json={}, headers=headers)
    assert res_missing.status_code == 422

    # Whitespace only token -> Returns status INVALID gracefully
    res_empty = client.post("/api/staff/ticket/verify", json={"qr_token": "   "}, headers=headers)
    assert res_empty.status_code == 200
    assert res_empty.json()["valid"] is False
    assert res_empty.json()["status"] == "INVALID"


# ---------------------------------------------------------------------------
# TEST 8: Cancelled Ticket Verification
# ---------------------------------------------------------------------------
def test_cancelled_ticket_verification(client):
    db = SessionTesting()
    staff = db.query(User).filter(User.role == "CHECKIN_STAFF").first()
    t4 = db.query(Ticket).filter(Ticket.ticket_id == "GN26-TKT-000104-01").first()
    db.close()

    headers = {"Authorization": f"Bearer {get_token('CHECKIN_STAFF', staff.id, staff.email)}"}

    res = client.post("/api/staff/ticket/verify", json={"qr_token": t4.qr_token_raw}, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is False
    assert data["status"] == "CANCELLED"
    assert "CANCELLED" in data["message"]


# ---------------------------------------------------------------------------
# TEST 9: Duplicate Check-In Attempts (Atomic Row-Locking)
# ---------------------------------------------------------------------------
def test_duplicate_check_in_atomic_prevention(client):
    db = SessionTesting()
    staff = db.query(User).filter(User.role == "CHECKIN_STAFF").first()
    t1 = db.query(Ticket).filter(Ticket.ticket_id == "GN26-TKT-000101-01").first()
    assert t1.checkin_status is False
    db.close()

    headers = {"Authorization": f"Bearer {get_token('CHECKIN_STAFF', staff.id, staff.email)}"}

    # Attempt 1: First check-in succeeds with 200 OK
    res_first = client.post(
        "/api/staff/checkin",
        json={"qr_token": t1.qr_token_raw, "device_information": "Test Gate 1"},
        headers=headers
    )
    assert res_first.status_code == 200
    data_first = res_first.json()
    assert data_first["success"] is True
    assert data_first["status"] == "SUCCESS"
    assert data_first["ticket_id"] == "GN26-TKT-000101-01"

    # Verify database ticket state
    db = SessionTesting()
    t1_updated = db.query(Ticket).filter(Ticket.ticket_id == "GN26-TKT-000101-01").first()
    assert t1_updated.checkin_status is True
    assert t1_updated.ticket_status == "USED"
    # Booking and payment status must NOT have changed
    assert t1_updated.booking.booking_status == "CONFIRMED"
    assert t1_updated.booking.payment_status == "PAID"
    db.close()

    # Attempt 2: Second check-in attempt MUST fail with 409 Conflict
    res_dup = client.post(
        "/api/staff/checkin",
        json={"qr_token": t1.qr_token_raw, "device_information": "Test Gate 2"},
        headers=headers
    )
    assert res_dup.status_code == 409
    assert "Already Checked In" in res_dup.json()["detail"]

    # Verify checkin log has recorded both attempts
    db = SessionTesting()
    logs = db.query(CheckIn).filter(CheckIn.ticket_id == t1_updated.id).all()
    assert len(logs) == 2
    assert logs[0].result == "SUCCESS"
    assert logs[1].result == "ALREADY_USED"
    db.close()
