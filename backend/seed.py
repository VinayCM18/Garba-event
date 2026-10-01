import sys
import os
from datetime import datetime, timedelta
import random

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import Base, engine, SessionLocal
from app.models.user import User
from app.models.event_setting import EventSetting
from app.models.booking import Booking
from app.models.ticket import Ticket
from app.models.payment import Payment
from app.models.checkin import CheckIn
from app.models.audit_log import AuditLog
from app.utils.security import get_password_hash
from app.services.qr_service import qr_service

def seed():
    print("Dropping existing tables and recreating schema...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        print("Seeding Event Settings...")
        setting = EventSetting(
            event_name="NAVRANG 2026",
            event_tagline="Celebrate. Dance. Connect.",
            event_date="October 17, 2026",
            event_time="06:30 PM - 10:00 PM",
            venue_name="The Green Acres",
            venue_address="The Green Acres, Mysuru",
            venue_city="Mysuru",
            ticket_price=300.0,
            convenience_fee=0.0,
            total_capacity=1500,
            max_per_booking=10,
            booking_open=True,
            contact_email="support@garbanight.in",
            contact_phone="+91 98765 43210",
            rules_text="1. Traditional attire (Chaniya Choli / Kurta Pajama) mandatory.\n2. Entry valid only with authentic QR code.\n3. Outside food, alcohol, and weapons strictly prohibited.\n4. Dandiya sticks available inside venue.\n5. Non-transferable ticket; duplicate entry forbidden."
        )
        db.add(setting)

        print("Seeding Users...")
        super_admin = User(
            email="admin@garbanight.local",
            name="Garba Night Lead Organizer",
            password_hash=get_password_hash("GarbaNight@2026"),
            role="SUPER_ADMIN",
            is_active=True
        )
        staff_user = User(
            email="staff@garbanight.local",
            name="Security Gate Scanner Staff",
            password_hash=get_password_hash("StaffEntry@2026"),
            role="CHECKIN_STAFF",
            is_active=True
        )
        db.add(super_admin)
        db.add(staff_user)
        db.flush()

        print("Seeding Sample Bookings and Tickets...")
        sample_customers = [
            ("Rahul Sharma", "rahul.sharma@example.com", "+919876543210", 4, 3), # 3 days ago
            ("Pooja Patel", "pooja.patel@example.com", "+919823456789", 2, 2),
            ("Amit Shah", "amit.shah@example.com", "+919765432101", 6, 2),
            ("Neha Verma", "neha.verma@example.com", "+919988776655", 3, 1),
            ("Vikram Joshi", "vikram.joshi@example.com", "+919811223344", 2, 1),
            ("Rohan Mehta", "rohan.mehta@example.com", "+919833445566", 5, 0), # today
            ("Ananya Desai", "ananya.desai@example.com", "+919844556677", 4, 0),
        ]

        ticket_counter = 1
        now = datetime.utcnow()

        for idx, (name, email, phone, count, days_ago) in enumerate(sample_customers):
            booking_id = f"GN-2026-{48291 + idx}"
            created_at = now - timedelta(days=days_ago, hours=random.randint(1, 10))
            amount = count * 300.0

            booking = Booking(
                booking_id=booking_id,
                customer_name=name,
                email=email,
                phone=phone,
                ticket_count=count,
                ticket_price=300.0,
                convenience_fee=0.0,
                amount=amount,
                currency="INR",
                payment_status="PAID",
                booking_status="CONFIRMED",
                email_status="SENT",
                email_sent_at=created_at + timedelta(minutes=1),
                created_at=created_at
            )
            db.add(booking)
            db.flush()

            # Payment record
            payment = Payment(
                booking_id=booking.id,
                razorpay_order_id=f"order_mock_{48291 + idx}",
                razorpay_payment_id=f"pay_mock_{48291 + idx}",
                razorpay_signature="sim_sig_valid_seed_data",
                amount=amount,
                currency="INR",
                status="PAID",
                payment_method="UPI",
                created_at=created_at
            )
            db.add(payment)

            # Tickets
            for t_idx in range(1, count + 1):
                clean_num = str(48291 + idx)
                ticket_code = f"GN26-TKT-{clean_num.zfill(6)}-{str(t_idx).zfill(2)}"
                raw_token, token_hash = qr_service.generate_token_pair()

                # Mark first few tickets as already checked in for demo
                is_checked_in = (days_ago >= 2 and t_idx <= 2)
                checkin_time = created_at + timedelta(hours=5) if is_checked_in else None

                ticket = Ticket(
                    ticket_id=ticket_code,
                    booking_id=booking.id,
                    customer_name=name,
                    event_name="GARBA NIGHT 2026",
                    qr_token_hash=token_hash,
                    qr_token_raw=raw_token,
                    ticket_status="USED" if is_checked_in else "VALID",
                    checkin_status=is_checked_in,
                    checked_in_at=checkin_time,
                    created_at=created_at
                )
                db.add(ticket)
                db.flush()

                if is_checked_in:
                    ci = CheckIn(
                        ticket_id=ticket.id,
                        staff_id=staff_user.id,
                        checked_in_at=checkin_time,
                        device_information="Camera Scanner Tab 01",
                        ip_address="192.168.1.101",
                        result="SUCCESS",
                        notes="Normal entry verification"
                    )
                    db.add(ci)

                ticket_counter += 1

            # Audit log
            audit = AuditLog(
                user_id=super_admin.id,
                action="BOOKING_CONFIRMED",
                entity_type="booking",
                entity_id=booking.booking_id,
                ip_address="127.0.0.1",
                details=f'{{"seed": true, "tickets": {count}}}',
                timestamp=created_at
            )
            db.add(audit)

        db.commit()
        print("Database seeded successfully!")
        print("---------------------------------------------")
        print("Super Admin Login: admin@garbanight.local / GarbaNight@2026")
        print("Staff Scanner Login: staff@garbanight.local / StaffEntry@2026")
        print("---------------------------------------------")

    except Exception as e:
        db.rollback()
        print(f"Error during seeding: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed()
