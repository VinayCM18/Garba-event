from sqlalchemy import Column, Integer, String, Float, Boolean, Text, DateTime
from datetime import datetime
from app.database import Base

class EventSetting(Base):
    __tablename__ = "event_settings"

    id = Column(Integer, primary_key=True, index=True)
    event_name = Column(String(255), default="NAVRANG 2026", nullable=False)
    event_tagline = Column(String(255), default="Celebrate. Dance. Connect.", nullable=False)
    event_date = Column(String(100), default="October 17, 2026", nullable=False)
    event_time = Column(String(100), default="06:30 PM - 10:00 PM", nullable=False)
    venue_name = Column(String(255), default="Green Acres", nullable=False)
    venue_address = Column(String(255), default="Green Acres, Mysuru", nullable=False)
    venue_city = Column(String(100), default="Mysuru", nullable=False)
    ticket_price = Column(Float, default=599.0, nullable=False)
    convenience_fee = Column(Float, default=0.0, nullable=False)
    total_capacity = Column(Integer, default=1500, nullable=False)
    max_per_booking = Column(Integer, default=10, nullable=False)
    # Group Offer: Group of 10
    group_offer_enabled = Column(Boolean, default=True, nullable=False)
    group_offer_size = Column(Integer, default=10, nullable=False)       # number of tickets to qualify
    group_offer_free_tickets = Column(Integer, default=1, nullable=False) # free tickets given
    booking_open = Column(Boolean, default=True, nullable=False)
    contact_email = Column(String(255), default="Samaymadhyastha2005@gmail.com", nullable=False)
    contact_phone = Column(String(50), default="+91 74831 39146", nullable=False)
    rules_text = Column(Text, default="1. Traditional festive attire (Chaniya Choli / Kurta Pajama) mandatory.\n2. Entry valid only with authentic QR code.\n3. Outside food, alcohol, and weapons strictly prohibited.\n4. Dandiya sticks available inside venue.\n5. Non-transferable ticket; duplicate entry forbidden.", nullable=False)

    # Owner Instant Notification Settings
    owner_notification_email = Column(String(255), default="", nullable=False)
    owner_notification_phone = Column(String(50), default="", nullable=False)
    owner_notification_enabled = Column(Boolean, default=True, nullable=False)
    owner_webhook_url = Column(String(500), nullable=True)

    # Dynamic SMTP & Resend API Credentials (Editable via Admin Settings)
    email_provider = Column(String(50), default="resend", nullable=False) # "resend", "smtp", or "console"
    resend_api_key = Column(String(255), nullable=True)
    smtp_host = Column(String(255), default="smtp.gmail.com", nullable=False)
    smtp_port = Column(Integer, default=587, nullable=False)
    smtp_username = Column(String(255), nullable=True)
    smtp_password = Column(String(255), nullable=True)
    smtp_from_email = Column(String(255), default="tickets@garbanight.in", nullable=False)
    smtp_from_name = Column(String(255), default="NAVRANG 2026", nullable=False)
    # Dynamic Razorpay Payment Gateway Credentials (Editable via Admin Settings)
    razorpay_key_id = Column(String(255), nullable=True)
    razorpay_key_secret = Column(String(255), nullable=True)
    razorpay_webhook_secret = Column(String(255), nullable=True)

    # Dynamic Payment Provider / Manual UPI Settings (Editable via Admin Settings)
    payment_method = Column(String(50), default="RAZORPAY", nullable=False) # RAZORPAY or UPI_MANUAL
    upi_id = Column(String(255), default="samaymadhyastha2005@oksbi", nullable=False)
    upi_qr_image = Column(String(255), default="uploads/qr/upi_qr.jpg", nullable=False)
    upi_payment_instructions = Column(Text, default="Scan the QR code using any UPI app (Google Pay, PhonePe, Paytm, etc.). After payment, enter your UTR / Transaction ID and upload screenshot.", nullable=False)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

