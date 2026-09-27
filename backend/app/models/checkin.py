from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class CheckIn(Base):
    __tablename__ = "checkins"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=True, index=True)
    staff_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    checked_in_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    device_information = Column(String(255), nullable=True)
    ip_address = Column(String(50), nullable=True)
    result = Column(String(50), nullable=False) # SUCCESS, ALREADY_USED, INVALID, CANCELLED
    notes = Column(Text, nullable=True)

    # Relationships
    ticket = relationship("Ticket", back_populates="checkins")
    staff = relationship("User", back_populates="checkins")
