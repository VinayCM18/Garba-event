from typing import Optional, Dict, Any, List
import random
import string
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status
from app.models.booking import Booking
from app.models.ticket import Ticket
from app.models.payment import Payment
from app.models.event_setting import EventSetting
from app.models.audit_log import AuditLog
from app.services.qr_service import qr_service
from app.services.email_service import email_service
from app.utils.logger import app_logger

class BookingService:
    @staticmethod
    def generate_booking_id(db: Session) -> str:
        """Generates a unique booking ID e.g. GN-2026-48291 or GN48291."""
        for _ in range(10):
            num = random.randint(10000, 99999)
            candidate = f"GN-2026-{num}"
            exists = db.query(Booking).filter(Booking.booking_id == candidate).first()
            if not exists:
                return candidate
        # Fallback with letters
        suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
        return f"GN-2026-{suffix}"

    @staticmethod
    def check_capacity(db: Session, requested_tickets: int) -> tuple[bool, int, int]:
        """Calculates capacity and checks if requested tickets can be fulfilled.
        Returns: (is_available, remaining_tickets, total_capacity)"""
        event_setting = db.query(EventSetting).first()
        if not event_setting:
            event_setting = EventSetting()
            db.add(event_setting)
            db.commit()

        if not event_setting.booking_open:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ticket booking is currently closed."
            )

        # Count sold tickets for confirmed or paid bookings
        sold_tickets = db.query(func.coalesce(func.sum(Booking.ticket_count), 0)).filter(
            Booking.booking_status == "CONFIRMED",
            Booking.payment_status == "PAID"
        ).scalar() or 0

        remaining = max(0, event_setting.total_capacity - sold_tickets)
        if requested_tickets > remaining:
            return False, remaining, event_setting.total_capacity
        return True, remaining, event_setting.total_capacity

    @classmethod
    def calculate_pricing(cls, db: Session, ticket_count: int, ticket_phase: Optional[str] = "EARLY_BIRD") -> dict:
        """Calculates exact server-side pricing breakdown via payment_service."""
        from app.services.payment_service import payment_service
        return payment_service.calculate_pricing(db=db, ticket_count=ticket_count, ticket_phase_code=ticket_phase)

    @classmethod
    def initiate_order(
        cls,
        customer_name: str,
        email: str,
        phone: str,
        ticket_count: int,
        db: Session,
        ticket_phase: Optional[str] = "EARLY_BIRD",
        idempotency_key: str = None
    ) -> tuple[Booking, dict]:
        """Validates capacity, initializes pending booking, and returns payment checkout info."""
        event_setting = db.query(EventSetting).first()
        if not event_setting:
            event_setting = EventSetting()
            db.add(event_setting)
            db.commit()

        if ticket_count > event_setting.max_per_booking:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Maximum {event_setting.max_per_booking} tickets allowed per booking."
            )

        # Check capacity
        is_avail, remaining, _ = cls.check_capacity(db, requested_tickets=ticket_count)
        if not is_avail:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Only {remaining} tickets remaining. Cannot book {ticket_count} tickets."
            )

        from app.services.payment_service import payment_service
        provider = payment_service.get_provider(db)

        # Calculate exact server-side pricing for requested ticket phase
        pricing = provider.calculate_pricing(db, ticket_count, ticket_phase_code=ticket_phase)
        total_amount = pricing["total_amount"]

        # Idempotency check: If an order with this key already exists, return it
        if idempotency_key:
            existing_booking = db.query(Booking).filter(Booking.idempotency_key == idempotency_key).first()
            if existing_booking:
                existing_payment = db.query(Payment).filter(Payment.booking_id == existing_booking.id).first()
                upi_id = getattr(event_setting, "upi_id", None) or settings.UPI_ID
                upi_instructions = getattr(event_setting, "upi_payment_instructions", None) or settings.UPI_PAYMENT_INSTRUCTIONS
                key_id, _, _, mode = payment_service._get_credentials(db)

                method = existing_booking.payment_method or provider.provider_code
                is_razorpay = (method == "RAZORPAY")

                return existing_booking, {
                    "payment_method": method,
                    "payment_id": existing_payment.payment_id if existing_payment else f"PAY-{existing_booking.booking_id}",
                    "booking_id": existing_booking.booking_id,
                    "ticket_phase": existing_booking.ticket_phase or pricing.get("ticket_phase", "EARLY_BIRD"),
                    "phase_name": pricing.get("phase_name", "Early Bird"),
                    "ticket_price": existing_booking.ticket_price,
                    "ticket_count": existing_booking.ticket_count,
                    "regular_amount": existing_booking.regular_amount or pricing["regular_amount"],
                    "group_discount": existing_booking.group_discount or pricing["group_discount"],
                    "ticket_subtotal": existing_booking.ticket_subtotal or pricing["ticket_subtotal"],
                    "payment_fee": existing_booking.payment_fee or pricing["payment_fee"],
                    "gst_amount": existing_booking.gst_amount or pricing["gst_amount"],
                    "amount": existing_booking.amount,
                    "currency": existing_booking.currency,
                    "is_group_offer": (existing_booking.group_discount or 0) > 0,
                    "offer_name": "BUY 10, PAY FOR 9" if (existing_booking.group_discount or 0) > 0 else None,
                    "upi_id": None if is_razorpay else upi_id,
                    "upi_qr_image_url": None if is_razorpay else "/api/payments/qr-image",
                    "upi_payment_instructions": None if is_razorpay else upi_instructions,
                    "razorpay_order_id": (existing_payment.razorpay_order_id if existing_payment and existing_payment.razorpay_order_id else existing_booking.razorpay_order_id) if is_razorpay else None,
                    "key_id": key_id if is_razorpay else None,
                    "is_simulation": False
                }

        booking_id = cls.generate_booking_id(db)

        # Create Pending Booking with full fee breakdown
        new_booking = Booking(
            booking_id=booking_id,
            customer_name=customer_name.strip(),
            email=email.strip().lower(),
            phone=phone.strip(),
            ticket_count=ticket_count,
            ticket_phase=pricing.get("ticket_phase", "EARLY_BIRD"),
            ticket_price=pricing["ticket_price"],
            regular_amount=pricing["regular_amount"],
            group_discount=pricing["group_discount"],
            ticket_subtotal=pricing["ticket_subtotal"],
            convenience_fee=pricing["payment_fee"],
            payment_fee=pricing["payment_fee"],
            gst_amount=pricing["gst_amount"],
            amount=total_amount,
            currency="INR",
            payment_method=provider.provider_code,
            payment_status="PENDING",
            booking_status="PAYMENT_PENDING",
            idempotency_key=idempotency_key
        )
        db.add(new_booking)
        db.flush()

        # Delegate checkout initialization to the active payment provider
        order_info = payment_service.initiate_payment_order(
            booking=new_booking,
            db=db,
            idempotency_key=idempotency_key
        )

        order_info.update({
            "ticket_phase": pricing.get("ticket_phase", "EARLY_BIRD"),
            "phase_name": pricing.get("phase_name", "Early Bird"),
            "ticket_price": pricing["ticket_price"],
            "ticket_count": ticket_count,
            "regular_amount": pricing["regular_amount"],
            "group_discount": pricing["group_discount"],
            "ticket_subtotal": pricing["ticket_subtotal"],
            "payment_fee": pricing["payment_fee"],
            "gst_amount": pricing["gst_amount"],
            "amount": total_amount,
            "currency": "INR",
            "is_group_offer": pricing["is_group_offer"],
            "offer_name": pricing["offer_name"],
            "free_tickets": pricing.get("free_tickets", 0),
        })

        return new_booking, order_info

    @classmethod
    def confirm_booking_and_generate_tickets(
        cls,
        booking_id: str,
        razorpay_payment_id: str = None,
        razorpay_signature: str = None,
        db: Session = None,
        payment_method: str = "online",
        verified_by: str = None
    ) -> Booking:
        """Atomically marks booking as confirmed, updates payment status, generates tickets with QR codes."""
        # Row-level locking to prevent race conditions
        booking = db.query(Booking).filter(Booking.booking_id == booking_id).with_for_update().first()
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found.")

        # Idempotent: If already confirmed, return directly
        if booking.booking_status == "CONFIRMED" and booking.payment_status in ["PAID", "CAPTURED"]:
            return booking

        now = datetime.utcnow()
        is_razorpay = (payment_method == "RAZORPAY" or booking.payment_method == "RAZORPAY")
        resolved_payment_status = "CAPTURED" if is_razorpay else "PAID"

        # Update Payment record
        payment = db.query(Payment).filter(Payment.booking_id == booking.id).first()
        if payment:
            if razorpay_payment_id:
                payment.razorpay_payment_id = razorpay_payment_id
            if razorpay_signature:
                payment.razorpay_signature = razorpay_signature
            payment.payment_status = resolved_payment_status
            payment.status = "PAID"
            payment.payment_method = payment_method or payment.payment_method or "RAZORPAY"
            if verified_by:
                payment.verified_by = verified_by
            payment.verified_at = now
            payment.updated_at = now

        if razorpay_payment_id:
            booking.razorpay_payment_id = razorpay_payment_id
        if razorpay_signature:
            booking.razorpay_signature = razorpay_signature
        booking.payment_method = payment_method or booking.payment_method or ("RAZORPAY" if is_razorpay else "UPI_MANUAL")
        booking.payment_status = "PAID"
        booking.booking_status = "CONFIRMED"
        if verified_by:
            booking.verified_by = verified_by
        booking.verified_at = now
        booking.updated_at = now

        # Generate individual tickets if not yet created
        existing_tickets = db.query(Ticket).filter(Ticket.booking_id == booking.id).all()
        if not existing_tickets:
            event_setting = db.query(EventSetting).first()
            event_name = event_setting.event_name if event_setting else "NAVRANG 2026"
            clean_booking_num = booking.booking_id.replace("GN-2026-", "").replace("GN", "")

            for i in range(1, booking.ticket_count + 1):
                ticket_code = f"GN26-TKT-{clean_booking_num.zfill(6)}-{str(i).zfill(2)}"
                raw_token, token_hash = qr_service.generate_token_pair()

                ticket = Ticket(
                    ticket_id=ticket_code,
                    booking_id=booking.id,
                    customer_name=booking.customer_name,
                    event_name=event_name,
                    qr_token_hash=token_hash,
                    qr_token_raw=raw_token,
                    ticket_status="VALID",
                    checkin_status=False
                )
                db.add(ticket)

            db.add(AuditLog(
                action="TICKETS_GENERATED",
                entity_type="booking",
                entity_id=booking.booking_id,
                details=f'{{"ticket_count": {booking.ticket_count}}}'
            ))

        # Audit log entry
        audit = AuditLog(
            action="BOOKING_CONFIRMED",
            entity_type="booking",
            entity_id=booking.booking_id,
            details=f'{{"tickets": {booking.ticket_count}, "amount": {booking.amount}, "payment_method": "{booking.payment_method}", "verified_by": "{verified_by or "system"}"}}'
        )
        db.add(audit)

        db.commit()
        db.refresh(booking)

        # 1. Send customer ticket confirmation email safely (idempotent: avoid re-sending)
        if booking.email_status != "SENT":
            try:
                email_service.send_confirmation_email(booking.booking_id, db)
            except Exception as e:
                app_logger.error(f"Error dispatching confirmation email: {e}")

        # 2. Send instant notification message & email to event owner/organizer (idempotent)
        if not booking.owner_notified:
            try:
                email_service.send_owner_notification(booking.booking_id, db)
            except Exception as e:
                app_logger.error(f"Error dispatching owner notification: {e}")

        return booking

booking_service = BookingService()
