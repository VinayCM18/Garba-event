import sys
import os
import uuid
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from fastapi.testclient import TestClient
from app.main import app, init_db_defaults
from app.database import get_db, SessionLocal
from app.models.booking import Booking
from app.models.ticket import Ticket
from app.models.event_setting import EventSetting
from app.services.booking_service import booking_service
from app.services.email_service import EmailService

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    init_db_defaults()

client = TestClient(app)

def mock_razorpay_order_create():
    """Helper context manager to mock Razorpay order creation in unit tests."""
    mock_client = MagicMock()
    mock_instance = MagicMock()
    mock_instance.order.create.side_effect = lambda *args, **kwargs: {
        "id": f"order_mock_{uuid.uuid4().hex[:8]}",
        "amount": (kwargs.get("data") or {}).get("amount", 10000) if isinstance(kwargs.get("data"), dict) else 10000,
        "currency": "INR",
        "status": "created"
    }
    mock_client.return_value = mock_instance
    return patch("razorpay.Client", mock_client)

def test_public_config_offers_structure():
    """Verify that public config returns NAVRANG 2026 offers array with authoritative prices."""
    response = client.get("/api/bookings/public-config")
    assert response.status_code == 200
    data = response.json()
    assert "offers" in data
    offers = {o["id"]: o for o in data["offers"]}

    # Early Bird Stag (Sold Out)
    assert "EARLY_BIRD_STAG" in offers
    assert offers["EARLY_BIRD_STAG"]["price"] == 599.0
    assert offers["EARLY_BIRD_STAG"]["per_unit_passes"] == 1
    assert offers["EARLY_BIRD_STAG"]["type"] == "STAG"
    assert offers["EARLY_BIRD_STAG"]["phase_status"] == "SOLD_OUT"
    assert offers["EARLY_BIRD_STAG"]["is_purchasable"] is False

    # Early Bird Group of 10 (Sold Out)
    assert "EARLY_BIRD_GROUP_10" in offers
    assert offers["EARLY_BIRD_GROUP_10"]["price"] == 4999.0
    assert offers["EARLY_BIRD_GROUP_10"]["per_unit_passes"] == 10
    assert offers["EARLY_BIRD_GROUP_10"]["type"] == "GROUP"
    assert offers["EARLY_BIRD_GROUP_10"]["phase_status"] == "SOLD_OUT"
    assert offers["EARLY_BIRD_GROUP_10"]["is_purchasable"] is False

    # Early Bird Couple (Sold Out)
    assert "EARLY_BIRD_COUPLE" in offers
    assert offers["EARLY_BIRD_COUPLE"]["price"] == 999.0
    assert offers["EARLY_BIRD_COUPLE"]["per_unit_passes"] == 2
    assert offers["EARLY_BIRD_COUPLE"]["type"] == "COUPLE"
    assert offers["EARLY_BIRD_COUPLE"]["phase_status"] == "SOLD_OUT"
    assert offers["EARLY_BIRD_COUPLE"]["is_purchasable"] is False

    # Phase 1 Stag (Active)
    assert "PHASE_1_STAG" in offers
    assert offers["PHASE_1_STAG"]["price"] == 799.0
    assert offers["PHASE_1_STAG"]["type"] == "STAG"
    assert offers["PHASE_1_STAG"]["phase_status"] == "ACTIVE"
    assert offers["PHASE_1_STAG"]["is_purchasable"] is True

    # Phase 1 Group of 10 (Active)
    assert "PHASE_1_GROUP_10" in offers
    assert offers["PHASE_1_GROUP_10"]["price"] == 6499.0
    assert offers["PHASE_1_GROUP_10"]["type"] == "GROUP"
    assert offers["PHASE_1_GROUP_10"]["phase_status"] == "ACTIVE"
    assert offers["PHASE_1_GROUP_10"]["is_purchasable"] is True

    # Phase 1 Couple (Sold Out)
    assert "PHASE_1_COUPLE" in offers
    assert offers["PHASE_1_COUPLE"]["price"] == 1299.0
    assert offers["PHASE_1_COUPLE"]["type"] == "COUPLE"
    assert offers["PHASE_1_COUPLE"]["phase_status"] == "SOLD_OUT"
    assert offers["PHASE_1_COUPLE"]["is_purchasable"] is False

    # Kids 5-12
    assert "KIDS_5_12" in offers
    assert offers["KIDS_5_12"]["price"] == 300.0
    assert offers["KIDS_5_12"]["per_unit_passes"] == 1
    assert offers["KIDS_5_12"]["type"] == "KIDS"
    assert offers["KIDS_5_12"]["phase_status"] == "ACTIVE"
    assert offers["KIDS_5_12"]["is_purchasable"] is True
    assert offers["KIDS_5_12"]["requires_id_proof"] is True

def test_phase_1_stag_pricing_and_order():
    """Verify Phase 1 Stag calculation and authoritative order creation."""
    calc_res = client.get("/api/payments/calculate", params={
        "offer_id": "PHASE_1_STAG",
        "quantity": 1
    })
    assert calc_res.status_code == 200
    calc_data = calc_res.json()
    assert calc_data["ticket_subtotal"] == 799.0
    assert calc_data["total_amount"] == 799.0
    assert calc_data["passes_count"] == 1

    # Create Order
    with mock_razorpay_order_create():
        order_res = client.post("/api/payments/create-order", json={
            "customer_name": "Rohan Patel",
            "email": "rohan.patel@example.com",
            "phone": "9876543210",
            "offer_id": "PHASE_1_STAG",
            "quantity": 1
        })
    assert order_res.status_code == 200
    order_data = order_res.json()
    assert order_data["amount"] == 799.0
    assert order_data["passes_count"] == 1

def test_phase_1_group_of_10_pricing_and_order():
    """Verify Phase 1 Group of 10 is ₹6,499 and allocates 10 passes."""
    calc_res = client.get("/api/payments/calculate", params={
        "offer_id": "PHASE_1_GROUP_10",
        "quantity": 1
    })
    assert calc_res.status_code == 200
    calc_data = calc_res.json()
    assert calc_data["ticket_subtotal"] == 6499.0
    assert calc_data["total_amount"] == 6499.0
    assert calc_data["passes_count"] == 10

    # Create Order
    with mock_razorpay_order_create():
        order_res = client.post("/api/payments/create-order", json={
            "customer_name": "Garba Squad Captain",
            "email": "garbasquad@example.com",
            "phone": "9876543211",
            "offer_id": "PHASE_1_GROUP_10",
            "quantity": 1
        })
    assert order_res.status_code == 200
    order_data = order_res.json()
    assert order_data["amount"] == 6499.0
    assert order_data["passes_count"] == 10
    assert order_data["ticket_count"] == 10

def test_phase_1_couple_is_sold_out_and_rejected():
    """Verify Phase 1 Couple calculations and new order creation are rejected with 400 Bad Request."""
    calc_res = client.get("/api/payments/calculate", params={
        "offer_id": "PHASE_1_COUPLE",
        "quantity": 1
    })
    assert calc_res.status_code == 400
    assert "Phase 1 Couple Entry is sold out" in calc_res.json()["detail"]

    # Attempt to Create Order must fail with 400
    with mock_razorpay_order_create():
        order_res = client.post("/api/payments/create-order", json={
            "customer_name": "Aarav and Ananya",
            "email": "aarav.ananya@example.com",
            "phone": "9876543212",
            "offer_id": "PHASE_1_COUPLE",
            "quantity": 1
        })
    assert order_res.status_code == 400
    assert "Phase 1 Couple Entry is sold out" in order_res.json()["detail"]

def test_kids_pricing_and_validation():
    """Verify Kids 5-12 is ₹300, requires child name and valid age (5-12)."""
    calc_res = client.get("/api/payments/calculate", params={
        "offer_id": "KIDS_5_12",
        "quantity": 1
    })
    assert calc_res.status_code == 200
    assert calc_res.json()["ticket_subtotal"] == 300.0

    # Missing child name should fail
    fail_res = client.post("/api/payments/create-order", json={
        "customer_name": "Parent Name",
        "email": "parent@example.com",
        "phone": "9876543213",
        "offer_id": "KIDS_5_12",
        "quantity": 1
    })
    assert fail_res.status_code == 400
    detail_lower = fail_res.json()["detail"].lower()
    assert "child" in detail_lower and "name" in detail_lower

    # Invalid child age (<5) should fail
    fail_age = client.post("/api/payments/create-order", json={
        "customer_name": "Parent Name",
        "email": "parent@example.com",
        "phone": "9876543213",
        "offer_id": "KIDS_5_12",
        "quantity": 1,
        "child_name": "Little Toddler",
        "child_age": 3
    })
    assert fail_age.status_code == 400
    assert "5 to 12" in fail_age.json()["detail"] or "5 and 12" in fail_age.json()["detail"]

    # Valid child order
    with mock_razorpay_order_create():
        order_res = client.post("/api/payments/create-order", json={
            "customer_name": "Meera Joshi (Parent)",
            "email": "meera.joshi@example.com",
            "phone": "9876543214",
            "offer_id": "KIDS_5_12",
            "quantity": 1,
            "child_name": "Vihaan Joshi",
            "child_age": 8
        })
    assert order_res.status_code == 200
    data = order_res.json()
    assert data["amount"] in (300.0, 307.08)
    assert data["child_name"] == "Vihaan Joshi"
    assert data["child_age"] == 8

def test_locked_phase_1_offers_rejected():
    """Early Bird offers must be rejected as sold out."""
    for offer_id in ["EARLY_BIRD_STAG", "EARLY_BIRD_GROUP_10", "EARLY_BIRD_COUPLE"]:
        calc_res = client.get("/api/payments/calculate", params={
            "offer_id": offer_id,
            "quantity": 1
        })
        assert calc_res.status_code == 400
        assert "Early Bird tickets are sold out. Please select Phase 1." in calc_res.json()["detail"]

        order_res = client.post("/api/payments/create-order", json={
            "customer_name": "Late Booker",
            "email": "late@example.com",
            "phone": "9876543215",
            "offer_id": offer_id,
            "quantity": 1
        })
        assert order_res.status_code == 400
        assert "Early Bird tickets are sold out. Please select Phase 1." in order_res.json()["detail"]

def test_frontend_cannot_manipulate_price():
    """Client cannot send a manipulated amount; backend authoritatively sets it."""
    with mock_razorpay_order_create():
        order_res = client.post("/api/payments/create-order", json={
            "customer_name": "Price Manipulator",
            "email": "manipulate@example.com",
            "phone": "9876543216",
            "offer_id": "PHASE_1_STAG",
            "quantity": 1,
            "amount": 1.0,  # manipulated amount ignored
            "ticket_price": 1.0
        })
    assert order_res.status_code == 200
    assert order_res.json()["amount"] == 799.0

def test_group_of_10_generates_10_individual_qr_tickets():
    """Confirming a Group of 10 booking generates 10 distinct QR tickets."""
    with mock_razorpay_order_create():
        order_res = client.post("/api/payments/create-order", json={
            "customer_name": "Navratri Dance Troupe",
            "email": "dancetroupe@example.com",
            "phone": "9876543217",
            "offer_id": "PHASE_1_GROUP_10",
            "quantity": 1
        })
    assert order_res.status_code == 200
    booking_id = order_res.json()["booking_id"]

    # Confirm booking via booking_service directly
    db = SessionLocal()
    try:
        confirmed = booking_service.confirm_booking_and_generate_tickets(
            booking_id=booking_id,
            razorpay_payment_id="pay_test_group10",
            payment_method="RAZORPAY",
            db=db
        )
        assert confirmed.booking_status == "CONFIRMED"
        assert confirmed.ticket_count == 10
        tickets = confirmed.tickets
        assert len(tickets) == 10

        # All 10 tickets must have unique ticket IDs and unique QR tokens
        ticket_ids = {t.ticket_id for t in tickets}
        qr_tokens = {t.qr_token_raw for t in tickets}
        assert len(ticket_ids) == 10
        assert len(qr_tokens) == 10
    finally:
        db.close()

def test_couple_generates_2_individual_qr_tickets():
    """Confirming a pre-existing Couple booking generates 2 distinct QR tickets."""
    db = SessionLocal()
    try:
        unique_id = uuid.uuid4().hex[:8]
        booking = Booking(
            booking_id=f"GN-2026-CPL-{unique_id}",
            customer_name="Kavita and Siddharth",
            email="kavita.sid@example.com",
            phone="9876543218",
            ticket_count=2,
            ticket_price=649.5,
            amount=1299.0,
            offer_id="PHASE_1_COUPLE",
            offer_title="Phase 1 — Couple Entry",
            ticket_phase="PHASE_1",
            payment_status="PENDING",
            booking_status="PENDING"
        )
        db.add(booking)
        db.commit()

        confirmed = booking_service.confirm_booking_and_generate_tickets(
            booking_id=booking.booking_id,
            razorpay_payment_id=f"pay_couple_{unique_id}",
            payment_method="RAZORPAY",
            db=db
        )
        assert confirmed.ticket_count == 2
        tickets = confirmed.tickets
        assert len(tickets) == 2
        assert len({t.ticket_id for t in tickets}) == 2
        assert len({t.qr_token_raw for t in tickets}) == 2
    finally:
        db.close()

def test_email_template_contains_offer_and_child_info():
    """EmailService confirmation HTML displays the selected offer and child information."""
    db = SessionLocal()
    try:
        event_setting = db.query(EventSetting).first() or EventSetting()
        mock_booking = Booking(
            booking_id="GN-2026-TESTKIDS",
            customer_name="Pooja Shah",
            email="pooja@example.com",
            phone="9876543219",
            ticket_count=1,
            ticket_price=300.0,
            amount=300.0,
            currency="INR",
            offer_id="KIDS_5_12",
            offer_title="Kids (5–12 years)",
            child_name="Aanya Shah",
            child_age=6,
            payment_status="PAID"
        )
        html = EmailService.render_confirmation_html(mock_booking, event_setting, "data:image/png;base64,mockqr")
        assert "Kids (5–12 years)" in html
        assert "Aanya Shah" in html
        assert "Aadhaar card / valid ID proof required at entry" in html
    finally:
        db.close()
