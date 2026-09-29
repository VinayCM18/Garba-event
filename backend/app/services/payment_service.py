import os
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.config import settings
from app.models.event_setting import EventSetting
from app.models.booking import Booking
from app.models.user import User
from app.utils.logger import app_logger
from app.services.payment_providers.base import BasePaymentProvider
from app.services.payment_providers.manual_upi import ManualUPIPaymentProvider
from app.services.payment_providers.razorpay_provider import RazorpayPaymentProvider

class PaymentService:
    """
    Core Payment Service Abstraction.
    Decouples the booking and ticketing systems from specific payment gateways.
    Allows seamlessly toggling between Manual UPI and Razorpay via settings.
    """
    def __init__(self):
        self.manual_upi_provider = ManualUPIPaymentProvider()
        self.razorpay_provider = RazorpayPaymentProvider()

    def get_provider(self, db: Session) -> BasePaymentProvider:
        """
        Deterministically resolves the active payment provider.
        Priority:
        1. Environment variables PAYMENT_PROVIDER or PAYMENT_METHOD (checked directly in os.environ and settings).
           - "RAZORPAY" / "RZP" -> RazorpayPaymentProvider
           - "UPI_MANUAL" / "MANUAL_UPI" / "UPI" -> ManualUPIPaymentProvider
        2. Database EventSetting.payment_method ONLY when environment variables are intentionally unset/empty.
        3. Defaults to RazorpayPaymentProvider.
        """
        # Step 1: Check environment variables first (case-insensitive & whitespace trimmed)
        env_raw = (
            os.environ.get("PAYMENT_PROVIDER")
            or os.environ.get("PAYMENT_METHOD")
            or getattr(settings, "PAYMENT_PROVIDER", None)
            or getattr(settings, "PAYMENT_METHOD", None)
            or ""
        )
        if isinstance(env_raw, str):
            env_val = env_raw.strip().upper()
            if env_val in ("RAZORPAY", "RZP"):
                return self.razorpay_provider
            elif env_val in ("UPI_MANUAL", "MANUAL_UPI", "UPI"):
                return self.manual_upi_provider

        # Step 2: Fallback to database setting ONLY when environment is intentionally unset/empty
        try:
            setting = db.query(EventSetting).first() if db else None
            if setting and getattr(setting, "payment_method", None):
                db_method = str(setting.payment_method).strip().upper()
                if db_method in ("UPI_MANUAL", "MANUAL_UPI", "UPI"):
                    return self.manual_upi_provider
                elif db_method in ("RAZORPAY", "RZP"):
                    return self.razorpay_provider
        except Exception as e:
            app_logger.warning(f"Could not read payment_method from EventSetting: {e}")

        # Step 3: Default to Razorpay
        return self.razorpay_provider

    def get_provider_by_code(self, provider_code: str) -> BasePaymentProvider:
        """Returns a specific provider instance by code name."""
        if (provider_code or "").strip().upper() == "UPI_MANUAL":
            return self.manual_upi_provider
        return self.razorpay_provider


    def calculate_pricing(self, db: Session, ticket_count: int, ticket_phase_code: Optional[str] = None) -> Dict[str, Any]:
        """Calculates server-side pricing breakdown using the active payment provider and ticket phase."""
        provider = self.get_provider(db)
        return provider.calculate_pricing(db=db, ticket_count=ticket_count, ticket_phase_code=ticket_phase_code)

    def initiate_payment_order(
        self,
        booking: Booking,
        db: Session,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Initializes payment checkout details using the active provider."""
        provider = self.get_provider(db)
        return provider.initiate_payment(booking=booking, db=db, idempotency_key=idempotency_key)

    def submit_manual_proof(
        self,
        booking_id: str,
        utr_number: str,
        screenshot_filename: Optional[str],
        db: Session
    ) -> Booking:
        """Records customer-submitted UTR and screenshot for manual verification."""
        return self.manual_upi_provider.submit_payment_proof(
            booking_id=booking_id,
            utr_number=utr_number,
            screenshot_filename=screenshot_filename,
            db=db
        )

    def approve_manual_payment(
        self,
        booking_id: str,
        admin_user: User,
        db: Session
    ) -> Booking:
        """Approves a manual UPI payment, generating tickets and emailing the customer."""
        return self.manual_upi_provider.approve_payment(
            booking_id=booking_id,
            admin_user=admin_user,
            db=db
        )

    def reject_manual_payment(
        self,
        booking_id: str,
        reason: str,
        admin_user: User,
        db: Session
    ) -> Booking:
        """Rejects a manual UPI payment with a reason."""
        return self.manual_upi_provider.reject_payment(
            booking_id=booking_id,
            reason=reason,
            admin_user=admin_user,
            db=db
        )

    # Razorpay compatibility delegates
    def create_razorpay_order(
        self,
        amount_inr: float,
        booking_id: str,
        db: Session,
        idempotency_key: str = None
    ) -> dict:
        booking = db.query(Booking).filter(Booking.booking_id == booking_id).first()
        if not booking:
            raise ValueError(f"Booking {booking_id} not found.")
        return self.razorpay_provider.initiate_payment(booking, db, idempotency_key=idempotency_key)

    def verify_payment(
        self,
        order_id: str,
        payment_id: str,
        signature: str,
        db: Session
    ) -> bool:
        result = self.razorpay_provider.verify_payment(
            db=db,
            order_id=order_id,
            payment_id=payment_id,
            signature=signature
        )
        if isinstance(result, bool):
            return result
        if isinstance(result, dict):
            return bool(result.get("verified", False))
        return False

    def process_webhook(self, body_bytes: bytes, signature: str, db: Session) -> dict:
        return self.razorpay_provider.process_webhook(body_bytes, signature, db)

    def _get_credentials(self, db: Session):
        return self.razorpay_provider._get_credentials(db)

payment_service = PaymentService()
