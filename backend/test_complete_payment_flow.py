import requests
import json
import hmac
import hashlib

BASE_URL = "http://127.0.0.1:8000"

def test_flow():
    print("--- 1. Testing Price Calculation API ---")
    res = requests.get(f"{BASE_URL}/api/payments/calculate?ticket_count=1")
    print(f"1 Ticket calculation status: {res.status_code}")
    data1 = res.json()
    print("1 Ticket:", json.dumps(data1, indent=2))
    assert data1["ticket_subtotal"] == 599.0, f"Expected 599.0 got {data1['ticket_subtotal']}"
    assert data1["payment_fee"] == 11.98, f"Expected 11.98 got {data1['payment_fee']}"
    assert data1["gst_amount"] == 2.16, f"Expected 2.16 got {data1['gst_amount']}"
    assert data1["total_amount"] == 613.14, f"Expected 613.14 got {data1['total_amount']}"

    res4 = requests.get(f"{BASE_URL}/api/payments/calculate?ticket_count=4")
    data4 = res4.json()
    print("4 Tickets:", json.dumps(data4, indent=2))
    assert data4["ticket_subtotal"] == 2396.0, f"Expected 2396.0 got {data4['ticket_subtotal']}"
    assert data4["payment_fee"] == 47.92, f"Expected 47.92 got {data4['payment_fee']}"
    assert data4["gst_amount"] == 8.63, f"Expected 8.63 got {data4['gst_amount']}"
    assert data4["total_amount"] == 2452.55, f"Expected 2452.55 got {data4['total_amount']}"
    print("[OK] Price calculation tests passed!")

    print("\n--- 2. Testing Order Creation API ---")
    order_payload = {
        "customer_name": "Antigravity Tester",
        "email": "tester@example.com",
        "phone": "9876543210",
        "ticket_count": 4,
        "idempotency_key": "test_order_key_9999"
    }
    order_res = requests.post(f"{BASE_URL}/api/payments/create-order", json=order_payload)
    print("Order Creation Status:", order_res.status_code)
    order_data = order_res.json()
    print("Order Data:", json.dumps(order_data, indent=2))
    assert order_data["amount"] == 2452.55, f"Expected 2452.55 got {order_data['amount']}"
    assert order_data["ticket_subtotal"] == 2396.0
    booking_id = order_data["booking_id"]
    order_id = order_data["razorpay_order_id"]
    print("[OK] Order creation test passed!")

    print("\n--- 3. Testing Payment Verification API ---")
    verify_payload = {
        "booking_id": booking_id,
        "razorpay_order_id": order_id,
        "razorpay_payment_id": "pay_test_simulation_9999",
        "razorpay_signature": "sim_sig_valid_12345"
    }
    verify_res = requests.post(f"{BASE_URL}/api/payments/verify", json=verify_payload)
    print("Verify Status:", verify_res.status_code)
    verify_data = verify_res.json()
    print("Verify Response:", json.dumps(verify_data, indent=2))
    assert verify_data["success"] is True
    assert verify_data["payment_status"] == "PAID"
    assert verify_data["booking_status"] == "CONFIRMED"
    print("[OK] Verification test passed!")

    print("\n--- 4. Testing Booking Details & QR Tickets Issuance ---")
    booking_res = requests.get(f"{BASE_URL}/api/bookings/{booking_id}")
    booking_data = booking_res.json()
    print("Booking Details:", json.dumps({
        "booking_id": booking_data["booking_id"],
        "customer_name": booking_data["customer_name"],
        "ticket_count": booking_data["ticket_count"],
        "ticket_subtotal": booking_data["ticket_subtotal"],
        "payment_fee": booking_data["payment_fee"],
        "gst_amount": booking_data["gst_amount"],
        "amount": booking_data["amount"],
        "payment_status": booking_data["payment_status"],
        "booking_status": booking_data["booking_status"],
        "tickets_count": len(booking_data["tickets"])
    }, indent=2))
    assert len(booking_data["tickets"]) == 4, f"Expected 4 tickets, got {len(booking_data['tickets'])}"
    print("[OK] QR Tickets successfully generated!")

    print("\n--- 5. Testing Webhook Idempotency ---")
    webhook_body = json.dumps({
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_test_simulation_9999",
                    "order_id": order_id,
                    "amount": 245255,
                    "currency": "INR",
                    "status": "captured"
                }
            }
        }
    }).encode("utf-8")
    webhook_res = requests.post(
        f"{BASE_URL}/api/payments/webhook",
        data=webhook_body,
        headers={"Content-Type": "application/json"}
    )
    print("Webhook response status:", webhook_res.status_code)
    print("Webhook response body:", webhook_res.json())
    assert webhook_res.json().get("status") in ["already_confirmed", "confirmed"]
    print("[OK] Webhook idempotency test passed!")

    print("\n=======================================================")
    print("[SUCCESS] ALL PAYMENT, FEE CALCULATION & WEBHOOK TESTS PASSED!")
    print("=======================================================")

if __name__ == "__main__":
    test_flow()
