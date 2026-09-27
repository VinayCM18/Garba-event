import pytest
import sys
import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.database import Base, get_db
from app.models.user import User
from app.models.event_setting import EventSetting
from app.models.booking import Booking
from app.models.ticket import Ticket
from app.utils.security import get_password_hash, create_access_token

TEST_DB_FILE = "./test_garba.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_FILE}"

test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    
    db = TestingSessionLocal()
    # Seed event setting
    setting = EventSetting(
        event_name="GARBA NIGHT 2026",
        ticket_price=300.0,
        total_capacity=100,
        max_per_booking=5,
        booking_open=True
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

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_admin_login_success(client):
    response = client.post("/api/auth/login", json={
        "email": "admin@example.com",
        "password": "TestPass@123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["role"] == "SUPER_ADMIN"

def test_admin_login_invalid_password(client):
    response = client.post("/api/auth/login", json={
        "email": "admin@example.com",
        "password": "WrongPassword"
    })
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]

def test_public_event_config(client):
    response = client.get("/api/bookings/public-config")
    assert response.status_code == 200
    data = response.json()
    assert data["event_name"] == "GARBA NIGHT 2026"
    assert data["ticket_price"] == 300.0
    assert data["remaining_tickets"] == 100

def test_create_order_pricing_calculation(client):
    # Customer requests 3 tickets
    response = client.post("/api/payments/create-order", json={
        "customer_name": "Deepak Patel",
        "email": "deepak@example.com",
        "phone": "+919876543210",
        "ticket_count": 3
    })
    assert response.status_code == 200
    data = response.json()
    assert data["ticket_subtotal"] == 900.0 # 3 * 300
    assert data["amount"] == 921.24 # 900 + 18.0 (2% fee) + 3.24 (18% GST)
    assert data["booking_id"].startswith("GN-2026-")

def test_inventory_capacity_exceeded(client):
    # Try booking 6 tickets when max_per_booking is 5
    response = client.post("/api/payments/create-order", json={
        "customer_name": "Over Limit Booker",
        "email": "over@example.com",
        "phone": "+919876543210",
        "ticket_count": 6
    })
    assert response.status_code == 400
    assert "Maximum 5 tickets" in response.json()["detail"]

def test_payment_verification_and_ticket_generation(client):
    # Step 1: Create Order
    order_res = client.post("/api/payments/create-order", json={
        "customer_name": "Rahul Sharma",
        "email": "rahul@example.com",
        "phone": "+919876543210",
        "ticket_count": 2
    })
    assert order_res.status_code == 200
    order_data = order_res.json()
    booking_id = order_data["booking_id"]
    order_id = order_data["razorpay_order_id"]

    # Step 2: Verify Payment
    verify_res = client.post("/api/payments/verify", json={
        "booking_id": booking_id,
        "razorpay_order_id": order_id,
        "razorpay_payment_id": "pay_test_123456",
        "razorpay_signature": "sim_sig_valid_test_signature"
    })
    assert verify_res.status_code == 200
    assert verify_res.json()["success"] is True

    # Step 3: Fetch Confirmed Booking Details
    booking_res = client.get(f"/api/bookings/{booking_id}")
    assert booking_res.status_code == 200
    b_data = booking_res.json()
    assert b_data["payment_status"] == "PAID"
    assert b_data["booking_status"] == "CONFIRMED"
    assert len(b_data["tickets"]) == 2
    assert b_data["tickets"][0]["ticket_id"].startswith("GN26-TKT-")

def test_qr_validation_and_duplicate_checkin_protection(client, db_session):
    # Create booking and verified tickets
    order_res = client.post("/api/payments/create-order", json={
        "customer_name": "Pooja Mehta",
        "email": "pooja@example.com",
        "phone": "+919876543210",
        "ticket_count": 1
    })
    booking_id = order_res.json()["booking_id"]
    order_id = order_res.json()["razorpay_order_id"]

    client.post("/api/payments/verify", json={
        "booking_id": booking_id,
        "razorpay_order_id": order_id,
        "razorpay_payment_id": "pay_test_7890",
        "razorpay_signature": "sim_sig_valid_test_signature"
    })

    booking_data = client.get(f"/api/bookings/{booking_id}").json()
    ticket = booking_data["tickets"][0]
    raw_token = ticket["qr_token_raw"]

    # 1. Verify QR token pre-check
    verify_res = client.post("/api/qr/verify", json={"qr_token": raw_token})
    assert verify_res.status_code == 200
    assert verify_res.json()["status"] == "VALID"
    assert verify_res.json()["valid"] is True

    # Login staff
    staff_user = db_session.query(User).filter(User.role == "CHECKIN_STAFF").first()
    staff_token = create_access_token({"sub": str(staff_user.id), "role": staff_user.role, "email": staff_user.email})

    headers = {"Authorization": f"Bearer {staff_token}"}

    # 2. Check in for the FIRST time -> MUST SUCCEED
    checkin_1 = client.post("/api/qr/checkin", json={"qr_token": raw_token}, headers=headers)
    assert checkin_1.status_code == 200
    assert checkin_1.json()["success"] is True
    assert checkin_1.json()["status"] == "SUCCESS"

    # 3. Verify QR again -> Status must now be USED
    verify_after = client.post("/api/qr/verify", json={"qr_token": raw_token})
    assert verify_after.status_code == 200
    assert verify_after.json()["status"] == "USED"
    assert verify_after.json()["valid"] is False

    # 4. Check in for the SECOND time (Duplicate entry attempt) -> MUST BE REJECTED (409 Conflict)
    checkin_2 = client.post("/api/qr/checkin", json={"qr_token": raw_token}, headers=headers)
    assert checkin_2.status_code == 409
    assert "TICKET ALREADY USED" in checkin_2.json()["detail"]

def test_invalid_qr_token_rejected(client):
    response = client.post("/api/qr/verify", json={"qr_token": "FAKE_TOKEN_XYZ_123"})
    assert response.status_code == 200
    assert response.json()["status"] == "INVALID"
    assert response.json()["valid"] is False

def test_owner_notification_and_email_tracking(client, db_session):
    # Book a ticket
    order_res = client.post("/api/payments/create-order", json={
        "customer_name": "Vinay Booker",
        "email": "vinay18744@gmail.com",
        "phone": "+919876543210",
        "ticket_count": 3
    })
    assert order_res.status_code == 200
    booking_id = order_res.json()["booking_id"]
    order_id = order_res.json()["razorpay_order_id"]

    # Verify payment
    verify_res = client.post("/api/payments/verify", json={
        "booking_id": booking_id,
        "razorpay_order_id": order_id,
        "razorpay_payment_id": "pay_test_owner_notification",
        "razorpay_signature": "sim_sig_valid_test_signature"
    })
    assert verify_res.status_code == 200

    # Fetch booking
    booking = client.get(f"/api/bookings/{booking_id}").json()
    assert booking["booking_id"] == booking_id
    assert booking["ticket_count"] == 3
    # Check that email tracking fields exist
    assert "email_status" in booking

def test_admin_settings_owner_config_and_test_email(client, db_session):
    # Super admin token
    admin_user = db_session.query(User).filter(User.role == "SUPER_ADMIN").first()
    admin_token = create_access_token({"sub": str(admin_user.id), "role": admin_user.role, "email": admin_user.email})
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Fetch settings
    settings_res = client.get("/api/admin/settings", headers=headers)
    assert settings_res.status_code == 200
    settings_data = settings_res.json()
    assert settings_data["owner_notification_email"] in ["vinay18744@gmail.com", "Samaymadhyastha2005@gmail.com"]
    assert "smtp_host" in settings_data

    # Update settings
    update_res = client.put("/api/admin/settings", json={
        "owner_notification_email": "vinay18744@gmail.com",
        "owner_notification_phone": "+91 99999 88888",
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587
    }, headers=headers)
    assert update_res.status_code == 200
    assert update_res.json()["owner_notification_phone"] == "+91 99999 88888"

    # Test email endpoint
    test_res = client.post("/api/admin/test-email", json={"to_email": "vinay18744@gmail.com"}, headers=headers)
    assert test_res.status_code == 200
    data = test_res.json()
    assert "success" in data

    # Recent notifications
    notif_res = client.get("/api/admin/notifications/recent", headers=headers)
    assert notif_res.status_code == 200
    assert isinstance(notif_res.json(), list)

