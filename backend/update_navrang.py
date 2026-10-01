"""
update_navrang.py — One-time seed/update script for NAVRANG 2026 event settings.

USAGE:
  Set SMTP_USERNAME, SMTP_PASSWORD, OWNER_NOTIFICATION_EMAIL, etc. in backend/.env
  BEFORE running this script.  Credentials are loaded from environment — never
  hard-coded here.

  cd backend
  python update_navrang.py
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.event_setting import EventSetting
from app.config import settings


def update_event_to_navrang():
    db = SessionLocal()
    try:
        setting = db.query(EventSetting).first()
        if not setting:
            setting = EventSetting()
            db.add(setting)

        setting.event_name = "NAVRANG 2026"
        setting.event_tagline = "Celebrate. Dance. Connect."
        setting.event_date = "October 17, 2026"
        setting.event_time = "06:30 PM - 10:00 PM"
        setting.venue_name = "The Green Acres"
        setting.venue_address = "The Green Acres, Mysuru"
        setting.venue_city = "Mysuru"
        setting.ticket_price = 599.0
        setting.convenience_fee = 0.0
        setting.total_capacity = 1500

        # Load sensitive values from environment variables — never hard-code them
        owner_email = settings.OWNER_NOTIFICATION_EMAIL
        owner_phone = settings.OWNER_NOTIFICATION_PHONE
        smtp_user = settings.SMTP_USERNAME
        smtp_pass = settings.SMTP_PASSWORD
        from_email = settings.FROM_EMAIL

        if owner_email:
            setting.owner_notification_email = owner_email
        if owner_phone:
            setting.owner_notification_phone = owner_phone
        if from_email:
            setting.contact_email = from_email
        if owner_phone:
            setting.contact_phone = owner_phone

        setting.smtp_from_name = "NAVRANG 2026"

        # SMTP credentials — sourced from .env, not hard-coded
        if smtp_user:
            setting.smtp_username = smtp_user
        if smtp_pass:
            setting.smtp_password = smtp_pass
        if from_email:
            setting.smtp_from_email = from_email

        db.commit()
        print(f"SUCCESS: EventSetting updated to NAVRANG 2026, Date: Oct 16 2026, "
              f"Venue: Serenity Groove, Price: Rs 599, Owner: {owner_email or '(not set)'}")
    except Exception as e:
        db.rollback()
        print("ERROR:", e)
    finally:
        db.close()


if __name__ == "__main__":
    update_event_to_navrang()
