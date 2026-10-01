import os
import sys
import json
import hmac
import hashlib
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Configure test environment
os.environ["RAZORPAY_KEY_ID"] = "rzp_test_std_key"
os.environ["RAZORPAY_KEY_SECRET"] = "rzp_test_std_secret"
os.environ["RAZORPAY_WEBHOOK_SECRET"] = "rzp_test_std_webhook_secret"
os.environ["PAYMENT_PROVIDER"] = "RAZORPAY"
os.environ["RAZORPAY_MODE"] = "TEST"
os.environ["PASS_GATEWAY_FEE_TO_CUSTOMER"] = "false"
os.environ["JWT_SECRET"] = "fixed_jwt_secret_test_key_32_characters_long"
os.environ["QR_SECRET_SALT"] = "fixed_qr_salt_test_key_32_characters_long"

from app.main import app
from app.database import SessionLocal, sync_database_schema
from app.models.booking import Booking
from app.models.ticket import Ticket
from app.models.payment import Payment
from app.models.event_setting import EventSetting

client = TestClient(app)

def _generate_webhook_signature(body_bytes: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()

def _setup_test_booking(booking_id: str, razorpay_order_id: str, amount: float = 599.0):
    os.environ["RAZORPAY_KEY_ID"] = "rzp_test_std_key"
    os.environ["RAZORPAY_KEY_SECRET"] = "rzp_test_std_secret"
    os.environ["RAZORPAY_WEBHOOK_SECRET"] = "rzp_test_std_webhook_secret"
    os.environ["PAYMENT_PROVIDER"] = "RAZORPAY"
    os.environ["RAZORPAY_MODE"] = "TEST"
    sync_database_schema()
    db = SessionLocal()
    try:
        setting = db.query(EventSetting).first()
        if not setting:
            setting = EventSetting()
            db.add(setting)
        setting.payment_method = "RAZORPAY"
        setting.ticket_price = 599.0
        setting.razorpay_webhook_secret = None
        db.commit()

        # Clean existing test records
        existing_b = db.query(Booking).filter(Booking.booking_id == booking_id).first()
        if existing_b:
            db.query(Ticket).filter(Ticket.booking_id == existing_b.id).delete()
            db.query(Payment).filter(Payment.booking_id == existing_b.id).delete()
            db.delete(existing_b)
            db.commit()

        b = Booking(
            booking_id=booking_id,
            customer_name="Webhook Test User",
            email="webhooktest@example.com",
            phone="9876543210",
            ticket_count=1,
            ticket_price=amount,
            regular_amount=amount,
            ticket_subtotal=amount,
            amount=amount,
            booking_status="PENDING",
            payment_status="PENDING",
            payment_method="RAZORPAY",
            razorpay_order_id=razorpay_order_id
        )
        db.add(b)
        db.commit()

        p = Payment(
            booking_id=b.id,
            amount=amount,
            status="PENDING",
            payment_status="PENDING",
            payment_method="RAZORPAY",
            razorpay_order_id=razorpay_order_id
        )
        db.add(p)
        db.commit()
    finally:
        db.close()


def test_canonical_webhook_payment_captured():
    """Verify that canonical endpoint /api/payments/webhook handles payment.captured and issues tickets."""
    booking_id = "STD-WH-CAPTURED-01"
    order_id = "order_std_cap_01"
    _setup_test_booking(booking_id, order_id, amount=599.0)

    webhook_payload = {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_std_cap_01",
                    "order_id": order_id,
                    "amount": 59900,
                    "currency": "INR",
                    "status": "captured",
                    "method": "upi",
                    "notes": {"booking_id": booking_id}
                }
            }
        }
    }
    body_bytes = json.dumps(webhook_payload).encode("utf-8")
    sig = _generate_webhook_signature(body_bytes, "rzp_test_std_webhook_secret")

    res = client.post(
        "/api/payments/webhook",
        content=body_bytes,
        headers={"x-razorpay-signature": sig, "Content-Type": "application/json"}
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["status"] == "confirmed"
    assert data["booking_id"] == booking_id

    # Verify booking status in database
    db = SessionLocal()
    try:
        b = db.query(Booking).filter(Booking.booking_id == booking_id).first()
        assert b.booking_status == "CONFIRMED"
        assert b.payment_status in ["PAID", "CAPTURED"]
        tickets = db.query(Ticket).filter(Ticket.booking_id == b.id).all()
        assert len(tickets) == 1
    finally:
        db.close()


def test_canonical_webhook_order_paid():
    """Verify that canonical endpoint /api/payments/webhook handles order.paid event."""
    booking_id = "STD-WH-ORDERPAID-02"
    order_id = "order_std_paid_02"
    _setup_test_booking(booking_id, order_id, amount=599.0)

    webhook_payload = {
        "event": "order.paid",
        "payload": {
            "order": {
                "entity": {
                    "id": order_id,
                    "amount": 59900,
                    "amount_paid": 59900,
                    "status": "paid",
                    "notes": {"booking_id": booking_id}
                }
            },
            "payment": {
                "entity": {
                    "id": "pay_std_paid_02",
                    "order_id": order_id,
                    "amount": 59900,
                    "currency": "INR",
                    "status": "captured",
                    "method": "card"
                }
            }
        }
    }
    body_bytes = json.dumps(webhook_payload).encode("utf-8")
    sig = _generate_webhook_signature(body_bytes, "rzp_test_std_webhook_secret")

    res = client.post(
        "/api/payments/webhook",
        content=body_bytes,
        headers={"x-razorpay-signature": sig, "Content-Type": "application/json"}
    )
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "confirmed"

    db = SessionLocal()
    try:
        b = db.query(Booking).filter(Booking.booking_id == booking_id).first()
        assert b.booking_status == "CONFIRMED"
    finally:
        db.close()


def test_canonical_webhook_payment_failed():
    """Verify that canonical endpoint /api/payments/webhook handles payment.failed event."""
    booking_id = "STD-WH-FAILED-03"
    order_id = "order_std_fail_03"
    _setup_test_booking(booking_id, order_id, amount=599.0)

    webhook_payload = {
        "event": "payment.failed",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_std_fail_03",
                    "order_id": order_id,
                    "amount": 59900,
                    "currency": "INR",
                    "status": "failed",
                    "error_description": "Card was declined",
                    "notes": {"booking_id": booking_id}
                }
            }
        }
    }
    body_bytes = json.dumps(webhook_payload).encode("utf-8")
    sig = _generate_webhook_signature(body_bytes, "rzp_test_std_webhook_secret")

    res = client.post(
        "/api/payments/webhook",
        content=body_bytes,
        headers={"x-razorpay-signature": sig, "Content-Type": "application/json"}
    )
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "payment_failed"

    db = SessionLocal()
    try:
        b = db.query(Booking).filter(Booking.booking_id == booking_id).first()
        assert b.booking_status == "PAYMENT_FAILED"
        assert b.payment_status == "FAILED"
    finally:
        db.close()


def test_canonical_webhook_idempotency_duplicate_event():
    """Verify that repeated webhook events on canonical endpoint are idempotent and return already_confirmed."""
    booking_id = "STD-WH-IDEMP-04"
    order_id = "order_std_idemp_04"
    _setup_test_booking(booking_id, order_id, amount=599.0)

    webhook_payload = {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_std_idemp_04",
                    "order_id": order_id,
                    "amount": 59900,
                    "currency": "INR",
                    "status": "captured",
                    "method": "upi",
                    "notes": {"booking_id": booking_id}
                }
            }
        }
    }
    body_bytes = json.dumps(webhook_payload).encode("utf-8")
    sig = _generate_webhook_signature(body_bytes, "rzp_test_std_webhook_secret")

    # First delivery
    res1 = client.post(
        "/api/payments/webhook",
        content=body_bytes,
        headers={"x-razorpay-signature": sig, "Content-Type": "application/json"}
    )
    assert res1.status_code == 200
    assert res1.json()["status"] == "confirmed"

    # Duplicate delivery
    res2 = client.post(
        "/api/payments/webhook",
        content=body_bytes,
        headers={"x-razorpay-signature": sig, "Content-Type": "application/json"}
    )
    assert res2.status_code == 200
    assert res2.json()["status"] == "already_confirmed"

    # Check that tickets were NOT duplicated
    db = SessionLocal()
    try:
        b = db.query(Booking).filter(Booking.booking_id == booking_id).first()
        tickets = db.query(Ticket).filter(Ticket.booking_id == b.id).all()
        assert len(tickets) == 1
    finally:
        db.close()


def test_canonical_webhook_amount_mismatch_rejected():
    """Verify that amount mismatch is rejected with 400 Bad Request."""
    booking_id = "STD-WH-MISMATCH-05"
    order_id = "order_std_mismatch_05"
    _setup_test_booking(booking_id, order_id, amount=599.0) # Expected: 59900 paise

    # Tampered amount: 100 paise (₹1 instead of ₹599)
    webhook_payload = {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_std_mismatch_05",
                    "order_id": order_id,
                    "amount": 100, # TAMPERED
                    "currency": "INR",
                    "status": "captured",
                    "notes": {"booking_id": booking_id}
                }
            }
        }
    }
    body_bytes = json.dumps(webhook_payload).encode("utf-8")
    sig = _generate_webhook_signature(body_bytes, "rzp_test_std_webhook_secret")

    res = client.post(
        "/api/payments/webhook",
        content=body_bytes,
        headers={"x-razorpay-signature": sig, "Content-Type": "application/json"}
    )
    assert res.status_code == 400
    assert "amount mismatch" in res.text.lower()


def test_canonical_webhook_missing_and_invalid_hmac_rejected():
    """Verify that requests missing signature or with forged HMAC are rejected with 400 Bad Request."""
    os.environ["RAZORPAY_WEBHOOK_SECRET"] = "rzp_test_std_webhook_secret"
    body_bytes = json.dumps({"event": "payment.captured"}).encode("utf-8")

    # Missing signature
    res_missing = client.post(
        "/api/payments/webhook",
        content=body_bytes,
        headers={"Content-Type": "application/json"}
    )
    assert res_missing.status_code == 400
    assert "missing" in res_missing.text.lower()

    # Invalid / forged signature
    res_forged = client.post(
        "/api/payments/webhook",
        content=body_bytes,
        headers={"x-razorpay-signature": "forged_hmac_hex", "Content-Type": "application/json"}
    )
    assert res_forged.status_code == 400
    assert "invalid" in res_forged.text.lower()


def test_legacy_alias_endpoint_payments_razorpay_webhook():
    """Verify that legacy endpoint /api/payments/razorpay/webhook functions as an alias to the same handler."""
    booking_id = "STD-WH-LEGACY-ALIAS-06"
    order_id = "order_std_legacy_06"
    _setup_test_booking(booking_id, order_id, amount=599.0)

    webhook_payload = {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_std_legacy_06",
                    "order_id": order_id,
                    "amount": 59900,
                    "currency": "INR",
                    "status": "captured",
                    "notes": {"booking_id": booking_id}
                }
            }
        }
    }
    body_bytes = json.dumps(webhook_payload).encode("utf-8")
    sig = _generate_webhook_signature(body_bytes, "rzp_test_std_webhook_secret")

    res = client.post(
        "/api/payments/razorpay/webhook",
        content=body_bytes,
        headers={"x-razorpay-signature": sig, "Content-Type": "application/json"}
    )
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "confirmed"


def test_legacy_delegated_endpoint_webhook_razorpay():
    """Verify that legacy endpoint /api/webhook/razorpay delegates internally to the canonical handler."""
    booking_id = "STD-WH-LEGACY-DELEG-07"
    order_id = "order_std_deleg_07"
    _setup_test_booking(booking_id, order_id, amount=599.0)

    webhook_payload = {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_std_deleg_07",
                    "order_id": order_id,
                    "amount": 59900,
                    "currency": "INR",
                    "status": "captured",
                    "notes": {"booking_id": booking_id}
                }
            }
        }
    }
    body_bytes = json.dumps(webhook_payload).encode("utf-8")
    sig = _generate_webhook_signature(body_bytes, "rzp_test_std_webhook_secret")

    res = client.post(
        "/api/webhook/razorpay",
        content=body_bytes,
        headers={"x-razorpay-signature": sig, "Content-Type": "application/json"}
    )
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "confirmed"
