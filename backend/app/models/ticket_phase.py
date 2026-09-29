from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from datetime import datetime
from app.database import Base

class TicketPhase(Base):
    __tablename__ = "ticket_phases"

    id = Column(Integer, primary_key=True, index=True)
    phase_code = Column(String(50), unique=True, index=True, nullable=False) # EARLY_BIRD, PHASE_1, PHASE_2, PHASE_3
    name = Column(String(100), nullable=False)                                # "Early Bird", "Phase 1", "Phase 2"
    price = Column(Float, nullable=False, default=599.0)
    tax_included = Column(Boolean, default=True, nullable=False)
    status = Column(String(50), default="LOCKED", nullable=False)            # ACTIVE, LOCKED, SOLD_OUT, COMPLETED
    total_inventory = Column(Integer, default=500, nullable=False)
    sold_count = Column(Integer, default=0, nullable=False)
    display_order = Column(Integer, default=1, nullable=False)
    badge_text = Column(String(50), default="COMING SOON", nullable=True)     # "AVAILABLE NOW", "COMING SOON", "LOCKED"
    description = Column(String(255), nullable=True)
    group_offer_eligible = Column(Boolean, default=False, nullable=False)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
