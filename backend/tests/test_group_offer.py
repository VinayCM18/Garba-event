import pytest
import sys
import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch, MagicMock
import hmac
import hashlib
from app.config import settings
from app.main import app
from app.database import Base, get_db
from app.models.user import User
from app.models.event_setting import EventSetting
from app.models.booking import Booking
from app.models.ticket import Ticket
from app.utils.security import get_password_hash, create_access_token
from app.services.email_service import EmailService

TEST_DB_FILE = "./test_group_offer.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_FILE}"

test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    os.environ["PASS_GATEWAY_FEE_TO_CUSTOMER"] = "true"
    os.environ["RAZORPAY_MODE"] = "TEST"
    os.environ["RAZORPAY_KEY_ID"] = "rzp_test_group_key_123"
    os.environ["RAZORPAY_KEY_SECRET"] = "rzp_test_secret_456"
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    
    db = TestingSessionLocal()
    # Seed event setting with Group Offer configured:
    # Regular ticket price = 599.0, max_per_booking = 10, group_offer_size = 10, free_tickets = 1
    setting = EventSetting(
        event_name="GARBA NIGHT 2026",
        ticket_price=599.0,
        total_capacity=500,
        max_per_booking=10,
        booking_open=True,
        group_offer_enabled=True,
        group_offer_size=10,
        group_offer_free_tickets=1
    )
    db.add(setting)

    # Seed Admin User
    admin = User(
        email="admin@example.com",
        name="Test Admin",
        password_hash=get_password_hash("TestPass@123"),
        role="SUPER_ADMIN",
        is_active=True
    )
    db.add(admin)

    # Seed Staff User
    staff = User(
        email="staff@example.com",
        name="Test Staff",
        password_hash=get_password_hash("StaffPass@123"),
        role="CHECKIN_STAFF",
        is_active=True
    )
    db.add(staff)
    db.commit()
    db.close()

    yield

    Base.metadata.drop_all(bind=test_engine)
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except Exception:
            pass

@pytest.fixture(scope="function")
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# =========================================================================
# TEST 1: Public Event Config Returns Group Offer Settings
# =========================================================================
def test_public_event_config_has_group_offer(client):
    res = client.get("/api/bookings/public-config")
    assert res.status_code == 200
    data = res.json()
    assert data["ticket_price"] == 599.0
    assert data["group_offer_enabled"] is True
    assert data["group_offer_size"] == 10
    assert data["group_offer_free_tickets"] == 1
    assert data["group_offer_discount"] == 599.0
    assert data["group_offer_regular_total"] == 5990.0
    assert data["group_offer_subtotal"] == 5391.0


# =========================================================================
# TEST 2: Fee Calculation for 1, 5, 8, 9, and 10 tickets
# =========================================================================
@pytest.mark.parametrize("count, expected_subtotal, expected_discount, is_offer", [
    (1, 599.0, 0.0, False),
    (5, 2995.0, 0.0, False),
    (8, 4792.0, 0.0, False),
    (9, 5391.0, 0.0, False),     # 9 tickets: normal price
    (10, 5391.0, 599.0, True),   # 10 tickets: BUY 10, PAY FOR 9
])
def test_fee_calculation_endpoint(client, count, expected_subtotal, expected_discount, is_offer):
    res = client.get(f"/api/payments/calculate?ticket_count={count}")
    assert res.status_code == 200
    data = res.json()
    assert data["ticket_subtotal"] == expected_subtotal
    assert data["group_discount"] == expected_discount
    assert data["is_group_offer"] == is_offer
    if is_offer:
        assert data["regular_amount"] == 5990.0
        assert data["free_tickets"] == 1
        assert data["offer_name"] in ("Group of 10", "BUY 10, PAY FOR 9")
        # Subtotal: 5391.0, 2% fee = 107.82, 18% GST on fee = 19.41, total = 5518.23
        assert data["payment_fee"] == 107.82
        assert data["gst_amount"] == 19.41
        assert data["total_amount"] == 5518.23


# =========================================================================
# TEST 3: Create Order for 10 Tickets (Backend Pricing & Razorpay Amount)
# =========================================================================
def test_create_order_for_10_tickets(client):
    with patch("razorpay.Client") as mock_client:
        mock_instance = MagicMock()
        mock_instance.order.create.return_value = {
            "id": "order_mock_group_10",
            "amount": 551823,
            "currency": "INR",
            "status": "created"
        }
        mock_client.return_value = mock_instance
        res = client.post("/api/payments/create-order", json={
            "customer_name": "Garba Squad Leader",
            "email": "squad@example.com",
            "phone": "+919876543210",
            "ticket_count": 10
        })
    assert res.status_code == 200
    data = res.json()
    assert data["ticket_count"] == 10
    assert data["regular_amount"] == 5990.0
    assert data["group_discount"] == 599.0
    assert data["ticket_subtotal"] == 5391.0
    assert data["is_group_offer"] is True
    assert data["offer_name"] in ("Group of 10", "BUY 10, PAY FOR 9")
    assert data["free_tickets"] in (0, 1)
    # Backend-calculated total amount must not be ₹5,990! It must be based on ₹5,391
    assert data["amount"] == 5518.23
    assert data["booking_id"].startswith("GN-2026-")


# =========================================================================
# TEST 4: Payment Verification & 10 Unique QR Code Tickets
# =========================================================================
def test_payment_and_10_unique_valid_tickets(client, db_session):
    # Step 1: Create Order for 10 tickets
    with patch("razorpay.Client") as mock_client:
        mock_instance = MagicMock()
        mock_instance.order.create.return_value = {
            "id": "order_mock_group_10_unique",
            "amount": 551823,
            "currency": "INR",
            "status": "created"
        }
        mock_client.return_value = mock_instance
        order_res = client.post("/api/payments/create-order", json={
            "customer_name": "Navratri Group",
            "email": "navratri@example.com",
            "phone": "+919876543210",
            "ticket_count": 10
        })
    assert order_res.status_code == 200
    order_data = order_res.json()
    booking_id = order_data["booking_id"]
    order_id = order_data["razorpay_order_id"]
    payment_id = f"pay_test_{booking_id}"

    # Generate valid HMAC signature matching the test secret
    secret = os.environ.get("RAZORPAY_KEY_SECRET") or settings.RAZORPAY_KEY_SECRET or "rzp_test_secret_456"
    msg = f"{order_id}|{payment_id}".encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()

    # Step 2: Verify payment with real HMAC signature
    verify_res = client.post("/api/payments/verify", json={
        "booking_id": booking_id,
        "razorpay_order_id": order_id,
        "razorpay_payment_id": payment_id,
        "razorpay_signature": sig
    })
    assert verify_res.status_code == 200
    verify_data = verify_res.json()
    assert verify_data["payment_status"] == "PAID"
    assert verify_data["booking_status"] == "CONFIRMED"

    # Step 3: Fetch booking record from DB
    booking = db_session.query(Booking).filter(Booking.booking_id == booking_id).first()
    assert booking is not None
    assert booking.ticket_count == 10
    assert booking.regular_amount == 5990.0
    assert booking.group_discount == 599.0
    assert booking.ticket_subtotal == 5391.0
    assert booking.amount == 5518.23

    # Step 4: Verify all 10 tickets
    tickets = db_session.query(Ticket).filter(Ticket.booking_id == booking.id).all()
    assert len(tickets) == 10, f"Expected 10 tickets, found {len(tickets)}"

    # Verify each ticket has unique QR token and ticket_status == VALID
    tokens = [t.qr_token_raw for t in tickets]
    assert len(set(tokens)) == 10, "All 10 tickets must have unique QR tokens"
    
    hashes = [t.qr_token_hash for t in tickets]
    assert len(set(hashes)) == 10, "All 10 tickets must have unique token hashes"

    for idx, t in enumerate(tickets, 1):
        assert t.ticket_status == "VALID", f"Ticket {idx} status should be VALID"
        assert t.checkin_status is False
        assert t.ticket_id.endswith(f"-{str(idx).zfill(2)}")

    # Step 5: Test check-in of the 10th (free) ticket to prove it is 100% functional
    staff_user = db_session.query(User).filter(User.role == "CHECKIN_STAFF").first()
    staff_token = create_access_token({"sub": str(staff_user.id), "role": staff_user.role, "email": staff_user.email})
    staff_headers = {"Authorization": f"Bearer {staff_token}"}

    ticket_10 = tickets[9]
    verify_qr_res = client.post("/api/qr/verify", json={
        "qr_token": ticket_10.qr_token_raw
    }, headers=staff_headers)
    assert verify_qr_res.status_code == 200
    assert verify_qr_res.json()["valid"] is True
    assert verify_qr_res.json()["ticket_status"] == "VALID"

    checkin_res = client.post("/api/qr/checkin", json={
        "qr_token": ticket_10.qr_token_raw
    }, headers=staff_headers)
    assert checkin_res.status_code == 200
    assert checkin_res.json()["success"] is True


# =========================================================================
# TEST 5: Public Booking Details Endpoint Returns Group Offer Info
# =========================================================================
def test_public_booking_details(client, db_session):
    booking = db_session.query(Booking).filter(Booking.ticket_count == 10, Booking.payment_status == "PAID").first()
    assert booking is not None

    res = client.get(f"/api/bookings/{booking.booking_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["ticket_count"] == 10
    assert data["regular_amount"] == 5990.0
    assert data["group_discount"] == 599.0
    assert data["ticket_subtotal"] == 5391.0
    assert data["is_group_offer"] is True
    assert data["offer_name"] in ("Group of 10", "BUY 10, PAY FOR 9")
    assert len(data["tickets"]) == 10


# =========================================================================
# TEST 6: Admin Settings Toggle Group Offer ON / OFF
# =========================================================================
def test_admin_settings_toggle_group_offer(client, db_session):
    admin_user = db_session.query(User).filter(User.role == "SUPER_ADMIN").first()
    admin_token = create_access_token({"sub": str(admin_user.id), "role": admin_user.role, "email": admin_user.email})
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Fetch current settings
    get_res = client.get("/api/admin/settings", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["group_offer_enabled"] is True

    # 2. Disable Group Offer
    put_res = client.put("/api/admin/settings", json={
        "group_offer_enabled": False
    }, headers=headers)
    assert put_res.status_code == 200
    assert put_res.json()["group_offer_enabled"] is False

    # 3. When disabled, 10 tickets should NOT get group discount
    calc_res = client.get("/api/payments/calculate?ticket_count=10")
    assert calc_res.status_code == 200
    calc_data = calc_res.json()
    assert calc_data["group_discount"] == 0.0
    assert calc_data["ticket_subtotal"] == 5990.0
    assert calc_data["is_group_offer"] is False

    # 4. Re-enable Group Offer
    re_enable_res = client.put("/api/admin/settings", json={
        "group_offer_enabled": True
    }, headers=headers)
    assert re_enable_res.status_code == 200
    assert re_enable_res.json()["group_offer_enabled"] is True

    # 5. Check calculation is back to BUY 10, PAY FOR 9
    calc_re_res = client.get("/api/payments/calculate?ticket_count=10")
    assert calc_re_res.json()["group_discount"] == 599.0
    assert calc_re_res.json()["ticket_subtotal"] == 5391.0
    assert calc_re_res.json()["is_group_offer"] is True


# =========================================================================
# TEST 7: Confirmation Email HTML Template Displays Group Offer Breakdown
# =========================================================================
def test_confirmation_email_html_content(db_session):
    booking = db_session.query(Booking).filter(Booking.ticket_count == 10).first()
    assert booking is not None

    setting = db_session.query(EventSetting).first()

    html = EmailService.render_confirmation_html(booking, setting, "data:image/png;base64,mockqr")
    assert "GROUP BOOKING CONFIRMED" in html
    assert ("BEST VALUE • SAVE ₹991" in html or "GROUP OF 10" in html or "BUY 10, PAY FOR 9" in html)
    assert "5,990" in html
    assert "599" in html
    assert "5,391" in html
    assert "YOU SAVED" in html
