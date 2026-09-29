import sys
import os
import uuid
import hmac
import hashlib
import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.config import settings
from app.main import app
from app.database import SessionLocal, sync_database_schema
from app.models.event_setting import EventSetting
from app.models.booking import Booking
from app.models.payment import Payment
from app.services.payment_service import payment_service
from app.services.payment_providers.razorpay_provider import RazorpayPaymentProvider
from app.services.payment_providers.manual_upi import ManualUPIPaymentProvider
from app.utils.security import verify_razorpay_signature, verify_razorpay_webhook_signature

@pytest.fixture(autouse=True)
def setup_environment():
    """Ensure database schema is synced and test credentials exist."""
    sync_database_schema()
    db = SessionLocal()
    setting = db.query(EventSetting).first()
    if not setting:
        setting = EventSetting(
            event_name="GARBA NIGHT 2026",
            ticket_price=599.0,
            total_capacity=1500,
            max_per_booking=10,
            booking_open=True,
            payment_method="RAZORPAY"
        )
        db.add(setting)
    else:
        setting.ticket_price = 599.0
        setting.payment_method = "RAZORPAY"
        setting.group_offer_enabled = True
        setting.group_offer_size = 10
        setting.group_offer_free_tickets = 1
    db.commit()
    db.close()
    yield

def test_1_ticket_pricing():
    """Verify 1 ticket pricing passes 2% fee + 18% GST to customer (₹613.14)."""
    db = SessionLocal()
    rzp = RazorpayPaymentProvider()
    os.environ["PASS_GATEWAY_FEE_TO_CUSTOMER"] = "true"

    p1 = rzp.calculate_pricing(db, 1)
    db.close()

    assert p1["ticket_price"] == 599.0
    assert p1["regular_amount"] == 599.0
    assert p1["group_discount"] == 0.0
    assert p1["ticket_subtotal"] == 599.0
    assert p1["payment_fee"] == 11.98  # 2% of 599.00
    assert p1["gst_amount"] == 2.16    # 18% of 11.98
    assert p1["total_amount"] == 613.14
    assert p1["is_group_offer"] is False

def test_10_tickets_group_pricing():
    """Verify 10 tickets BUY 10, PAY FOR 9 subtotal ₹5,391.00 + fee + GST = ₹5,518.23."""
    db = SessionLocal()
    rzp = RazorpayPaymentProvider()
    os.environ["PASS_GATEWAY_FEE_TO_CUSTOMER"] = "true"

    p10 = rzp.calculate_pricing(db, 10)
    db.close()

    assert p10["ticket_price"] == 599.0
    assert p10["regular_amount"] == 5990.0
    assert p10["group_discount"] == 599.0
    assert p10["ticket_subtotal"] == 5391.0
    assert p10["payment_fee"] == 107.82  # 2% of 5391.00
    assert p10["gst_amount"] == 19.41    # 18% of 107.82
    assert p10["total_amount"] == 5518.23
    assert p10["is_group_offer"] is True
    assert p10["free_tickets"] == 1
    assert p10["offer_name"] == "BUY 10, PAY FOR 9"

def test_provider_selection_deterministic():
    """Verify provider selection prioritizes environment variables with case & whitespace normalization."""
    db = SessionLocal()

    # Razorpay variations
    for env_val in ["RAZORPAY", "razorpay", " Razorpay ", "RZP"]:
        os.environ["PAYMENT_PROVIDER"] = env_val
        if "PAYMENT_METHOD" in os.environ:
            del os.environ["PAYMENT_METHOD"]
        provider = payment_service.get_provider(db)
        assert isinstance(provider, RazorpayPaymentProvider)
        assert provider.provider_code == "RAZORPAY"

    # UPI manual variations
    for env_val in ["UPI_MANUAL", "upi_manual", " UPI ", "MANUAL_UPI"]:
        os.environ["PAYMENT_METHOD"] = env_val
        if "PAYMENT_PROVIDER" in os.environ:
            del os.environ["PAYMENT_PROVIDER"]
        provider = payment_service.get_provider(db)
        assert isinstance(provider, ManualUPIPaymentProvider)
        assert provider.provider_code == "UPI_MANUAL"

    db.close()

def test_stale_db_payment_method_overridden_by_env():
    """Verify stale DB row payment_method='UPI_MANUAL' does NOT override environment PAYMENT_PROVIDER='RAZORPAY'."""
    db = SessionLocal()
    setting = db.query(EventSetting).first()
    setting.payment_method = "UPI_MANUAL"
    db.commit()

    # Environment explicitly set to RAZORPAY
    os.environ["PAYMENT_PROVIDER"] = "RAZORPAY"
    if "PAYMENT_METHOD" in os.environ:
        del os.environ["PAYMENT_METHOD"]

    provider = payment_service.get_provider(db)
    assert isinstance(provider, RazorpayPaymentProvider)
    assert provider.provider_code == "RAZORPAY"

    # When environment is intentionally unset, falls back to DB
    os.environ.pop("PAYMENT_PROVIDER", None)
    os.environ.pop("PAYMENT_METHOD", None)
    orig_prov = getattr(settings, "PAYMENT_PROVIDER", None)
    orig_meth = getattr(settings, "PAYMENT_METHOD", None)
    try:
        settings.PAYMENT_PROVIDER = None
        settings.PAYMENT_METHOD = None
        fallback_provider = payment_service.get_provider(db)
        assert isinstance(fallback_provider, ManualUPIPaymentProvider)
        assert fallback_provider.provider_code == "UPI_MANUAL"
    finally:
        settings.PAYMENT_PROVIDER = orig_prov
        settings.PAYMENT_METHOD = orig_meth

    # Restore DB to RAZORPAY
    setting.payment_method = "RAZORPAY"
    db.commit()
    db.close()

def test_razorpay_order_creation_response_fields():
    """Verify /api/payments/create-order returns Razorpay fields and suppresses manual UPI QR fields."""
    os.environ["PAYMENT_PROVIDER"] = "RAZORPAY"
    os.environ["RAZORPAY_KEY_ID"] = "rzp_test_flow_key_123"
    os.environ["RAZORPAY_KEY_SECRET"] = "rzp_test_flow_secret_456"
    os.environ["RAZORPAY_MODE"] = "TEST"
    os.environ["PASS_GATEWAY_FEE_TO_CUSTOMER"] = "true"

    client = TestClient(app)
    mock_order_id = f"order_test_mock_{uuid.uuid4().hex[:8]}"

    with patch("razorpay.Client") as mock_client:
        mock_instance = MagicMock()
        mock_instance.order.create.return_value = {
            "id": mock_order_id,
            "amount": 61314,
            "currency": "INR",
            "status": "created"
        }
        mock_client.return_value = mock_instance

        response = client.post("/api/payments/create-order", json={
            "customer_name": "Test Customer",
            "email": f"cust_{uuid.uuid4().hex[:6]}@example.com",
            "phone": "+919876543210",
            "ticket_count": 1
        })

    assert response.status_code == 200
    data = response.json()

    # Must contain
    assert data["payment_method"] == "RAZORPAY"
    assert data["razorpay_order_id"] == mock_order_id
    assert data["key_id"] == "rzp_test_flow_key_123"
    assert data["razorpay_mode"] == "TEST"
    assert data["amount"] == 613.14
    assert data["payment_fee"] == 11.98
    assert data["gst_amount"] == 2.16

    # Must NOT contain manual UPI details
    assert data["upi_id"] is None
    assert data["upi_qr_image_url"] is None
    assert data["upi_payment_instructions"] is None

def test_missing_razorpay_credentials_raises_500():
    """Verify initiate_payment raises HTTP 500 when credentials are missing."""
    import uuid
    db = SessionLocal()
    setting = db.query(EventSetting).first()
    setting.razorpay_key_id = None
    setting.razorpay_key_secret = None
    db.commit()

    saved_id = os.environ.pop("RAZORPAY_KEY_ID", None)
    saved_secret = os.environ.pop("RAZORPAY_KEY_SECRET", None)

    try:
        rzp = RazorpayPaymentProvider()
        test_booking = Booking(
            booking_id=f"GN-2026-TEST-{uuid.uuid4().hex[:8]}",
            customer_name="Missing Creds",
            email="missing@example.com",
            phone="+919876543210",
            ticket_count=1,
            ticket_price=599.0,
            regular_amount=599.0,
            group_discount=0.0,
            ticket_subtotal=599.0,
            payment_fee=11.98,
            gst_amount=2.16,
            amount=613.14,
            currency="INR",
            payment_method="RAZORPAY",
            payment_status="PENDING",
            booking_status="PAYMENT_PENDING"
        )
        db.add(test_booking)
        db.commit()

        with pytest.raises(HTTPException) as exc_info:
            rzp.initiate_payment(test_booking, db)

        assert exc_info.value.status_code == 500
        assert "credentials" in str(exc_info.value.detail).lower()

    finally:
        if saved_id:
            os.environ["RAZORPAY_KEY_ID"] = saved_id
        if saved_secret:
            os.environ["RAZORPAY_KEY_SECRET"] = saved_secret
        db.close()

def test_webhook_and_payment_signatures():
    """Verify HMAC SHA-256 signature verification for payments and webhooks."""
    # Razorpay Payment Signature
    order_id = "order_test_sig_123"
    payment_id = "pay_test_sig_456"
    secret = "rzp_secret_key_testing_123"
    msg = f"{order_id}|{payment_id}".encode("utf-8")
    valid_sig = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()

    assert verify_razorpay_signature(order_id, payment_id, valid_sig, key_secret=secret) is True
    assert verify_razorpay_signature(order_id, payment_id, "tampered_signature", key_secret=secret) is False
    assert verify_razorpay_signature(order_id, "wrong_payment_id", valid_sig, key_secret=secret) is False

    # Razorpay Webhook Signature
    body = b'{"event":"payment.captured","payload":{"payment":{"entity":{"id":"pay_test_sig_456"}}}}'
    wh_secret = "whsec_test_flow_789"
    valid_wh_sig = hmac.new(wh_secret.encode("utf-8"), body, hashlib.sha256).hexdigest()

    assert verify_razorpay_webhook_signature(body, valid_wh_sig, webhook_secret=wh_secret) is True
    assert verify_razorpay_webhook_signature(body, "tampered_wh_sig", webhook_secret=wh_secret) is False
    assert verify_razorpay_webhook_signature(b'{"different":"body"}', valid_wh_sig, webhook_secret=wh_secret) is False
