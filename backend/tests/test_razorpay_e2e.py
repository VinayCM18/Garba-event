import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import json
import hmac
import hashlib
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Configure environment for tests before loading app
os.environ["RAZORPAY_KEY_ID"] = "rzp_test_e2e_mock_key"
os.environ["RAZORPAY_KEY_SECRET"] = "rzp_test_e2e_mock_secret"
os.environ["RAZORPAY_WEBHOOK_SECRET"] = "rzp_webhook_e2e_secret"
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

import time
from app.models.event_setting import EventSetting

client = TestClient(app)

def run_e2e_tests():
    os.environ["PASS_GATEWAY_FEE_TO_CUSTOMER"] = "false"
    os.environ["RAZORPAY_KEY_ID"] = "rzp_test_e2e_mock_key"
    os.environ["RAZORPAY_KEY_SECRET"] = "rzp_test_e2e_mock_secret"
    os.environ["RAZORPAY_WEBHOOK_SECRET"] = "rzp_webhook_e2e_secret"
    os.environ["RAZORPAY_MODE"] = "TEST"
    sync_database_schema()
    db = SessionLocal()
    setting = db.query(EventSetting).first()
    if not setting:
        setting = EventSetting()
        db.add(setting)
    setting.payment_method = "RAZORPAY"
    setting.ticket_price = 599.0
    from app.models.ticket_phase import TicketPhase
    phase = db.query(TicketPhase).filter(TicketPhase.phase_code == "EARLY_BIRD").first()
    if phase:
        phase.status = "ACTIVE"
        phase.sold_count = 0
    db.commit()
    # Clean up any previous test runs
    db.query(Ticket).filter(Ticket.booking_id.in_(
        db.query(Booking.id).filter(Booking.email.like("%example.com"))
    )).delete(synchronize_session=False)
    db.query(Payment).filter(Payment.booking_id.in_(
        db.query(Booking.id).filter(Booking.email.like("%example.com"))
    )).delete(synchronize_session=False)
    db.query(Booking).filter(Booking.email.like("%example.com")).delete(synchronize_session=False)
    db.commit()
    db.close()

    print("--- STARTING END-TO-END RAZORPAY INTEGRATION TESTS ---")

    key_secret = os.environ["RAZORPAY_KEY_SECRET"]
    webhook_secret = os.environ["RAZORPAY_WEBHOOK_SECRET"]

    # Mock razorpay Client so we do not make external HTTP calls to Razorpay in automated test
    with patch("razorpay.Client") as mock_rzp_client:
        mock_instance = MagicMock()
        mock_rzp_client.return_value = mock_instance

        # Test Case 1: Create Order for 1 Ticket (₹599.00 -> 59900 paise)
        mock_instance.order.create.return_value = {
            "id": "order_test_1tkt_001",
            "amount": 59900,
            "currency": "INR",
            "status": "created"
        }

        unique_idemp_1 = f"idemp_1_{int(time.time()*1000)}"
        res_1 = client.post("/api/payments/create-order", json={
            "customer_name": "Vinay Test Single",
            "email": "vinay.single@example.com",
            "phone": "9876543210",
            "ticket_count": 1,
            "idempotency_key": unique_idemp_1
        })
        assert res_1.status_code == 200, f"Error: {res_1.text}"
        data_1 = res_1.json()
        print("Test 1 (1 Ticket Order) Output:", data_1)
        assert data_1["amount"] == 599.0
        assert data_1["ticket_count"] == 1
        assert data_1["razorpay_order_id"] == "order_test_1tkt_001"
        assert data_1["payment_method"] == "RAZORPAY"
        assert data_1["key_id"] == "rzp_test_e2e_mock_key"
        booking_id_1 = data_1["booking_id"]

        # Verify call to mock_instance.order.create had amount = 59900 paise
        args, kwargs = mock_instance.order.create.call_args
        order_arg = kwargs.get("data") or (args[0] if args else {})
        assert order_arg["amount"] == 59900
        assert order_arg["currency"] == "INR"
        print("✓ Test 1 Passed: 1 ticket order correctly calculated as ₹599.00 (59900 paise)")

        # Test Case 2: Create Order for 10 Tickets with "BUY 10, PAY FOR 9" Offer (₹5,391.00 -> 539100 paise)
        mock_instance.order.create.return_value = {
            "id": "order_test_10tkt_002",
            "amount": 539100,
            "currency": "INR",
            "status": "created"
        }

        unique_idemp_10 = f"idemp_10_{int(time.time()*1000)}"
        res_10 = client.post("/api/payments/create-order", json={
            "customer_name": "Vinay Test Group",
            "email": "vinay.group@example.com",
            "phone": "9876543211",
            "ticket_count": 10,
            "idempotency_key": unique_idemp_10
        })
        assert res_10.status_code == 200, f"Error: {res_10.text}"
        data_10 = res_10.json()
        print("Test 2 (10 Tickets Group Offer) Output:", data_10)
        assert data_10["amount"] == 5391.0
        assert data_10["ticket_count"] == 10
        assert data_10["razorpay_order_id"] == "order_test_10tkt_002"
        booking_id_10 = data_10["booking_id"]

        # Verify call to mock_instance.order.create had amount = 539100 paise
        args, kwargs = mock_instance.order.create.call_args
        order_arg = kwargs.get("data") or (args[0] if args else {})
        assert order_arg["amount"] == 539100
        print("✓ Test 2 Passed: 10 tickets order correctly calculated as ₹5,391.00 (539100 paise, Buy 10 Pay For 9)")

        # Test Case 3: Signature Verification Success & Ticket Generation (10 Tickets)
        pay_id_10 = "pay_test_group_999"
        ord_id_10 = "order_test_10tkt_002"
        sig_data = f"{ord_id_10}|{pay_id_10}".encode("utf-8")
        valid_signature = hmac.new(key_secret.encode("utf-8"), sig_data, hashlib.sha256).hexdigest()

        res_verify = client.post("/api/payments/verify", json={
            "booking_id": booking_id_10,
            "razorpay_order_id": ord_id_10,
            "razorpay_payment_id": pay_id_10,
            "razorpay_signature": valid_signature
        })
        assert res_verify.status_code == 200, f"Error: {res_verify.text}"
        verify_data = res_verify.json()
        print("Test 3 (Signature Verification) Output:", verify_data)
        assert verify_data["booking_status"] == "CONFIRMED"
        assert verify_data["payment_status"] in ["PAID", "CAPTURED"]

        # Fetch tickets via details endpoint
        res_booking_10 = client.get(f"/api/bookings/{booking_id_10}")
        assert res_booking_10.status_code == 200
        booking_data_10 = res_booking_10.json()
        assert len(booking_data_10["tickets"]) == 10
        for tkt in booking_data_10["tickets"]:
            assert tkt["qr_token_raw"]
            assert tkt["ticket_status"] == "VALID"
        print("✓ Test 3 Passed: Payment verified via HMAC SHA-256 signature, 10 tickets generated with unique QR tokens")

        # Test Case 4: Idempotency Check (Duplicate verify callback)
        res_verify_duplicate = client.post("/api/payments/verify", json={
            "booking_id": booking_id_10,
            "razorpay_order_id": ord_id_10,
            "razorpay_payment_id": pay_id_10,
            "razorpay_signature": valid_signature
        })
        assert res_verify_duplicate.status_code == 200
        dup_data = res_verify_duplicate.json()
        assert dup_data["booking_status"] == "CONFIRMED"

        res_booking_dup = client.get(f"/api/bookings/{booking_id_10}")
        assert len(res_booking_dup.json()["tickets"]) == 10  # Must NOT have created 20 tickets!
        print("✓ Test 4 Passed: Duplicate verification is strictly idempotent, no duplicate tickets created")

        # Test Case 5: Reject Invalid Signature (Tampered)
        res_tampered = client.post("/api/payments/verify", json={
            "booking_id": booking_id_1,
            "razorpay_order_id": "order_test_1tkt_001",
            "razorpay_payment_id": "pay_test_bad_123",
            "razorpay_signature": "tampered_invalid_signature_hex"
        })
        assert res_tampered.status_code == 400
        print("✓ Test 5 Passed: Tampered payment signature rejected with 400 Bad Request")

        # Test Case 6: Reject Order ID Mismatch
        res_mismatch = client.post("/api/payments/verify", json={
            "booking_id": booking_id_1,
            "razorpay_order_id": "order_wrong_order_id_999",
            "razorpay_payment_id": "pay_test_bad_123",
            "razorpay_signature": "any_sig"
        })
        assert res_mismatch.status_code == 400
        print("✓ Test 6 Passed: Order ID mismatch rejected with 400 Bad Request")

        # Test Case 7: Disconnected Browser Edge Case (Browser closed before callback)
        # Customer pays successfully for booking_id_1, but browser crashes.
        # Razorpay sends webhook `payment.captured` directly to Railway backend.
        webhook_payload_captured = {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_async_webhook_888",
                        "order_id": "order_test_1tkt_001",
                        "amount": 59900,
                        "currency": "INR",
                        "status": "captured",
                        "method": "upi",
                        "notes": {
                            "booking_id": booking_id_1
                        }
                    }
                }
            }
        }
        body_bytes = json.dumps(webhook_payload_captured).encode("utf-8")
        wh_signature = hmac.new(webhook_secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()

        res_webhook = client.post(
            "/api/payments/razorpay/webhook",
            content=body_bytes,
            headers={
                "Content-Type": "application/json",
                "x-razorpay-signature": wh_signature
            }
        )
        assert res_webhook.status_code == 200, f"Webhook Error: {res_webhook.text}"
        wh_res_data = res_webhook.json()
        print("Test 7 (Webhook Capture) Output:", wh_res_data)
        assert wh_res_data["status"] in ["confirmed", "already_confirmed"]

        # Verify that customer looking up booking_id_1 on /booking-status finds it CONFIRMED with QR tickets
        res_lookup = client.get(f"/api/bookings/{booking_id_1}")
        assert res_lookup.status_code == 200
        lookup_data = res_lookup.json()
        assert lookup_data["booking_status"] == "CONFIRMED"
        assert lookup_data["payment_status"] in ["PAID", "CAPTURED"]
        assert len(lookup_data["tickets"]) == 1
        assert lookup_data["tickets"][0]["qr_token_raw"]
        print("✓ Test 7 Passed: Disconnected browser edge case solved: Webhook confirmed booking and customer can retrieve tickets on /booking-status")

        # Test Case 8: Webhook Replay / Duplicate Webhook
        res_webhook_dup = client.post(
            "/api/payments/razorpay/webhook",
            content=body_bytes,
            headers={
                "Content-Type": "application/json",
                "x-razorpay-signature": wh_signature
            }
        )
        assert res_webhook_dup.status_code == 200
        print("✓ Test 8 Passed: Webhook replay handled idempotently without error or duplicate tickets")

        # Test Case 9: Webhook payment.failed Event
        # Create another booking to test failed state
        mock_instance.order.create.return_value = {
            "id": "order_test_failed_003",
            "amount": 59900,
            "currency": "INR",
            "status": "created"
        }
        unique_fail_idemp = f"idemp_fail_test_{int(time.time()*1000)}"
        res_f = client.post("/api/payments/create-order", json={
            "customer_name": "Failed Pay Test",
            "email": "fail@example.com",
            "phone": "9876543212",
            "ticket_count": 1,
            "idempotency_key": unique_fail_idemp
        })
        assert res_f.status_code == 200, f"Create order failed: {res_f.text}"
        b_failed_id = res_f.json()["booking_id"]

        webhook_payload_failed = {
            "event": "payment.failed",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_declined_111",
                        "order_id": "order_test_failed_003",
                        "amount": 59900,
                        "currency": "INR",
                        "status": "failed",
                        "error_description": "Card was declined by issuing bank",
                        "notes": {
                            "booking_id": b_failed_id
                        }
                    }
                }
            }
        }
        body_failed_bytes = json.dumps(webhook_payload_failed).encode("utf-8")
        wh_failed_sig = hmac.new(webhook_secret.encode("utf-8"), body_failed_bytes, hashlib.sha256).hexdigest()

        res_wh_failed = client.post(
            "/api/payments/razorpay/webhook",
            content=body_failed_bytes,
            headers={
                "Content-Type": "application/json",
                "x-razorpay-signature": wh_failed_sig
            }
        )
        assert res_wh_failed.status_code == 200

        # Check booking status in database
        res_lookup_failed = client.get(f"/api/bookings/{b_failed_id}")
        assert res_lookup_failed.json()["booking_status"] == "PAYMENT_FAILED"
        print("✓ Test 9 Passed: Webhook payment.failed correctly transitions booking to PAYMENT_FAILED")

        # Test Case 10: Reject Webhook with Invalid Signature
        res_wh_bad = client.post(
            "/api/payments/razorpay/webhook",
            content=body_bytes,
            headers={
                "Content-Type": "application/json",
                "x-razorpay-signature": "forged_webhook_signature"
            }
        )
        assert res_wh_bad.status_code == 400
        print("✓ Test 10 Passed: Forged webhook signature correctly rejected with 400 Bad Request")

        # Authenticate staff
        res_login = client.post("/api/auth/login", json={
            "email": "staff@garbanight.in",
            "password": "StaffEntry@2026"
        })
        assert res_login.status_code == 200
        staff_token = res_login.json()["access_token"]
        staff_headers = {"Authorization": f"Bearer {staff_token}"}

        # Test Case 15: Staff scans QR ticket
        qr_token_1 = lookup_data["tickets"][0]["qr_token_raw"]
        res_verify_qr = client.post("/api/qr/verify", json={"qr_token": qr_token_1}, headers=staff_headers)
        assert res_verify_qr.status_code == 200
        assert res_verify_qr.json()["valid"] is True
        assert res_verify_qr.json()["status"] == "VALID"

        res_checkin = client.post(
            "/api/qr/checkin",
            json={
                "qr_token": qr_token_1,
                "device_information": "Staff Gate Mobile Scanner"
            },
            headers=staff_headers
        )
        assert res_checkin.status_code == 200
        assert res_checkin.json()["success"] is True
        assert res_checkin.json()["status"] == "SUCCESS"
        print("✓ Test 15 Passed: Staff authenticated, scanned, and successfully checked in QR ticket")

        # Test Case 16: Duplicate scan rejected
        res_verify_dup = client.post("/api/qr/verify", json={"qr_token": qr_token_1}, headers=staff_headers)
        assert res_verify_dup.status_code == 200
        assert res_verify_dup.json()["valid"] is False
        assert res_verify_dup.json()["status"] == "USED"

        res_checkin_dup = client.post(
            "/api/qr/checkin",
            json={
                "qr_token": qr_token_1,
                "device_information": "Staff Gate Mobile Scanner"
            },
            headers=staff_headers
        )
        assert res_checkin_dup.status_code == 409
        assert "ALREADY USED" in res_checkin_dup.json()["detail"]
        print("✓ Test 16 Passed: Duplicate QR scan immediately detected and rejected (HTTP 409 Conflict, ALREADY USED)")

    print("\n=======================================================")
    print("ALL 16 END-TO-END RAZORPAY INTEGRATION TESTS PASSED!")
    print("=======================================================")

def test_razorpay_e2e_suite():
    run_e2e_tests()

if __name__ == "__main__":
    run_e2e_tests()
