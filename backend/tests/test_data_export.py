import os
import sys
import uuid
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app, init_db_defaults
from app.database import SessionLocal
from app.models.user import User
from app.models.booking import Booking
from app.models.payment import Payment
from app.models.ticket import Ticket
from app.models.checkin import CheckIn
from app.models.ticket_phase import TicketPhase
from app.utils.security import create_access_token
from app.services.export_service import sanitize_csv_cell

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_export_env():
    init_db_defaults()

@pytest.fixture
def admin_headers():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.role.in_(["ADMIN", "SUPER_ADMIN"])).first()
        if not user:
            user = User(
                email="export_admin@test.local",
                name="Export Admin",
                password_hash="fakehash",
                role="ADMIN",
                is_active=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        token = create_access_token({"sub": str(user.id), "email": user.email, "role": user.role})
        return {"Authorization": f"Bearer {token}"}
    finally:
        db.close()

@pytest.fixture
def staff_headers():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.role.in_(["CHECKIN_STAFF", "STAFF"])).first()
        if not user:
            user = User(
                email="export_staff@test.local",
                name="Export Staff",
                password_hash="fakehash",
                role="CHECKIN_STAFF",
                is_active=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        token = create_access_token({"sub": str(user.id), "email": user.email, "role": user.role})
        return {"Authorization": f"Bearer {token}"}
    finally:
        db.close()

def test_sanitize_csv_cell_formula_injection():
    """Verify that dangerous CSV formula characters are neutralized by prepending single quote."""
    assert sanitize_csv_cell("=cmd|' /C calc'!A0") == "'=cmd|' /C calc'!A0"
    assert sanitize_csv_cell("+1234567890") == "'+1234567890"
    assert sanitize_csv_cell("-SOMECMD()") == "'-SOMECMD()"
    assert sanitize_csv_cell("@SUM(A1:A10)") == "'@SUM(A1:A10)"
    assert sanitize_csv_cell("\tTABBED") == "'\tTABBED"
    assert sanitize_csv_cell("\rRETURN") == "'\rRETURN"

    # Numeric and harmless values should NOT be mangled
    assert sanitize_csv_cell(599) == 599
    assert sanitize_csv_cell(599.0) == 599.0
    assert sanitize_csv_cell(True) is True
    assert sanitize_csv_cell(None) == ""
    assert sanitize_csv_cell("Harmless Text") == "Harmless Text"

def test_export_endpoints_require_admin_auth(staff_headers):
    """Verify that unauthenticated and staff users are rejected from exporting data."""
    endpoints = [
        "/api/admin/export/bookings",
        "/api/admin/export/payments",
        "/api/admin/export/tickets",
        "/api/admin/export/checkins",
        "/api/admin/export/offers-inventory",
        "/api/admin/export/users?confirm=true"
    ]

    for ep in endpoints:
        # Unauthenticated -> 401
        res_no_auth = client.get(ep)
        assert res_no_auth.status_code == 401, f"Expected 401 for unauthenticated on {ep}"

        # Staff -> 403 Forbidden
        res_staff = client.get(ep, headers=staff_headers)
        assert res_staff.status_code == 403, f"Expected 403 for staff on {ep}"

def test_export_bookings_csv(admin_headers):
    """Verify bookings CSV export returns valid UTF-8 BOM CSV with proper columns."""
    db = SessionLocal()
    try:
        bid = f"GN-2026-EXP-{uuid.uuid4().hex[:6]}"
        b = Booking(
            booking_id=bid,
            customer_name="=Exploit Tester",
            email="exploit@test.com",
            phone="+919876543210",
            ticket_count=1,
            ticket_price=599.0,
            amount=599.0,
            payment_status="PAID",
            booking_status="CONFIRMED"
        )
        db.add(b)
        db.commit()

        res = client.get("/api/admin/export/bookings", headers=admin_headers)
        assert res.status_code == 200
        assert "text/csv" in res.headers["content-type"]
        assert "attachment; filename=" in res.headers["content-disposition"]

        text = res.text
        # Check UTF-8 BOM
        assert text.startswith("\ufeff")
        assert "Booking ID" in text
        assert "Customer Name" in text
        assert "Total Paid (INR)" in text
        # Verify formula injection neutralization on customer name
        assert "'=Exploit Tester" in text
        # Verify phone with leading + is safely quoted
        assert "'+919876543210" in text
    finally:
        db.close()

def test_export_tickets_never_exposes_qr_tokens(admin_headers):
    """Verify tickets CSV export NEVER exports secret raw QR tokens or hashes."""
    db = SessionLocal()
    try:
        bid = f"GN-2026-TKTEXP-{uuid.uuid4().hex[:6]}"
        secret_raw_token = f"SECRET_RAW_TOKEN_{uuid.uuid4().hex}"
        secret_hash = f"SECRET_HASH_{uuid.uuid4().hex}"

        b = Booking(
            booking_id=bid,
            customer_name="Secure Attendee",
            email="sec@test.com",
            phone="9876543210",
            ticket_count=1,
            ticket_price=599.0,
            amount=599.0,
            payment_status="PAID",
            booking_status="CONFIRMED"
        )
        db.add(b)
        db.commit()
        db.refresh(b)

        t = Ticket(
            ticket_id=f"TKT-{uuid.uuid4().hex[:8]}",
            booking_id=b.id,
            customer_name="Secure Attendee",
            qr_token_raw=secret_raw_token,
            qr_token_hash=secret_hash,
            ticket_status="VALID",
            checkin_status=False
        )
        db.add(t)
        db.commit()

        res = client.get("/api/admin/export/tickets", headers=admin_headers)
        assert res.status_code == 200
        text = res.text
        assert "Ticket ID" in text
        assert "Checked In" in text
        # Raw token and hash MUST NEVER appear in output
        assert secret_raw_token not in text
        assert secret_hash not in text
        assert "qr_token" not in text.lower()
    finally:
        db.close()

def test_export_users_never_exposes_passwords(admin_headers):
    """Verify users CSV export strictly excludes password_hash and requires confirmation."""
    db = SessionLocal()
    try:
        # Without confirmation, if not super admin, must be rejected
        user = db.query(User).filter(User.role == "ADMIN").first()
        if user:
            token = create_access_token({"sub": str(user.id), "email": user.email, "role": "ADMIN"})
            headers = {"Authorization": f"Bearer {token}"}
            res_no_confirm = client.get("/api/admin/export/users?confirm=false", headers=headers)
            assert res_no_confirm.status_code == 403

        # With confirm=true, export succeeds but password_hash must NEVER be present
        res = client.get("/api/admin/export/users?confirm=true", headers=admin_headers)
        assert res.status_code == 200
        text = res.text
        assert "User ID" in text
        assert "Role" in text
        assert "password" not in text.lower()
        assert "hash" not in text.lower()
    finally:
        db.close()

def test_export_offers_inventory(admin_headers):
    """Verify offers and inventory CSV export."""
    res = client.get("/api/admin/export/offers-inventory", headers=admin_headers)
    assert res.status_code == 200
    text = res.text
    assert "Category" in text
    assert "Total Inventory" in text
    assert "EARLY_BIRD" in text

def test_export_payments_csv(admin_headers):
    """Verify payments CSV export includes payment fields, booking link, and no raw response secrets."""
    db = SessionLocal()
    try:
        bid = f"GN-2026-PAYEXP-{uuid.uuid4().hex[:6]}"
        b = Booking(
            booking_id=bid,
            customer_name="Payment Tester",
            email="pay@test.com",
            phone="9876543210",
            ticket_count=1,
            ticket_price=599.0,
            amount=599.0,
            payment_status="PAID",
            booking_status="CONFIRMED"
        )
        db.add(b)
        db.commit()
        db.refresh(b)

        p = Payment(
            payment_id=f"PAY-{uuid.uuid4().hex[:8]}",
            booking_id=b.id,
            payment_method="RAZORPAY",
            amount=599.0,
            currency="INR",
            payment_status="PAID",
            razorpay_order_id=f"order_test_{uuid.uuid4().hex[:8]}",
            razorpay_payment_id=f"pay_test_{uuid.uuid4().hex[:8]}",
            raw_response="{\"secret_internal_data\": 12345}"
        )
        db.add(p)
        db.commit()

        res = client.get("/api/admin/export/payments", headers=admin_headers)
        assert res.status_code == 200
        text = res.text
        assert "Payment ID" in text
        assert "Amount (INR)" in text
        assert "Payment Method" in text
        assert "secret_internal_data" not in text
    finally:
        db.close()

def test_export_checkins_csv(admin_headers):
    """Verify check-ins CSV export."""
    res = client.get("/api/admin/export/checkins", headers=admin_headers)
    assert res.status_code == 200
    text = res.text
    assert "Check-in ID" in text
    assert "Attendee Name" in text
    assert "Result" in text

