from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Normalize postgres:// to postgresql:// for compatibility with SQLAlchemy 2+
db_url = settings.DATABASE_URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

connect_args = {}
if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
    engine = create_engine(db_url, connect_args=connect_args)
else:
    engine = create_engine(
        db_url,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def sync_database_schema():
    """Ensures newly added columns in models are automatically present in existing databases."""
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    table_names = inspector.get_table_names()

    with engine.connect() as conn:
        if "event_settings" in table_names:
            cols = {col["name"] for col in inspector.get_columns("event_settings")}
            new_cols = [
                ("owner_notification_email", "VARCHAR(255) DEFAULT ''"),
                ("owner_notification_phone", "VARCHAR(50) DEFAULT '+91 98765 43210'"),
                ("owner_notification_enabled", "BOOLEAN DEFAULT 1"),
                ("owner_webhook_url", "VARCHAR(500) DEFAULT NULL"),
                ("smtp_host", "VARCHAR(255) DEFAULT 'smtp.gmail.com'"),
                ("smtp_port", "INTEGER DEFAULT 587"),
                ("smtp_username", "VARCHAR(255) DEFAULT NULL"),
                ("smtp_password", "VARCHAR(255) DEFAULT NULL"),
                ("smtp_from_email", "VARCHAR(255) DEFAULT 'tickets@garbanight.in'"),
                ("smtp_from_name", "VARCHAR(255) DEFAULT 'GARBA NIGHT 2026'"),
                ("smtp_use_tls", "BOOLEAN DEFAULT 1"),
                ("razorpay_key_id", "VARCHAR(255) DEFAULT NULL"),
                ("razorpay_key_secret", "VARCHAR(255) DEFAULT NULL"),
                ("razorpay_webhook_secret", "VARCHAR(255) DEFAULT NULL"),
                ("group_offer_enabled", "BOOLEAN DEFAULT 1"),
                ("group_offer_size", "INTEGER DEFAULT 10"),
                ("group_offer_free_tickets", "INTEGER DEFAULT 1"),
                ("payment_method", "VARCHAR(50) DEFAULT 'UPI_MANUAL'"),
                ("upi_id", "VARCHAR(255) DEFAULT 'samaymadhyastha2005@oksbi'"),
                ("upi_qr_image", "VARCHAR(255) DEFAULT 'uploads/qr/upi_qr.jpg'"),
                ("upi_payment_instructions", "TEXT DEFAULT 'Scan the QR code using any UPI app (GPay, PhonePe, Paytm, etc.). After paying, enter your UTR / Transaction ID.'"),
            ]
            for col_name, col_type in new_cols:
                if col_name not in cols:
                    try:
                        conn.execute(text(f"ALTER TABLE event_settings ADD COLUMN {col_name} {col_type}"))
                        conn.commit()
                        logger.info(f"Added column {col_name} to event_settings.")
                    except Exception as e:
                        logger.warning(f"Could not add column {col_name} to event_settings: {e}")

        if "bookings" in table_names:
            cols = {col["name"] for col in inspector.get_columns("bookings")}
            booking_new_cols = [
                ("regular_amount", "FLOAT DEFAULT 0.0"),
                ("group_discount", "FLOAT DEFAULT 0.0"),
                ("ticket_subtotal", "FLOAT DEFAULT 0.0"),
                ("payment_fee", "FLOAT DEFAULT 0.0"),
                ("gst_amount", "FLOAT DEFAULT 0.0"),
                ("razorpay_order_id", "VARCHAR(100) DEFAULT NULL"),
                ("razorpay_payment_id", "VARCHAR(100) DEFAULT NULL"),
                ("razorpay_signature", "VARCHAR(255) DEFAULT NULL"),
                ("owner_notified", "BOOLEAN DEFAULT 0"),
                ("owner_notified_at", "DATETIME DEFAULT NULL"),
                ("owner_notify_error", "TEXT DEFAULT NULL"),
                ("payment_method", "VARCHAR(50) DEFAULT 'UPI_MANUAL'"),
                ("utr_number", "VARCHAR(100) DEFAULT NULL"),
                ("payment_screenshot", "VARCHAR(255) DEFAULT NULL"),
                ("verified_by", "VARCHAR(100) DEFAULT NULL"),
                ("verified_at", "DATETIME DEFAULT NULL"),
                ("rejection_reason", "TEXT DEFAULT NULL"),
            ]
            for col_name, col_type in booking_new_cols:
                if col_name not in cols:
                    try:
                        conn.execute(text(f"ALTER TABLE bookings ADD COLUMN {col_name} {col_type}"))
                        conn.commit()
                        logger.info(f"Added column {col_name} to bookings.")
                    except Exception as e:
                        logger.warning(f"Could not add column {col_name} to bookings: {e}")

        if "payments" in table_names:
            cols = {col["name"] for col in inspector.get_columns("payments")}
            payment_new_cols = [
                ("payment_id", "VARCHAR(100) DEFAULT NULL"),
                ("payment_method", "VARCHAR(50) DEFAULT 'RAZORPAY'"),
                ("currency", "VARCHAR(10) DEFAULT 'INR'"),
                ("payment_status", "VARCHAR(50) DEFAULT 'PENDING'"),
                ("razorpay_order_id", "VARCHAR(100) DEFAULT NULL"),
                ("razorpay_payment_id", "VARCHAR(100) DEFAULT NULL"),
                ("razorpay_signature", "VARCHAR(255) DEFAULT NULL"),
                ("idempotency_key", "VARCHAR(100) DEFAULT NULL"),
                ("raw_response", "TEXT DEFAULT NULL"),
                ("utr_number", "VARCHAR(100) DEFAULT NULL"),
                ("payment_screenshot", "VARCHAR(255) DEFAULT NULL"),
                ("verified_by", "VARCHAR(100) DEFAULT NULL"),
                ("verified_at", "DATETIME DEFAULT NULL"),
                ("rejection_reason", "TEXT DEFAULT NULL"),
            ]
            for col_name, col_type in payment_new_cols:
                if col_name not in cols:
                    try:
                        conn.execute(text(f"ALTER TABLE payments ADD COLUMN {col_name} {col_type}"))
                        conn.commit()
                        logger.info(f"Added column {col_name} to payments.")
                    except Exception as e:
                        logger.warning(f"Could not add column {col_name} to payments: {e}")

        # Ensure event_settings matches required ₹599.00 pricing and Razorpay configuration
        if "event_settings" in table_names:
            try:
                conn.execute(text("UPDATE event_settings SET ticket_price = 599.0 WHERE ticket_price = 300.0 OR ticket_price IS NULL"))
                conn.commit()
            except Exception as e:
                logger.warning(f"Could not update event_settings ticket_price: {e}")

