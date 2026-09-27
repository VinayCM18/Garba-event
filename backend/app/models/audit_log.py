from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(100), nullable=False, index=True) # LOGIN, LOGOUT, BOOKING_CREATED, PAYMENT_VERIFIED, CHECKIN_SUCCESS, CHECKIN_FAILED, SETTINGS_UPDATED
    entity_type = Column(String(50), nullable=False) # booking, ticket, payment, user, setting
    entity_id = Column(String(100), nullable=True)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(255), nullable=True)
    details = Column(Text, nullable=True) # JSON metadata
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="audit_logs")
