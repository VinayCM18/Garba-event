import os
from typing import Optional, Dict, Any, List
import random
import string
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status
from app.config import settings
from app.models.booking import Booking
from app.models.ticket import Ticket
from app.models.payment import Payment
from app.models.event_setting import EventSetting
from app.models.ticket_phase import TicketPhase
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
        Accounts for both confirmed sales and active unexpired reservations.
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

        now = datetime.utcnow()
        # Count sold tickets for confirmed or paid bookings
        sold_tickets = db.query(func.coalesce(func.sum(Booking.ticket_count), 0)).filter(
            Booking.booking_status == "CONFIRMED",
            Booking.payment_status.in_(["PAID", "CAPTURED"])
        ).scalar() or 0

        # Count active pending reservations (unexpired)
        reserved_tickets = db.query(func.coalesce(func.sum(Booking.ticket_count), 0)).filter(
            Booking.booking_status == "PAYMENT_PENDING",
            Booking.payment_status == "PENDING",
            Booking.reservation_expires_at > now
        ).scalar() or 0

        remaining = max(0, event_setting.total_capacity - (sold_tickets + reserved_tickets))
        if requested_tickets > remaining:
            return False, remaining, event_setting.total_capacity
        return True, remaining, event_setting.total_capacity

    @staticmethod
    def check_phase_capacity(db: Session, requested_tickets: int, phase_code: Optional[str] = "EARLY_BIRD") -> tuple[bool, int, Any]:
        """Validates phase status and capacity:
        - ACTIVE phase can be purchased
        - LOCKED, COMING_SOON, SOLD_OUT, or expired phases cannot be purchased
        - Reserves inventory temporarily without permanent oversell
        """
        code = (phase_code or "EARLY_BIRD").strip().upper()
        phase = db.query(TicketPhase).filter(TicketPhase.phase_code == code).first()
        if not phase:
            return True, 9999, None

        if phase.status != "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ticket phase '{phase.name}' is currently {phase.status.lower()} and cannot be purchased."
            )

        now = datetime.utcnow()
        if phase.start_time and now < phase.start_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ticket phase '{phase.name}' has not opened yet."
            )
        if phase.end_time and now > phase.end_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ticket phase '{phase.name}' has expired."
            )

        # Count confirmed sold for this phase
        confirmed_sold = db.query(func.coalesce(func.sum(Booking.ticket_count), 0)).filter(
            Booking.booking_status == "CONFIRMED",
            Booking.payment_status.in_(["PAID", "CAPTURED"]),
            Booking.ticket_phase == phase.phase_code
        ).scalar() or 0

        # Count active pending reservations for this phase
        active_reserved = db.query(func.coalesce(func.sum(Booking.ticket_count), 0)).filter(
            Booking.booking_status == "PAYMENT_PENDING",
            Booking.payment_status == "PENDING",
            Booking.ticket_phase == phase.phase_code,
            Booking.reservation_expires_at > now
        ).scalar() or 0

        phase_remaining = max(0, phase.total_inventory - (confirmed_sold + active_reserved))
        if requested_tickets > phase_remaining:
            return False, phase_remaining, phase
        return True, phase_remaining, phase

    @classmethod
    def calculate_pricing(
        cls,
        db: Session,
        ticket_count: int = 1,
        ticket_phase: Optional[str] = "EARLY_BIRD",
        offer_id: Optional[str] = None,
        quantity: Optional[int] = 1
    ) -> dict:
        """Calculates exact server-side pricing breakdown via payment_service."""
        from app.services.payment_service import payment_service
        return payment_service.calculate_pricing(
            db=db,
            ticket_count=ticket_count,
            ticket_phase_code=ticket_phase,
            offer_id=offer_id,
            quantity=quantity
        )

    @classmethod
    def initiate_order(
        cls,
        customer_name: str,
        email: str,
        phone: str,
        ticket_count: Optional[int] = None,
        db: Session = None,
        ticket_phase: Optional[str] = "EARLY_BIRD",
        idempotency_key: str = None,
        offer_id: Optional[str] = None,
        quantity: Optional[int] = 1,
        child_name: Optional[str] = None,
        child_age: Optional[int] = None,
    ) -> tuple[Booking, dict]:
        """Validates capacity, initializes pending booking, and returns payment checkout info."""
        event_setting = db.query(EventSetting).first()
        if not event_setting:
            event_setting = EventSetting()
            db.add(event_setting)
            db.commit()

        from app.services.payment_service import payment_service
        provider = payment_service.get_provider(db)

        # Calculate exact server-side pricing for requested ticket offer or phase
        if offer_id:
            from app.models.offers import calculate_offer_pricing
            pricing = calculate_offer_pricing(offer_id=offer_id, quantity=quantity or 1, db=db)
            resolved_ticket_count = pricing["passes_count"]
            resolved_phase = pricing["ticket_phase"]
            
            # Validation for kids offer
            if pricing.get("is_kids"):
                if not child_name or not child_name.strip():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Child's full name is required for Kids ticket."
                    )
                if child_age is not None:
                    try:
                        c_age = int(child_age)
                        if c_age < 5 or c_age > 12:
                            raise HTTPException(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Kids ticket is only applicable for children aged 5 to 12 years."
                            )
                    except ValueError:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid child age specified."
                        )
        else:
            resolved_ticket_count = ticket_count or 1
            resolved_phase = ticket_phase or "EARLY_BIRD"
            if resolved_ticket_count > event_setting.max_per_booking:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Maximum {event_setting.max_per_booking} tickets allowed per booking."
                )
            pricing = provider.calculate_pricing(db, resolved_ticket_count, ticket_phase_code=resolved_phase)

        total_amount = pricing["total_amount"]

        # Check venue capacity
        is_avail, remaining, _ = cls.check_capacity(db, requested_tickets=resolved_ticket_count)
        if not is_avail:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Only {remaining} tickets remaining. Cannot book {resolved_ticket_count} tickets."
            )

        # Check ticket phase status and capacity
        phase_avail, phase_rem, phase_obj = cls.check_phase_capacity(db, requested_tickets=resolved_ticket_count, phase_code=resolved_phase)
        if not phase_avail:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Only {phase_rem} tickets remaining in {phase_obj.name}. Cannot book {resolved_ticket_count} tickets."
            )

        # Reservation timeout
        timeout_mins = int(os.environ.get("PAYMENT_RESERVATION_MINUTES", getattr(settings, "PAYMENT_RESERVATION_MINUTES", 15)))
        reservation_expires = datetime.utcnow() + timedelta(minutes=timeout_mins)

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
                    "is_group_offer": (existing_booking.group_discount or 0) > 0 or (existing_booking.offer_id in ("EARLY_BIRD_GROUP_10", "PHASE_1_GROUP_10")),
                    "offer_name": existing_booking.offer_title or pricing.get("offer_name"),
                    "offer_id": existing_booking.offer_id,
                    "offer_title": existing_booking.offer_title,
                    "passes_count": existing_booking.ticket_count,
                    "child_name": existing_booking.child_name,
                    "child_age": existing_booking.child_age,
                    "upi_id": None if is_razorpay else upi_id,
                    "upi_qr_image_url": None if is_razorpay else "/api/payments/qr-image",
                    "upi_payment_instructions": None if is_razorpay else upi_instructions,
                    "razorpay_order_id": (existing_payment.razorpay_order_id if existing_payment and existing_payment.razorpay_order_id else existing_booking.razorpay_order_id) if is_razorpay else None,
                    "key_id": key_id if is_razorpay else None,
                    "razorpay_mode": mode if is_razorpay else None,
                    "is_simulation": False
                }

        booking_id = cls.generate_booking_id(db)

        # Create Pending Booking with reservation expiration, offer and fee breakdown
        new_booking = Booking(
            booking_id=booking_id,
            customer_name=customer_name.strip(),
            email=email.strip().lower(),
            phone=phone.strip(),
            ticket_count=resolved_ticket_count,
            ticket_phase=pricing.get("ticket_phase", resolved_phase),
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
            idempotency_key=idempotency_key,
            reservation_expires_at=reservation_expires,
            offer_id=pricing.get("offer_id"),
            offer_title=pricing.get("offer_title"),
            child_name=child_name.strip() if child_name else None,
            child_age=int(child_age) if child_age is not None else None
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
            "ticket_phase": pricing.get("ticket_phase", resolved_phase),
            "phase_name": pricing.get("phase_name", "Early Bird"),
            "ticket_price": pricing["ticket_price"],
            "ticket_count": resolved_ticket_count,
            "regular_amount": pricing["regular_amount"],
            "group_discount": pricing["group_discount"],
            "ticket_subtotal": pricing["ticket_subtotal"],
            "payment_fee": pricing["payment_fee"],
            "gst_amount": pricing["gst_amount"],
            "amount": total_amount,
            "currency": "INR",
            "is_group_offer": pricing.get("is_group_offer", False),
            "offer_name": pricing.get("offer_name"),
            "offer_id": pricing.get("offer_id"),
            "offer_title": pricing.get("offer_title"),
            "passes_count": resolved_ticket_count,
            "child_name": new_booking.child_name,
            "child_age": new_booking.child_age,
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
        booking.payment_status = "PAID"
        booking.booking_status = "CONFIRMED"
        booking.reservation_expires_at = None
        if verified_by:
            booking.verified_by = verified_by
        booking.verified_at = now
        booking.updated_at = now

        # Update phase inventory sold count atomically
        if booking.ticket_phase:
            phase = db.query(TicketPhase).filter(TicketPhase.phase_code == booking.ticket_phase).first()
            if phase:
                phase.sold_count = (phase.sold_count or 0) + booking.ticket_count
                if phase.sold_count >= phase.total_inventory:
                    phase.status = "SOLD_OUT"

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

        # 1. Send customer & admin ticket confirmation email safely (idempotent: avoid re-sending)
        if booking.email_status != "SENT" or booking.admin_email_status != "SENT":
            try:
                email_service.send_confirmation_email(booking.booking_id, db, send_to_admin=True)
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
