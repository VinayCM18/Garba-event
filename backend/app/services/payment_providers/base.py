from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.booking import Booking

class BasePaymentProvider(ABC):
    """
    Abstract Base Class for all payment providers.
    Enables pluggable payment gateways (Manual UPI, Razorpay, etc.)
    without modifying core booking, ticketing, or verification logic.
    """
    @property
    @abstractmethod
    def provider_code(self) -> str:
        """Unique provider identifier, e.g. 'UPI_MANUAL', 'RAZORPAY'."""
        pass

    @abstractmethod
    def calculate_pricing(self, db: Session, ticket_count: int, ticket_phase_code: Optional[str] = None) -> Dict[str, Any]:
        """Calculates server-side ticket pricing breakdown."""
        pass

    @abstractmethod
    def initiate_payment(
        self,
        booking: Booking,
        db: Session,
        idempotency_key: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Initializes payment order / checkout parameters for the booking."""
        pass

    @abstractmethod
    def verify_payment(self, db: Session, **kwargs) -> Dict[str, Any]:
        """Verifies payment transaction or signature."""
        pass
