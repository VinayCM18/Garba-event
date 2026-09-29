from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(String(100), unique=True, index=True, nullable=False)  # GN26-TKT-00048291-01
    booking_id = Column(Integer, ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_name = Column(String(255), nullable=False)
    event_name = Column(String(255), default="NAVRANG 2026", nullable=False)
    
    # QR Cryptographic Security
    qr_token_hash = Column(String(128), unique=True, index=True, nullable=False) # SHA-256 of raw secret token
    qr_token_raw = Column(String(128), unique=True, index=True, nullable=False)  # Secret token for public link / verification
    
    # Statuses
    ticket_status = Column(String(50), default="VALID", index=True, nullable=False) # VALID, USED, CANCELLED, REFUNDED
    checkin_status = Column(Boolean, default=False, index=True, nullable=False)
    checked_in_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True, nullable=False)

    # Relationships
    booking = relationship("Booking", back_populates="tickets")
    checkins = relationship("CheckIn", back_populates="ticket", cascade="all, delete-orphan")
