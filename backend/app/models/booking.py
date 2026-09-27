from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(String(50), unique=True, index=True, nullable=False)  # GN-2026-XXXXX
    customer_name = Column(String(255), nullable=False)
    email = Column(String(255), index=True, nullable=False)
    phone = Column(String(50), index=True, nullable=False)
    ticket_count = Column(Integer, nullable=False)
    ticket_price = Column(Float, nullable=False)
    regular_amount = Column(Float, default=0.0, nullable=False)   # ticket_count × ticket_price before discount
    group_discount = Column(Float, default=0.0, nullable=False)   # BUY 10 PAY FOR 9 discount amount
    ticket_subtotal = Column(Float, default=0.0, nullable=False)  # after group discount
    convenience_fee = Column(Float, default=0.0, nullable=False)  # Payment Processing Fee
    payment_fee = Column(Float, default=0.0, nullable=False)      # Payment Processing Fee
    gst_amount = Column(Float, default=0.0, nullable=False)       # 18% GST on processing fee
    amount = Column(Float, nullable=False)  # total amount (subtotal + fee + gst)
    currency = Column(String(10), default="INR", nullable=False)
    
    # Payment & Provider Details
    payment_method = Column(String(50), default="UPI_MANUAL", nullable=False) # UPI_MANUAL, RAZORPAY
    utr_number = Column(String(100), index=True, nullable=True)
    payment_screenshot = Column(String(255), nullable=True)
    verified_by = Column(String(100), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # Razorpay Transaction Identifiers (for future / alternative provider)
    razorpay_order_id = Column(String(100), index=True, nullable=True)
    razorpay_payment_id = Column(String(100), index=True, nullable=True)
    razorpay_signature = Column(String(255), nullable=True)
    
    # Statuses
    # payment_status: PENDING, VERIFICATION_PENDING, PAID, FAILED, REJECTED, REFUNDED, CANCELLED
    payment_status = Column(String(50), default="PENDING", index=True, nullable=False)
    # booking_status: PAYMENT_PENDING, PAYMENT_VERIFICATION_PENDING, CONFIRMED, PAYMENT_FAILED, CANCELLED
    booking_status = Column(String(50), default="PAYMENT_PENDING", index=True, nullable=False)
    
    # Idempotency & Tracking
    idempotency_key = Column(String(100), unique=True, nullable=True, index=True)
    
    # Email Delivery Tracking
    email_status = Column(String(50), default="PENDING", nullable=False) # PENDING, SENT, FAILED, NOT_CONFIGURED
    email_sent_at = Column(DateTime, nullable=True)
    email_error = Column(Text, nullable=True)
    
    # Owner Notification Tracking
    owner_notified = Column(Boolean, default=False, nullable=False)
    owner_notified_at = Column(DateTime, nullable=True)
    owner_notify_error = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    tickets = relationship("Ticket", back_populates="booking", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="booking", cascade="all, delete-orphan")
