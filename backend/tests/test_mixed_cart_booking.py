import pytest
import os
import sys
import json
import uuid
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SessionLocal
from app.models.booking import Booking
from app.models.booking_item import BookingItem
from app.models.ticket import Ticket
from app.models.event_setting import EventSetting
from app.models.ticket_phase import TicketPhase
from app.models.offers import calculate_cart_pricing, get_offer_by_id
from app.services.booking_service import booking_service
from fastapi import HTTPException

@pytest.fixture(autouse=True)
def setup_test_data():
    os.environ["RAZORPAY_KEY_ID"] = "rzp_test_abcdef123456"
    os.environ["RAZORPAY_KEY_SECRET"] = "testsecret123456"
    os.environ["RAZORPAY_MODE"] = "TEST"
    db = SessionLocal()
    try:
        setting = db.query(EventSetting).first()
        if not setting:
            setting = EventSetting(
                event_name="NAVRANG 2026",
                ticket_price=599.0,
                total_capacity=5000,
                booking_open=True,
                payment_method="RAZORPAY"
            )
            db.add(setting)
        else:
            setting.event_name = "NAVRANG 2026"
            setting.ticket_price = 599.0
            setting.total_capacity = 5000
            setting.booking_open = True
            setting.payment_method = "RAZORPAY"

        # Ensure Early Bird phase is active
        eb = db.query(TicketPhase).filter(TicketPhase.phase_code == "EARLY_BIRD").first()
        if not eb:
            eb = TicketPhase(
                phase_code="EARLY_BIRD",
                name="Early Bird",
                price=599.0,
                status="ACTIVE",
                total_inventory=2500,
                sold_count=0
            )
            db.add(eb)
        else:
            eb.status = "ACTIVE"

        # Ensure Phase 1 is locked
        p1 = db.query(TicketPhase).filter(TicketPhase.phase_code == "PHASE_1").first()
        if not p1:
            p1 = TicketPhase(
                phase_code="PHASE_1",
                name="Phase 1",
                price=799.0,
                status="LOCKED",
                total_inventory=2500,
                sold_count=0
            )
            db.add(p1)
        else:
            p1.status = "LOCKED"

        db.commit()
    finally:
        db.close()

def test_cart_pricing_authoritative_calculation():
    """Verify authoritative backend calculation for mixed cart examples from prompt:
    2 × Group of 10 = ₹9,998 (20 passes)
    3 × Couple      = ₹2,997 (6 passes)
    2 × Stag        = ₹1,198 (2 passes)
    Total           = ₹14,193 (28 passes)
    """
    db = SessionLocal()
    try:
        cart = [
            {"offer_id": "EARLY_BIRD_GROUP_10", "quantity": 2},
            {"offer_id": "EARLY_BIRD_COUPLE", "quantity": 3},
            {"offer_id": "EARLY_BIRD_STAG", "quantity": 2},
        ]
        pricing = calculate_cart_pricing(items=cart, db=db)
        assert pricing["total_amount"] == 14193.0
        assert pricing["amount"] == 14193.0
        assert pricing["total_passes"] == 28
        assert pricing["ticket_count"] == 28
        assert pricing["payment_fee"] == 0.0
        assert pricing["gst_amount"] == 0.0
        assert pricing["is_mixed_cart"] is True
        assert len(pricing["items"]) == 3

        # Verify line subtotals
        assert pricing["items"][0]["line_total"] == 9998.0
        assert pricing["items"][0]["total_passes"] == 20
        assert pricing["items"][1]["line_total"] == 2997.0
        assert pricing["items"][1]["total_passes"] == 6
        assert pricing["items"][2]["line_total"] == 1198.0
        assert pricing["items"][2]["total_passes"] == 2
    finally:
        db.close()

def test_cart_pricing_with_kids():
    """Verify cart combining Group, Couple, and Kids:
    1 × Group of 10  = ₹4,999 (10 passes)
    1 × Couple       = ₹999   (2 passes)
    2 × Kids (5–12)  = ₹600   (2 passes)
    Total            = ₹6,598 (14 passes)
    """
    db = SessionLocal()
    try:
        cart = [
            {"offer_id": "EARLY_BIRD_GROUP_10", "quantity": 1},
            {"offer_id": "EARLY_BIRD_COUPLE", "quantity": 1},
            {"offer_id": "KIDS_5_12", "quantity": 2},
        ]
        pricing = calculate_cart_pricing(items=cart, db=db)
        assert pricing["total_amount"] == 6598.0
        assert pricing["total_passes"] == 14
        assert pricing["kids_count"] == 2
    finally:
        db.close()

def test_locked_phase_rejected_in_cart():
    """Verify that adding a locked offer to cart raises HTTP 400."""
    db = SessionLocal()
    try:
        cart = [
            {"offer_id": "EARLY_BIRD_STAG", "quantity": 1},
            {"offer_id": "PHASE_1_STAG", "quantity": 1},  # Locked phase
        ]
        with pytest.raises(HTTPException) as exc:
            calculate_cart_pricing(items=cart, db=db)
        assert exc.value.status_code == 400
        assert "locked" in str(exc.value.detail).lower()
    finally:
        db.close()

def test_kids_validation_multiple_records():
    """Verify that 2 kids tickets require exactly 2 child records with ages 5 to 12."""
    db = SessionLocal()
    try:
        cart = [
            {"offer_id": "EARLY_BIRD_STAG", "quantity": 1},
            {"offer_id": "KIDS_5_12", "quantity": 2},
        ]

        # Case 1: Missing child records
        with pytest.raises(HTTPException) as exc1:
            booking_service.initiate_order(
                customer_name="Aarav Sharma",
                email="aarav@example.com",
                phone="9876543210",
                items=cart,
                children=[],
                db=db
            )
        assert exc1.value.status_code == 400

        # Case 2: One child too young (< 5)
        with pytest.raises(HTTPException) as exc2:
            booking_service.initiate_order(
                customer_name="Aarav Sharma",
                email="aarav@example.com",
                phone="9876543210",
                items=cart,
                children=[
                    {"name": "Anaya", "age": 7},
                    {"name": "Advait", "age": 4} # invalid
                ],
                db=db
            )
        assert exc2.value.status_code == 400
        assert "5 and 12" in str(exc2.value.detail)

        # Case 3: Valid children (ages 7 and 10)
        test_order_id = f"order_cart_test_{uuid.uuid4().hex[:8]}"
        with patch("app.services.payment_providers.razorpay_provider.razorpay.Client") as mock_rzp:
            mock_client = MagicMock()
            mock_client.order.create.return_value = {"id": test_order_id}
            mock_rzp.return_value = mock_client

            booking, order_info = booking_service.initiate_order(
                customer_name="Aarav Sharma",
                email="aarav@example.com",
                phone="9876543210",
                items=cart,
                children=[
                    {"name": "Anaya", "age": 7},
                    {"name": "Advait", "age": 10}
                ],
                db=db
            )
            assert booking.amount == 599.0 + 600.0  # ₹1,199
            assert booking.ticket_count == 3  # 1 Stag + 2 Kids passes
            assert len(booking.items) == 2
            assert order_info["razorpay_order_id"] == test_order_id
    finally:
        db.close()

def test_full_mixed_cart_booking_order_and_tickets():
    """Verify full end-to-end flow:
    Cart: 2 Group of 10 + 3 Couple + 2 Stag
    1. Creates ONE booking with total passes = 28 and amount = ₹14,193
    2. Creates ONE Razorpay order for 1419300 paise
    3. Confirms booking and generates 28 unique valid tickets with unique cryptographic QR tokens.
    """
    db = SessionLocal()
    try:
        cart = [
            {"offer_id": "EARLY_BIRD_GROUP_10", "quantity": 2},
            {"offer_id": "EARLY_BIRD_COUPLE", "quantity": 3},
            {"offer_id": "EARLY_BIRD_STAG", "quantity": 2},
        ]

        full_order_id = f"order_mixed_cart_{uuid.uuid4().hex[:8]}"
        with patch("app.services.payment_providers.razorpay_provider.razorpay.Client") as mock_rzp:
            mock_client = MagicMock()
            created_order_data = {}

            def fake_create(data):
                nonlocal created_order_data
                created_order_data = data
                return {"id": full_order_id}

            mock_client.order.create.side_effect = fake_create
            mock_rzp.return_value = mock_client

            booking, order_info = booking_service.initiate_order(
                customer_name="Priya Patel",
                email="priya@example.com",
                phone="9876543210",
                items=cart,
                db=db
            )

            # 1. Order verification
            assert booking.amount == 14193.0
            assert booking.ticket_count == 28
            assert created_order_data["amount"] == 1419300  # 14,193 * 100 paise
            assert created_order_data["currency"] == "INR"
            assert created_order_data["notes"]["ticket_count"] == "28"

            # Verify BookingItems
            items = db.query(BookingItem).filter(BookingItem.booking_id == booking.id).all()
            assert len(items) == 3
            assert sum(it.total_passes for it in items) == 28
            assert sum(it.line_total for it in items) == 14193.0

            # 2. Payment confirmation and ticket generation
            with patch("app.services.email_service.email_service.send_confirmation_email"), \
                 patch("app.services.email_service.email_service.send_owner_notification"):
                confirmed_booking = booking_service.confirm_booking_and_generate_tickets(
                    booking_id=booking.booking_id,
                    razorpay_payment_id=f"pay_mixed_cart_{uuid.uuid4().hex[:8]}",
                    razorpay_signature="fake_sig",
                    db=db,
                    payment_method="RAZORPAY"
                )

                assert confirmed_booking.booking_status == "CONFIRMED"
                assert confirmed_booking.payment_status == "PAID"

                # Verify 28 tickets generated
                tickets = db.query(Ticket).filter(Ticket.booking_id == booking.id).all()
                assert len(tickets) == 28

                # Verify each ticket is unique
                ticket_ids = {t.ticket_id for t in tickets}
                assert len(ticket_ids) == 28

                # Verify each QR token is unique
                qr_tokens = {t.qr_token_raw for t in tickets}
                assert len(qr_tokens) == 28

                # Verify all tickets are VALID
                assert all(t.ticket_status == "VALID" for t in tickets)
    finally:
        db.close()
