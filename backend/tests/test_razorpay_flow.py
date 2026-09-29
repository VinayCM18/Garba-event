import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import hmac
import hashlib
from app.database import SessionLocal
from app.services.payment_providers.razorpay_provider import RazorpayPaymentProvider
from app.utils.security import verify_razorpay_signature, verify_razorpay_webhook_signature

def test_razorpay_pricing_and_signatures():
    db = SessionLocal()
    rzp = RazorpayPaymentProvider()

    # 1 Ticket Calculation Test
    p1 = rzp.calculate_pricing(db, 1)
    print("1 Ticket Pricing:", p1)
    assert p1["ticket_price"] == 599.0
    assert p1["regular_amount"] == 599.0
    assert p1["group_discount"] == 0.0
    assert p1["ticket_subtotal"] == 599.0
    assert p1["total_amount"] == 599.0
    assert p1["tax_included"] is True
    assert p1["is_group_offer"] is False

    # 10 Tickets BUY 10, PAY FOR 9 Group Offer Test
    p10 = rzp.calculate_pricing(db, 10)
    print("10 Tickets Group Offer Pricing:", p10)
    assert p10["ticket_price"] == 599.0
    assert p10["regular_amount"] == 5990.0
    assert p10["group_discount"] == 599.0
    assert p10["ticket_subtotal"] == 5391.0
    assert p10["total_amount"] == 5391.0
    assert p10["is_group_offer"] is True
    assert p10["free_tickets"] == 1
    assert p10["offer_name"] == "BUY 10, PAY FOR 9"

    # Razorpay Payment Signature Verification Test
    order_id = "order_test_123"
    payment_id = "pay_test_456"
    secret = "test_secret_key_123"
    msg = f"{order_id}|{payment_id}".encode("utf-8")
    valid_sig = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()
    assert verify_razorpay_signature(order_id, payment_id, valid_sig, key_secret=secret) is True
    assert verify_razorpay_signature(order_id, payment_id, "invalid_signature", key_secret=secret) is False

    # Razorpay Webhook Signature Verification Test
    webhook_body = b'{"event": "payment.captured", "payload": {"payment": {"entity": {"id": "pay_test_456"}}}}'
    webhook_secret = "whsec_test_789"
    valid_wh_sig = hmac.new(webhook_secret.encode("utf-8"), webhook_body, hashlib.sha256).hexdigest()
    assert verify_razorpay_webhook_signature(webhook_body, valid_wh_sig, webhook_secret=webhook_secret) is True
    assert verify_razorpay_webhook_signature(webhook_body, "tampered_sig", webhook_secret=webhook_secret) is False

    print("ALL RAZORPAY UNIT TESTS PASSED!")

if __name__ == "__main__":
    test_razorpay_pricing_and_signatures()
