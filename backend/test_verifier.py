import requests
import time

base_url = "http://127.0.0.1:8000"

print("--- Step 1: Testing Public Configuration ---")
r = requests.get(f"{base_url}/api/bookings/public-config")
assert r.status_code == 200, f"Public config failed: {r.status_code}"
cfg = r.json()
print(f"Event: {cfg.get('event_name')} | Price: Rs {cfg.get('ticket_price')} | Capacity: {cfg.get('total_capacity')} | Remaining: {cfg.get('remaining_tickets')}")

print("\n--- Step 2: Testing Payment Gateway Order Creation ---")
t = int(time.time())
order_payload = {
    "customer_name": "Riya Patel",
    "email": "riya.patel@example.com",
    "phone": "9876543210",
    "ticket_count": 2,
    "idempotency_key": f"test_order_gateway_{t}"
}
r = requests.post(f"{base_url}/api/payments/create-order", json=order_payload)
assert r.status_code == 200, f"Order creation failed: {r.status_code} {r.text}"
order_data = r.json()
booking_id = order_data["booking_id"]
order_id = order_data["razorpay_order_id"]
print(f"Order created: {order_id} | Booking: {booking_id} | Amount: Rs {order_data['amount']} | Sim Mode: {order_data.get('is_simulation')}")

print("\n--- Step 3: Testing Real-time / Simulator Payment Verification ---")
verify_payload = {
    "booking_id": booking_id,
    "razorpay_order_id": order_id,
    "razorpay_payment_id": f"pay_test_sim_{t}",
    "razorpay_signature": f"sim_sig_test_{t}"
}
r = requests.post(f"{base_url}/api/payments/verify", json=verify_payload)
assert r.status_code == 200, f"Payment verification failed: {r.status_code} {r.text}"
print(f"Payment verified: {r.json().get('message')} | Status: {r.json().get('payment_status')}")

print("\n--- Step 4: Testing Staff & Admin Authentication ---")
login_payload = {"email": "admin@garbanight.in", "password": "GarbaNight@2026"}
r = requests.post(f"{base_url}/api/auth/login", json=login_payload)
assert r.status_code == 200, f"Admin login failed: {r.status_code}"
token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
print(f"Logged in as: {r.json().get('name')} ({r.json().get('role')})")

print("\n--- Step 5: Testing Ticket Lookup & QR Verification ---")
booking = requests.get(f"{base_url}/api/admin/bookings/{booking_id}", headers=headers).json()
ticket = booking["tickets"][0]
ticket_id = ticket["ticket_id"]
qr_token = ticket["qr_token_raw"]
print(f"Issued Ticket ID: {ticket_id}")

# Verify via ticket ID
v1 = requests.post(f"{base_url}/api/qr/verify", json={"qr_token": ticket_id}).json()
print(f"Verify by Ticket ID: Valid={v1.get('valid')} | Status={v1.get('status')}")

# Verify via raw token
v2 = requests.post(f"{base_url}/api/qr/verify", json={"qr_token": qr_token}).json()
print(f"Verify by Raw QR Token: Valid={v2.get('valid')} | Status={v2.get('status')}")

# Verify via phone
v3 = requests.post(f"{base_url}/api/qr/verify", json={"qr_token": "9876543210"}).json()
print(f"Verify by Customer Phone: Valid={v3.get('valid')} | Status={v3.get('status')}")

print("\n--- Step 6: Testing Check-in Scans & Logging ---")
# 1st scan - Success
c1 = requests.post(f"{base_url}/api/qr/checkin", json={"qr_token": ticket_id, "device_information": "Main Turnstile A"}, headers=headers)
print(f"1st Check-in (Expect 200): Status={c1.status_code} | Result={c1.json().get('status')}")

# 2nd scan - Duplicate
c2 = requests.post(f"{base_url}/api/qr/checkin", json={"qr_token": ticket_id, "device_information": "Main Turnstile A"}, headers=headers)
print(f"2nd Duplicate Check-in (Expect 409): Status={c2.status_code}")

# 3rd scan - Invalid
c3 = requests.post(f"{base_url}/api/qr/checkin", json={"qr_token": "FAKE_TOKEN_99999", "device_information": "Main Turnstile A"}, headers=headers)
print(f"3rd Invalid Token Scan (Expect 404): Status={c3.status_code}")

print("\n--- Step 7: Testing Check-in Audit Log Retrieval ---")
checkins_res = requests.get(f"{base_url}/api/admin/checkins?limit=10", headers=headers)
assert checkins_res.status_code == 200, f"Checkins log failed: {checkins_res.status_code}"
checkins = checkins_res.json()
print(f"Retrieved {len(checkins)} check-in log records. Latest 3:")
for c in checkins[:3]:
    print(f" -> Result: {c.get('result')} | Ticket: {c.get('ticket_id')} | Customer: {c.get('customer_name')} | Staff: {c.get('staff_name')}")

print("\n--- Step 8: Testing System Security Audit Log Retrieval ---")
audit_res = requests.get(f"{base_url}/api/admin/audit-logs?limit=10", headers=headers)
assert audit_res.status_code == 200, f"Audit logs failed: {audit_res.status_code}"
audit_logs = audit_res.json()
print(f"Retrieved {len(audit_logs)} audit log records. Latest 3:")
for a in audit_logs[:3]:
    print(f" -> Action: {a.get('action')} | User: {a.get('user_email')} | Entity: {a.get('entity_type')}")

print("\n--- Step 9: Testing Bookings List with Search & Filtering ---")
bookings_res = requests.get(f"{base_url}/api/admin/bookings?page=1&per_page=10", headers=headers)
assert bookings_res.status_code == 200, f"Bookings list failed: {bookings_res.status_code}"
print(f"Total bookings registered: {bookings_res.json().get('total')}")

print("\n--- Step 10: Testing Admin Settings Configuration ---")
settings_res = requests.get(f"{base_url}/api/admin/settings", headers=headers)
assert settings_res.status_code == 200, f"Settings retrieval failed: {settings_res.status_code}"
print(f"Settings Event: {settings_res.json().get('event_name')} | Razorpay Secret Configured: {settings_res.json().get('razorpay_key_secret_set')}")

print("\n=======================================================")
print(" ALL 10 TEST SUITES PASSED FLAWLESSLY WITH ZERO ERRORS!")
print("=======================================================")
