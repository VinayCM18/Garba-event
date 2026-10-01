import os
import sys
import uuid
import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app
from app.database import SessionLocal, sync_database_schema
from app.models.event_setting import EventSetting
from app.models.booking import Booking
from app.services.payment_providers.razorpay_provider import RazorpayPaymentProvider

@pytest.fixture(autouse=True)
def clean_db():
    sync_database_schema()
    db = SessionLocal()
    setting = db.query(EventSetting).first()
    if not setting:
        setting = EventSetting(
            event_name="NAVRANG 2026",
            ticket_price=599.0,
            payment_method="RAZORPAY"
        )
        db.add(setting)
    else:
        setting.event_name = "NAVRANG 2026"
        setting.ticket_price = 599.0
        setting.payment_method = "RAZORPAY"
        # Simulate old test key in SQLite EventSetting
        setting.razorpay_key_id = "rzp_test_TiC6o9R7o57CrC"
        setting.razorpay_key_secret = "old_test_secret_in_db"
    db.commit()
    db.close()
    yield

def test_live_mode_resolves_env_key_and_ignores_sqlite_test_key():
    """When RAZORPAY_MODE=LIVE, environment variables rzp_live_... MUST win over SQLite rzp_test_."""
    db = SessionLocal()
    rzp = RazorpayPaymentProvider()

    with patch.dict(os.environ, {
        "RAZORPAY_MODE": "LIVE",
        "RAZORPAY_KEY_ID": "rzp_live_abc123XYZliveKey",
        "RAZORPAY_KEY_SECRET": "live_secret_456789",
    }, clear=False):
        key_id, key_secret, _, mode = rzp._get_credentials(db)
        assert mode == "LIVE"
        assert key_id == "rzp_live_abc123XYZliveKey"
        assert key_secret == "live_secret_456789"
        # Ensure SQLite key was NOT used
        assert "rzp_test_TiC6o9R7o57CrC" != key_id
    db.close()

def test_live_mode_rejects_test_key():
    """When RAZORPAY_MODE=LIVE and key begins with rzp_test_, strictly raise configuration error."""
    db = SessionLocal()
    rzp = RazorpayPaymentProvider()

    with patch.dict(os.environ, {
        "RAZORPAY_MODE": "LIVE",
        "RAZORPAY_KEY_ID": "rzp_test_TiC6o9R7o57CrC",
        "RAZORPAY_KEY_SECRET": "some_secret",
    }, clear=False):
        with pytest.raises(HTTPException) as exc_info:
            rzp._get_credentials(db)
        assert exc_info.value.status_code == 500
        assert "Razorpay LIVE mode requires a live API key beginning with rzp_live_" in exc_info.value.detail
        assert "rzp_test_" in exc_info.value.detail
    db.close()

def test_live_mode_rejects_missing_key():
    """When RAZORPAY_MODE=LIVE and RAZORPAY_KEY_ID is missing/empty, strictly raise configuration error."""
    db = SessionLocal()
    rzp = RazorpayPaymentProvider()

    with patch.dict(os.environ, {
        "RAZORPAY_MODE": "LIVE",
        "RAZORPAY_KEY_ID": "",
        "RAZORPAY_KEY_SECRET": "live_secret",
    }, clear=False):
        with pytest.raises(HTTPException) as exc_info:
            rzp._get_credentials(db)
        assert exc_info.value.status_code == 500
        assert "Razorpay LIVE mode requires RAZORPAY_KEY_ID environment variable to be configured" in exc_info.value.detail
    db.close()

def test_live_mode_rejects_missing_secret():
    """When RAZORPAY_MODE=LIVE and RAZORPAY_KEY_SECRET is missing, strictly raise configuration error."""
    db = SessionLocal()
    rzp = RazorpayPaymentProvider()

    with patch.dict(os.environ, {
        "RAZORPAY_MODE": "LIVE",
        "RAZORPAY_KEY_ID": "rzp_live_abc123XYZliveKey",
        "RAZORPAY_KEY_SECRET": "",
    }, clear=False):
        with pytest.raises(HTTPException) as exc_info:
            rzp._get_credentials(db)
        assert exc_info.value.status_code == 500
        assert "Razorpay LIVE mode requires RAZORPAY_KEY_SECRET environment variable to be configured" in exc_info.value.detail
    db.close()

def test_test_mode_allows_test_key():
    """When RAZORPAY_MODE=TEST, test keys are allowed and env vars take priority."""
    db = SessionLocal()
    rzp = RazorpayPaymentProvider()

    with patch.dict(os.environ, {
        "RAZORPAY_MODE": "TEST",
        "RAZORPAY_KEY_ID": "rzp_test_myValidTestKey",
        "RAZORPAY_KEY_SECRET": "test_secret_123",
    }, clear=False):
        key_id, key_secret, _, mode = rzp._get_credentials(db)
        assert mode == "TEST"
        assert key_id == "rzp_test_myValidTestKey"
        assert key_secret == "test_secret_123"
    db.close()

def test_create_order_endpoint_live_mode_response():
    """Verifies POST /api/payments/create-order in LIVE mode returns rzp_live_ key and never leaks secret."""
    client = TestClient(app)
    mock_order_id = f"order_live_{uuid.uuid4().hex[:8]}"

    with patch.dict(os.environ, {
        "RAZORPAY_MODE": "LIVE",
        "RAZORPAY_KEY_ID": "rzp_live_prodKey999",
        "RAZORPAY_KEY_SECRET": "super_secret_live_value_never_leak",
        "PAYMENT_PROVIDER": "RAZORPAY"
    }, clear=False):
        with patch("razorpay.Client") as mock_client:
            mock_instance = MagicMock()
            mock_instance.order.create.return_value = {
                "id": mock_order_id,
                "amount": 59900,
                "currency": "INR",
                "status": "created"
            }
            mock_client.return_value = mock_instance

            res = client.post("/api/payments/create-order", json={
                "customer_name": "Live Customer",
                "email": "customer@live.com",
                "phone": "9876543210",
                "ticket_count": 1
            })

            assert res.status_code == 200, f"Error: {res.text}"
            data = res.json()

            # Confirm required response fields
            assert data["payment_method"] == "RAZORPAY"
            assert data["razorpay_order_id"] == mock_order_id
            assert data["key_id"] == "rzp_live_prodKey999"
            assert data["razorpay_mode"] == "LIVE"
            assert data["is_simulation"] is False

            # Confirm secret is NEVER leaked in the response
            assert "super_secret_live_value_never_leak" not in str(data)
            assert "key_secret" not in data
            assert "razorpay_key_secret" not in data
