from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(String(100), unique=True, index=True, nullable=True) # e.g. PAY-UPI-GN-2026-..., or Razorpay payment ID
    booking_id = Column(Integer, ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False, index=True)
    payment_method = Column(String(50), default="UPI_MANUAL", nullable=False) # UPI_MANUAL, RAZORPAY
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="INR", nullable=False)
    payment_status = Column(String(50), default="PENDING", index=True, nullable=False) # PENDING, VERIFICATION_PENDING, PAID, FAILED, REJECTED
    status = Column(String(50), default="PENDING", index=True, nullable=False) # Alias for backwards compatibility
    
    # Manual UPI verification fields
    utr_number = Column(String(100), index=True, nullable=True)
    payment_screenshot = Column(String(255), nullable=True)
    verified_by = Column(String(100), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    # Razorpay Transaction Identifiers (for future / alternative provider)
    razorpay_order_id = Column(String(100), index=True, nullable=True)
    razorpay_payment_id = Column(String(100), index=True, nullable=True)
    razorpay_signature = Column(String(255), nullable=True)
    
    idempotency_key = Column(String(100), nullable=True)
    raw_response = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    booking = relationship("Booking", back_populates="payments")
