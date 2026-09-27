import os
import io
import sys
from PIL import Image

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal, sync_database_schema
from app.models.event_setting import EventSetting
from app.models.user import User
from app.models.booking import Booking
from app.models.ticket import Ticket
from app.models.payment import Payment
from app.utils.security import get_password_hash, create_access_token

def create_test_image_bytes(format="JPEG"):
    buf = io.BytesIO()
    img = Image.new("RGB", (100, 100), color=(255, 215, 0))
    img.save(buf, format=format)
    buf.seek(0)
    return buf.getvalue()

def run_tests():
    print("==================================================")
    print("RUNNING END-TO-END MANUAL UPI & ARCHITECTURE TESTS")
    print("==================================================")

    # 1. Sync DB
    sync_database_schema()
    db = SessionLocal()

    # Ensure admin user exists
    admin = db.query(User).filter(User.email == "admin@garbanight.com").first()
    if not admin:
        admin = User(
            email="admin@garbanight.com",
            password_hash=get_password_hash("Admin@12345"),
            name="System Admin",
            role="SUPER_ADMIN",
            is_active=True
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)

    admin_token = create_access_token(data={"sub": str(admin.id), "role": admin.role})
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Ensure event settings are set to UPI_MANUAL
    setting = db.query(EventSetting).first()
    if not setting:
        setting = EventSetting(id=1, event_name="GARBA NIGHT 2026", payment_method="UPI_MANUAL")
        db.add(setting)
    else:
        setting.payment_method = "UPI_MANUAL"
        setting.upi_id = "samaymadhyastha2005@oksbi"
    db.commit()
    db.close()

    client = TestClient(app)

    # TEST 1: Public Config
    print("\n--- TEST 1: Public Config Returns Manual UPI Settings ---")
    res = client.get("/api/bookings/public-config")
    assert res.status_code == 200, f"Config failed: {res.text}"
    cfg = res.json()
    print(f"Payment Method: {cfg.get('payment_method')}")
    print(f"UPI ID: {cfg.get('upi_id')}")
    assert cfg.get("payment_method") == "UPI_MANUAL"
    assert cfg.get("upi_id") == "samaymadhyastha2005@oksbi"
    print("✓ Test 1 Passed!")

    # TEST 2: Pricing Calculations
    print("\n--- TEST 2: Amount & Pricing Backend Calculation ---")
    # 1 ticket
    res_1 = client.get("/api/payments/calculate?ticket_count=1")
    assert res_1.status_code == 200
    p1 = res_1.json()
    print(f"1 Ticket: total_amount = ₹{p1['total_amount']}, payment_fee = ₹{p1['payment_fee']}")
    assert p1["total_amount"] == 599.0
    assert p1["payment_fee"] == 0.0

    # 10 tickets (BUY 10, PAY FOR 9)
    res_10 = client.get("/api/payments/calculate?ticket_count=10")
    assert res_10.status_code == 200
    p10 = res_10.json()
    print(f"10 Tickets: regular = ₹{p10['regular_amount']}, discount = ₹{p10['group_discount']}, total = ₹{p10['total_amount']}, fee = ₹{p10['payment_fee']}")
    assert p10["regular_amount"] == 5990.0
    assert p10["group_discount"] == 599.0
    assert p10["total_amount"] == 5391.0
    assert p10["payment_fee"] == 0.0
    print("✓ Test 2 Passed: Exactly ₹5,391 calculated on backend for 10 tickets!")

    # TEST 3: Order Creation for 10 tickets
    print("\n--- TEST 3: Create Order for 10 Tickets (Manual UPI) ---")
    order_payload = {
        "customer_name": "Rahul Sharma",
        "email": "rahul.sharma.test@gmail.com",
        "phone": "9876543210",
        "ticket_count": 10
    }
    res_order = client.post("/api/payments/create-order", json=order_payload)
    assert res_order.status_code == 200, f"Order creation failed: {res_order.text}"
    order_data = res_order.json()
    booking_id = order_data["booking_id"]
    print(f"Created Booking ID: {booking_id}")
    print(f"Amount: ₹{order_data['amount']}")
    print(f"Payment Method: {order_data['payment_method']}")
    print(f"UPI ID: {order_data['upi_id']}")
    assert order_data["amount"] == 5391.0
    assert order_data["payment_method"] == "UPI_MANUAL"
    assert order_data["upi_id"] == "samaymadhyastha2005@oksbi"
    print("✓ Test 3 Passed!")

    # TEST 4: Initial Booking Status Check
    print("\n--- TEST 4: Initial Booking Status before payment ---")
    res_b = client.get(f"/api/bookings/{booking_id}")
    assert res_b.status_code == 200
    b_data = res_b.json()
    print(f"Booking status: {b_data['booking_status']}")
    print(f"Payment status: {b_data['payment_status']}")
    assert b_data["booking_status"] == "PAYMENT_PENDING"
    assert b_data["payment_status"] == "PENDING"
    print("✓ Test 4 Passed!")

    # TEST 5: UTR & Screenshot Validation Checks
    print("\n--- TEST 5: Validation on Proof Submission ---")
    # A. Empty UTR should fail
    img_data = create_test_image_bytes()
    res_bad_utr = client.post(
        "/api/payments/submit-manual-proof",
        data={"booking_id": booking_id, "utr_number": ""},
        files={"screenshot": ("test.jpg", img_data, "image/jpeg")}
    )
    assert res_bad_utr.status_code in [400, 422], f"Bad UTR test failed: {res_bad_utr.status_code}, {res_bad_utr.text}"
    print(f"Empty UTR rejected correctly: {res_bad_utr.json()['detail']}")

    # B. Fake executable disguised as jpg should fail image verification
    fake_exe = b"MZ\x90\x00\x03\x00\x00\x00This is a fake windows binary"
    res_bad_file = client.post(
        "/api/payments/submit-manual-proof",
        data={"booking_id": booking_id, "utr_number": "UTR123456789012"},
        files={"screenshot": ("malicious.jpg", fake_exe, "image/jpeg")}
    )
    assert res_bad_file.status_code == 400
    print(f"Corrupt / executable file rejected correctly: {res_bad_file.json()['detail']}")
    print("✓ Test 5 Passed!")

    # TEST 6: Valid Submission
    print("\n--- TEST 6: Valid Submission with UTR & Real Screenshot ---")
    import uuid
    valid_utr = f"UTR{uuid.uuid4().hex[:12].upper()}"
    res_submit = client.post(
        "/api/payments/submit-manual-proof",
        data={"booking_id": booking_id, "utr_number": valid_utr},
        files={"screenshot": ("proof.jpg", img_data, "image/jpeg")}
    )
    assert res_submit.status_code == 200, f"Submit proof failed: {res_submit.text}"
    sub_data = res_submit.json()
    print(f"Submission response: {sub_data['message']}")
    print(f"Booking status: {sub_data['booking_status']}")
    print(f"Payment status: {sub_data['payment_status']}")
    assert sub_data["booking_status"] == "PAYMENT_VERIFICATION_PENDING"
    assert sub_data["payment_status"] == "VERIFICATION_PENDING"
    print("✓ Test 6 Passed!")

    # TEST 7: Duplicate UTR Prevention
    print("\n--- TEST 7: Duplicate UTR Prevention ---")
    # Initiate another booking
    res_order_2 = client.post("/api/payments/create-order", json={
        "customer_name": "Pooja Patel",
        "email": "pooja.patel.test@gmail.com",
        "phone": "9123456780",
        "ticket_count": 1
    })
    booking_id_2 = res_order_2.json()["booking_id"]
    # Attempt to submit the same UTR
    res_dup = client.post(
        "/api/payments/submit-manual-proof",
        data={"booking_id": booking_id_2, "utr_number": valid_utr},
        files={"screenshot": ("proof2.jpg", img_data, "image/jpeg")}
    )
    assert res_dup.status_code == 400
    print(f"Duplicate UTR rejected correctly: {res_dup.json()['detail']}")
    print("✓ Test 7 Passed!")

    # TEST 8: Screenshot Protection (Unauthenticated vs Admin)
    print("\n--- TEST 8: Screenshot Protection Security ---")
    # Unauthenticated should be 401
    res_unauth = client.get(f"/api/admin/payments/{booking_id}/screenshot")
    assert res_unauth.status_code == 401
    print("Unauthenticated access blocked: 401 Unauthorized")

    # Authenticated Admin should succeed (200)
    res_auth = client.get(f"/api/admin/payments/{booking_id}/screenshot", headers=admin_headers)
    assert res_auth.status_code == 200
    assert res_auth.headers["content-type"] in ["image/jpeg", "image/png", "image/webp"]
    print("Authenticated admin access allowed: 200 OK image stream")
    print("✓ Test 8 Passed!")

    # TEST 9: Admin Verification List
    print("\n--- TEST 9: Admin Verification Queue ---")
    res_list = client.get("/api/admin/payments/verification?status=VERIFICATION_PENDING", headers=admin_headers)
    assert res_list.status_code == 200
    items = res_list.json()
    target_item = next((i for i in items if i["booking_id"] == booking_id), None)
    assert target_item is not None, "Booking not found in pending verification queue"
    print(f"Found in verification queue: {target_item['booking_id']}, customer: {target_item['customer_name']}, UTR: {target_item['utr_number']}, Amount: ₹{target_item['amount']}")
    assert target_item["amount"] == 5391.0
    assert target_item["ticket_count"] == 10
    print("✓ Test 9 Passed!")

    # TEST 10: Rejection Flow
    print("\n--- TEST 10: Admin Rejection Flow on Booking 2 ---")
    # Submit proof on booking 2 with distinct UTR
    res_sub2 = client.post(
        "/api/payments/submit-manual-proof",
        data={"booking_id": booking_id_2, "utr_number": f"UTR{uuid.uuid4().hex[:12].upper()}"},
        files={"screenshot": ("proof2.jpg", img_data, "image/jpeg")}
    )
    assert res_sub2.status_code == 200

    # Reject payment
    reject_reason = "UTR reference not found in bank statement"
    res_reject = client.post(
        f"/api/admin/payments/{booking_id_2}/reject",
        headers=admin_headers,
        json={"reason": reject_reason}
    )
    assert res_reject.status_code == 200
    # Check booking 2 status
    res_b2 = client.get(f"/api/bookings/{booking_id_2}")
    b2_data = res_b2.json()
    print(f"Booking 2 Status after rejection: {b2_data['booking_status']}")
    print(f"Payment 2 Status after rejection: {b2_data['payment_status']}")
    print(f"Rejection Reason: {b2_data['rejection_reason']}")
    assert b2_data["booking_status"] == "PAYMENT_FAILED"
    assert b2_data["payment_status"] == "REJECTED"
    assert b2_data["rejection_reason"] == reject_reason
    assert len(b2_data.get("tickets", [])) == 0, "No tickets should be generated for rejected payment!"
    print("✓ Test 10 Passed!")

    # TEST 11: Approval Flow & 10 Ticket Generation
    print("\n--- TEST 11: Admin Approval Flow & Unique Ticket Generation ---")
    res_approve = client.post(
        f"/api/admin/payments/{booking_id}/approve",
        headers=admin_headers
    )
    assert res_approve.status_code == 200
    app_data = res_approve.json()
    print(f"Approval response: {app_data['message']}")

    # Verify Booking 1 is CONFIRMED and has 10 tickets
    res_b1 = client.get(f"/api/bookings/{booking_id}")
    b1_data = res_b1.json()
    print(f"Booking Status: {b1_data['booking_status']}")
    print(f"Payment Status: {b1_data['payment_status']}")
    print(f"Verified by: {b1_data['verified_by']}")
    assert b1_data["booking_status"] == "CONFIRMED"
    assert b1_data["payment_status"] == "PAID"
    assert b1_data["verified_by"] is not None

    tickets = b1_data.get("tickets", [])
    print(f"Total tickets generated: {len(tickets)}")
    assert len(tickets) == 10, f"Expected 10 tickets, got {len(tickets)}"

    # Verify all 10 tickets have unique IDs and QR codes
    ticket_ids = set()
    qr_tokens = set()
    for idx, t in enumerate(tickets):
        ticket_ids.add(t["ticket_id"])
        if t.get("qr_token_raw"):
            qr_tokens.add(t["qr_token_raw"])
        assert t["ticket_status"] == "VALID"
        assert t["checkin_status"] is False
    assert len(ticket_ids) == 10, "All 10 tickets must have unique ticket IDs"
    assert len(qr_tokens) == 10, "All 10 tickets must have unique QR codes"
    print("✓ All 10 tickets have unique IDs, unique QR codes, and are VALID!")

    # TEST 12: Idempotency (Admin double clicks Approve)
    print("\n--- TEST 12: Double-Click Approve Idempotency ---")
    res_approve_again = client.post(
        f"/api/admin/payments/{booking_id}/approve",
        headers=admin_headers
    )
    assert res_approve_again.status_code == 200
    res_b1_again = client.get(f"/api/bookings/{booking_id}")
    tickets_again = res_b1_again.json().get("tickets", [])
    assert len(tickets_again) == 10, "Tickets must not be duplicated on repeated approval"
    print("✓ Test 12 Passed: Idempotent! Double-click approve did not duplicate tickets.")

    print("\n==================================================")
    print("ALL 12 END-TO-END TESTS PASSED SUCCESSFULLY!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
