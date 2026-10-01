import os
import sys
import uuid
import hmac
import hashlib
import json
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app, init_db_defaults
from app.config import settings
from app.database import get_db, SessionLocal
from app.models.offers import OFFER_DEFINITIONS, get_all_offers, calculate_offer_pricing
from app.models.booking import Booking
from app.models.event_setting import EventSetting
from app.models.ticket_phase import TicketPhase
from app.models.user import User
from app.services.email_service import EmailService
from app.services.payment_service import payment_service
from app.services.booking_service import booking_service

@pytest.fixture(scope="module", autouse=True)
def setup_master_env():
    init_db_defaults()

client = TestClient(app)

def test_01_seven_authoritative_offers():
    """Verify all 7 authoritative NAVRANG 2026 offers exist with exact prices, passes, and types."""
    assert len(OFFER_DEFINITIONS) == 7

    # 1. EARLY_BIRD_STAG
    eb_stag = OFFER_DEFINITIONS["EARLY_BIRD_STAG"]
    assert eb_stag["price_per_unit"] == 599.0
    assert eb_stag["passes_per_unit"] == 1
    assert eb_stag["type"] == "STAG"
    assert eb_stag["phase_code"] == "EARLY_BIRD"

    # 2. EARLY_BIRD_GROUP_10
    eb_group = OFFER_DEFINITIONS["EARLY_BIRD_GROUP_10"]
    assert eb_group["price_per_unit"] == 4999.0
    assert eb_group["passes_per_unit"] == 10
    assert eb_group["type"] == "GROUP"
    assert eb_group["phase_code"] == "EARLY_BIRD"
    assert "991" in eb_group["badge"]

    # 3. EARLY_BIRD_COUPLE
    eb_couple = OFFER_DEFINITIONS["EARLY_BIRD_COUPLE"]
    assert eb_couple["price_per_unit"] == 999.0
    assert eb_couple["passes_per_unit"] == 2
    assert eb_couple["type"] == "COUPLE"
    assert eb_couple["phase_code"] == "EARLY_BIRD"

    # 4. PHASE_1_STAG
    p1_stag = OFFER_DEFINITIONS["PHASE_1_STAG"]
    assert p1_stag["price_per_unit"] == 799.0
    assert p1_stag["passes_per_unit"] == 1
    assert p1_stag["type"] == "STAG"
    assert p1_stag["phase_code"] == "PHASE_1"

    # 5. PHASE_1_GROUP_10
    p1_group = OFFER_DEFINITIONS["PHASE_1_GROUP_10"]
    assert p1_group["price_per_unit"] == 6799.0
    assert p1_group["passes_per_unit"] == 10
    assert p1_group["type"] == "GROUP"
    assert p1_group["phase_code"] == "PHASE_1"

    # 6. PHASE_1_COUPLE
    p1_couple = OFFER_DEFINITIONS["PHASE_1_COUPLE"]
    assert p1_couple["price_per_unit"] == 1399.0
    assert p1_couple["passes_per_unit"] == 2
    assert p1_couple["type"] == "COUPLE"
    assert p1_couple["phase_code"] == "PHASE_1"

    # 7. KIDS_5_12
    kids = OFFER_DEFINITIONS["KIDS_5_12"]
    assert kids["price_per_unit"] == 300.0
    assert kids["passes_per_unit"] == 1
    assert kids["type"] == "KIDS"
    assert kids["requires_id_proof"] is True

def test_02_offer_schema_completeness():
    """Verify backend get_all_offers returns all fields expected by frontend OfferItem."""
    db = SessionLocal()
    try:
        offers = get_all_offers(db)
        required_fields = [
            "id", "phase_code", "phase_name", "phase_status", "type",
            "title", "price", "per_unit_passes", "description", "badge",
            "is_purchasable", "requires_id_proof"
        ]
        for offer in offers:
            for field in required_fields:
                assert field in offer, f"Missing field '{field}' in offer {offer.get('id')}"
                assert offer[field] is not None, f"Field '{field}' is None in offer {offer.get('id')}"
            assert offer["type"] in ("STAG", "GROUP", "COUPLE", "KIDS")
            assert offer["phase_status"] in ("ACTIVE", "LOCKED", "COMING_SOON")
    finally:
        db.close()

def test_03_all_inclusive_pricing():
    """Verify strictly all-inclusive pricing: 599 is strictly 599 with zero fees or taxes added."""
    db = SessionLocal()
    try:
        pricing = calculate_offer_pricing("EARLY_BIRD_STAG", quantity=1, db=db)
        assert pricing["unit_price"] == 599.0
        assert pricing["ticket_subtotal"] == 599.0
        assert pricing["payment_fee"] == 0.0
        assert pricing["gst_amount"] == 0.0
        assert pricing["total_amount"] == 599.0
    finally:
        db.close()

def test_04_group_of_10_savings():
    """Verify Group of 10 subtotal is ₹4,999 and savings calculation equals ₹991."""
    db = SessionLocal()
    try:
        pricing = calculate_offer_pricing("EARLY_BIRD_GROUP_10", quantity=1, db=db)
        assert pricing["unit_price"] == 4999.0
        assert pricing["ticket_subtotal"] == 4999.0
        assert pricing["passes_count"] == 10
        assert pricing["total_amount"] == 4999.0
        # Savings vs 10 individual early bird passes (10 * 599 = 5990)
        savings = (10 * 599.0) - pricing["total_amount"]
        assert savings == 991.0
    finally:
        db.close()

def test_05_kids_age_validation():
    """Verify Kids 5-12 requires child_name and age strictly between 5 and 12."""
    db = SessionLocal()
    try:
        # Age < 5 -> rejected
        with pytest.raises(Exception) as exc1:
            booking_service.initiate_order(
                customer_name="Parent",
                email="parent@test.com",
                phone="9876543210",
                offer_id="KIDS_5_12",
                quantity=1,
                child_name="Baby",
                child_age=4,
                db=db
            )
        assert "5 to 12" in str(exc1.value)

        # Age > 12 -> rejected
        with pytest.raises(Exception) as exc2:
            booking_service.initiate_order(
                customer_name="Parent",
                email="parent@test.com",
                phone="9876543210",
                offer_id="KIDS_5_12",
                quantity=1,
                child_name="Teen",
                child_age=13,
                db=db
            )
        assert "5 to 12" in str(exc2.value)

        # Missing name -> rejected
        with pytest.raises(Exception) as exc3:
            booking_service.initiate_order(
                customer_name="Parent",
                email="parent@test.com",
                phone="9876543210",
                offer_id="KIDS_5_12",
                quantity=1,
                child_name="",
                child_age=8,
                db=db
            )
        assert "full name is required" in str(exc3.value).lower()
    finally:
        db.close()

def test_06_locked_phase_rejected():
    """Verify phase locked offers cannot be calculated or ordered."""
    db = SessionLocal()
    try:
        with pytest.raises(Exception) as exc:
            calculate_offer_pricing("PHASE_1_STAG", quantity=1, db=db)
        assert "locked" in str(exc.value).lower()
    finally:
        db.close()

def test_07_no_predictable_passwords_in_production():
    """Verify that in production, missing or predictable seed passwords raise RuntimeError on startup."""
    with patch.object(settings, "ENVIRONMENT", "production"):
        with patch.dict(os.environ, {"ADMIN_SEED_PASSWORD": "GarbaNight@2026"}):
            with patch("app.main.SessionLocal") as mock_session_factory:
                mock_db = MagicMock()
                # Simulate no user in DB
                mock_db.query.return_value.filter.return_value.first.return_value = None
                mock_session_factory.return_value = mock_db
                with pytest.raises(RuntimeError) as exc:
                    init_db_defaults()
                assert "CRITICAL CONFIGURATION ERROR" in str(exc.value)

def test_08_production_resend_sender_enforcement():
    """Verify that in production, sending from onboarding@resend.dev is strictly rejected."""
    with patch.object(settings, "ENVIRONMENT", "production"):
        config = {
            "resend_api_key": "re_dummy_key_12345",
            "smtp_from_email": "onboarding@resend.dev",
            "smtp_from_name": "NAVRANG 2026"
        }
        with pytest.raises(ValueError) as exc:
            EmailService._dispatch_resend_email(
                to_emails=["test@example.com"],
                subject="Test",
                html_content="<p>Test</p>",
                config=config
            )
        assert "Cannot silently use onboarding@resend.dev in production" in str(exc.value)

def test_09_email_recipients_resolution():
    """Verify email configuration resolves without hardcoded email addresses."""
    db = SessionLocal()
    try:
        with patch.dict(os.environ, {
            "OWNER_NOTIFICATION_EMAIL": "organizer@heritageproduction.online",
            "ADMIN_NOTIFICATION_EMAIL": "organizer@heritageproduction.online"
        }, clear=False):
            cfg = EmailService.get_email_config(db)
            assert cfg["owner_email"] == "organizer@heritageproduction.online"
            assert cfg["admin_email"] == "organizer@heritageproduction.online"
            # Ensure no legacy hardcoded strings
            assert "samaymadhyastha" not in cfg["admin_email"].lower()
    finally:
        db.close()

def test_10_razorpay_canonical_webhook_hmac():
    """Verify canonical /api/payments/webhook validates HMAC signature and handles payment.captured."""
    db = SessionLocal()
    try:
        bid = f"GN-2026-WHSEC-{uuid.uuid4().hex[:6]}"
        oid = f"order_wh_test_{uuid.uuid4().hex[:6]}"
        # Create test booking
        booking = Booking(
            booking_id=bid,
            customer_name="Webhook User",
            email="wh@example.com",
            phone="9876543210",
            ticket_count=1,
            ticket_price=599.0,
            amount=599.0,
            payment_status="PENDING",
            booking_status="PAYMENT_PENDING",
            razorpay_order_id=oid
        )
        db.add(booking)
        db.commit()

        webhook_secret = "test_webhook_secret_key"
        with patch.dict(os.environ, {"RAZORPAY_WEBHOOK_SECRET": webhook_secret}):
            payload = {
                "event": "payment.captured",
                "payload": {
                    "payment": {
                        "entity": {
                            "id": f"pay_wh_captured_{uuid.uuid4().hex[:6]}",
                            "order_id": oid,
                            "amount": 59900,
                            "currency": "INR",
                            "status": "captured"
                        }
                    }
                }
            }
            body_bytes = json.dumps(payload).encode("utf-8")
            signature = hmac.new(webhook_secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()

            # Dispatch to canonical endpoint
            res = client.post(
                "/api/payments/webhook",
                data=body_bytes,
                headers={"X-Razorpay-Signature": signature, "Content-Type": "application/json"}
            )
            assert res.status_code == 200
            assert res.json().get("status") in ("confirmed", "ok")

            # Check booking confirmed
            db.refresh(booking)
            assert booking.booking_status == "CONFIRMED"
            assert booking.payment_status in ("PAID", "CAPTURED")
            assert len(booking.tickets) == 1

            # Duplicate webhook event (idempotency check)
            res2 = client.post(
                "/api/payments/webhook",
                data=body_bytes,
                headers={"X-Razorpay-Signature": signature, "Content-Type": "application/json"}
            )
            assert res2.status_code == 200
            assert res2.json().get("status") in ("already_confirmed", "confirmed", "ok")
            db.refresh(booking)
            assert len(booking.tickets) == 1
    finally:
        db.close()
