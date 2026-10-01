import json
import re
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.config import settings
from app.models.booking import Booking
from app.models.payment import Payment
from app.models.ticket import Ticket
from app.models.event_setting import EventSetting
from app.models.audit_log import AuditLog
from app.models.user import User
from app.services.payment_providers.base import BasePaymentProvider
from app.services.qr_service import qr_service
from app.services.email_service import email_service
from app.utils.logger import app_logger

class ManualUPIPaymentProvider(BasePaymentProvider):
    provider_code = "UPI_MANUAL"

    def calculate_pricing(
        self,
        db: Session,
        ticket_count: int = 1,
        ticket_phase_code: Optional[str] = None,
        offer_id: Optional[str] = None,
        quantity: Optional[int] = 1
    ) -> Dict[str, Any]:
        """
        Calculates exact ticket pricing breakdown for manual UPI.
        """
        if offer_id:
            from app.models.offers import calculate_offer_pricing
            return calculate_offer_pricing(offer_id=offer_id, quantity=quantity or 1, db=db)

        event_setting = db.query(EventSetting).first() if db else None

        from app.models.ticket_phase import TicketPhase
        phase = None
        if ticket_phase_code and db:
            phase = db.query(TicketPhase).filter(TicketPhase.phase_code == ticket_phase_code.strip().upper()).first()
            if not phase:
                raise HTTPException(
                    status_code=400,
                    detail=f"Ticket phase '{ticket_phase_code}' was not found."
                )
            if phase.status != "ACTIVE":
                raise HTTPException(
                    status_code=400,
                    detail=f"Ticket phase '{phase.name}' is currently {phase.status.lower()} and cannot be purchased."
                )

        if not phase and db:
            phase = db.query(TicketPhase).filter(TicketPhase.status == "ACTIVE").first()

        if phase:
            phase_code = phase.phase_code
            phase_name = phase.name
            ticket_price = float(phase.price)
            group_offer_enabled = bool(phase.group_offer_eligible)
        else:
            phase_code = "EARLY_BIRD"
            phase_name = "Early Bird"
            ticket_price = float(event_setting.ticket_price) if event_setting and event_setting.ticket_price is not None else 599.0
            group_offer_enabled = bool(event_setting.group_offer_enabled) if event_setting and hasattr(event_setting, "group_offer_enabled") else True

        group_offer_size = int(event_setting.group_offer_size) if event_setting and hasattr(event_setting, "group_offer_size") and event_setting.group_offer_size else 10
        group_offer_free_tickets = int(event_setting.group_offer_free_tickets) if event_setting and hasattr(event_setting, "group_offer_free_tickets") and event_setting.group_offer_free_tickets else 1

        regular_amount = round(ticket_price * ticket_count, 2)

        # Check if group offer applies
        if group_offer_enabled and ticket_count == group_offer_size:
            group_discount = round(ticket_price * group_offer_free_tickets, 2)
            ticket_subtotal = round(regular_amount - group_discount, 2)
            is_group_offer = True
            offer_name = f"BUY {group_offer_size}, PAY FOR {group_offer_size - group_offer_free_tickets}"
            free_tickets = group_offer_free_tickets
        else:
            group_discount = 0.0
            ticket_subtotal = regular_amount
            is_group_offer = False
            offer_name = None
            free_tickets = 0

        # Tax-inclusive pricing breakdown (18% GST)
        tax_rate = 0.18
        tax_amount = round(ticket_subtotal - (ticket_subtotal / (1.0 + tax_rate)), 2)
        base_amount = round(ticket_subtotal - tax_amount, 2)
        tax_label = "Taxes included"
        payment_fee = 0.0
        gst_amount = 0.0
        total_amount = ticket_subtotal

        return {
            "ticket_phase": phase_code,
            "phase_name": phase_name,
            "ticket_price": ticket_price,
            "ticket_count": ticket_count,
            "regular_amount": regular_amount,
            "group_discount": group_discount,
            "ticket_subtotal": ticket_subtotal,
            "payment_fee": payment_fee,
            "gst_amount": gst_amount,
            "tax_amount": tax_amount,
            "base_amount": base_amount,
            "tax_rate": tax_rate,
            "tax_included": True,
            "tax_label": tax_label,
            "total_amount": total_amount,
            "currency": "INR",
            "is_group_offer": is_group_offer,
            "offer_name": offer_name,
            "free_tickets": free_tickets,
        }

    def initiate_payment(
        self,
        booking: Booking,
        db: Session,
        idempotency_key: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Creates or updates a manual UPI payment record and returns QR code & UPI ID instructions.
        """
        event_setting = db.query(EventSetting).first()
        upi_id = (getattr(event_setting, "upi_id", None) or "").strip() or settings.UPI_ID or "samaymadhyastha2005@oksbi"
        upi_instructions = (
            getattr(event_setting, "upi_payment_instructions", None) or ""
        ).strip() or settings.UPI_PAYMENT_INSTRUCTIONS

        payment_id = f"PAY-UPI-{booking.booking_id}"

        # Ensure Payment record exists
        payment = db.query(Payment).filter(Payment.booking_id == booking.id).first()
        upi_order_ref = f"upi_order_{booking.booking_id}"
        if not payment:
            payment = Payment(
                payment_id=payment_id,
                booking_id=booking.id,
                payment_method="UPI_MANUAL",
                amount=booking.amount,
                currency="INR",
                payment_status="PENDING",
                status="PENDING",
                razorpay_order_id=upi_order_ref,
                idempotency_key=idempotency_key
            )
            db.add(payment)
        else:
            payment.payment_id = payment_id
            payment.payment_method = "UPI_MANUAL"
            payment.amount = booking.amount
            payment.payment_status = "PENDING"
            payment.status = "PENDING"
            payment.razorpay_order_id = upi_order_ref
            payment.idempotency_key = idempotency_key

        booking.payment_method = "UPI_MANUAL"
        booking.payment_status = "PENDING"
        booking.booking_status = "PAYMENT_PENDING"
        db.commit()
        db.refresh(booking)

        return {
            "payment_method": "UPI_MANUAL",
            "payment_id": payment_id,
            "booking_id": booking.booking_id,
            "amount": booking.amount,
            "currency": "INR",
            "upi_id": upi_id,
            "upi_qr_image_url": "/api/payments/qr-image",
            "upi_payment_instructions": upi_instructions,
        }

    def verify_payment(self, db: Session, **kwargs) -> Dict[str, Any]:
        """
        Manual UPI payments cannot be automatically verified by API.
        Admin manual review is required.
        """
        return {
            "verified": False,
            "requires_admin_approval": True,
            "message": "Manual UPI payment requires administrator verification."
        }

    def submit_payment_proof(
        self,
        booking_id: str,
        utr_number: str,
        screenshot_filename: Optional[str],
        db: Session
    ) -> Booking:
        """
        Records the customer-submitted UTR / Transaction reference and optional screenshot.
        Transitions booking to PAYMENT_VERIFICATION_PENDING.
        Validates UTR format and prevents duplicate UTR reuse across confirmed/pending bookings.
        """
        booking = db.query(Booking).filter(Booking.booking_id == booking_id).first()
        if not booking:
            raise HTTPException(status_code=404, detail="Booking reference not found.")

        # Allow submission if currently pending or if retrying after rejection
        allowed_statuses = ["PAYMENT_PENDING", "PAYMENT_VERIFICATION_PENDING", "PAYMENT_FAILED", "PENDING"]
        if booking.booking_status not in allowed_statuses and booking.payment_status != "REJECTED":
            if booking.booking_status == "CONFIRMED" and booking.payment_status == "PAID":
                raise HTTPException(status_code=400, detail="This booking has already been verified and confirmed.")
            raise HTTPException(
                status_code=400,
                detail=f"Cannot submit payment proof for booking with status '{booking.booking_status}'."
            )

        clean_utr = utr_number.strip()
        if len(clean_utr) < 6 or len(clean_utr) > 60:
            raise HTTPException(
                status_code=400,
                detail="Invalid UTR / Transaction ID. Must be between 6 and 60 alphanumeric characters."
            )

        # Disallow malicious symbols
        if not re.match(r"^[A-Za-z0-9\-_./]+$", clean_utr):
            raise HTTPException(
                status_code=400,
                detail="UTR / Transaction ID contains invalid characters. Use letters, numbers, or dashes only."
            )

        # Duplicate UTR prevention: Check if another booking already used this UTR and is confirmed or under review
        duplicate_booking = db.query(Booking).filter(
            Booking.utr_number == clean_utr,
            Booking.id != booking.id,
            Booking.payment_status.in_(["PAID", "VERIFICATION_PENDING"])
        ).first()

        if duplicate_booking:
            raise HTTPException(
                status_code=400,
                detail="This UTR / Transaction reference has already been submitted for another booking. Please check your transaction details."
            )

        # Update Payment record
        payment = db.query(Payment).filter(Payment.booking_id == booking.id).first()
        if not payment:
            payment = Payment(
                payment_id=f"PAY-UPI-{booking.booking_id}",
                booking_id=booking.id,
                payment_method="UPI_MANUAL",
                amount=booking.amount,
                currency="INR"
            )
            db.add(payment)

        payment.utr_number = clean_utr
        if screenshot_filename:
            payment.payment_screenshot = screenshot_filename
        payment.payment_status = "VERIFICATION_PENDING"
        payment.status = "VERIFICATION_PENDING"
        payment.updated_at = datetime.utcnow()

        # Update Booking record
        booking.utr_number = clean_utr
        if screenshot_filename:
            booking.payment_screenshot = screenshot_filename
        booking.booking_status = "PAYMENT_VERIFICATION_PENDING"
        booking.payment_status = "VERIFICATION_PENDING"
        booking.updated_at = datetime.utcnow()

        # Audit log entry
        audit = AuditLog(
            action="PAYMENT_PROOF_SUBMITTED",
            entity_type="booking",
            entity_id=booking.booking_id,
            details=json.dumps({
                "utr_number": clean_utr,
                "has_screenshot": bool(screenshot_filename),
                "amount": booking.amount,
                "customer_name": booking.customer_name
            })
        )
        db.add(audit)

        db.commit()
        db.refresh(booking)

        app_logger.info(
            f"[UPI MANUAL] Payment proof submitted for {booking.booking_id} with UTR: {clean_utr} "
            f"(Screenshot: {screenshot_filename or 'None'})"
        )

        # Immediate alert to owner & Vinay that verification is required
        try:
            email_service.send_payment_submission_alert(booking.booking_id, db)
        except Exception as alert_err:
            app_logger.warning(f"Could not dispatch payment verification alert: {alert_err}")

        return booking

    def approve_payment(self, booking_id: str, admin_user: User, db: Session) -> Booking:
        """
        Admin action: Approves the submitted UPI payment.
        Performs transactional state update:
        1. Verifies booking
        2. Marks payment as PAID
        3. Marks booking as CONFIRMED
        4. Generates all individual tickets (with valid QR codes)
        5. Sends confirmation email & owner alert
        6. Logs audit trail with admin ID and timestamp
        """
        # Row-level lock to prevent double-clicks or concurrency races
        booking = db.query(Booking).filter(Booking.booking_id == booking_id).with_for_update().first()
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found.")

        # Idempotency: If already confirmed, return directly without re-issuing tickets or emails
        if booking.booking_status == "CONFIRMED" and booking.payment_status == "PAID":
            app_logger.info(f"Booking {booking_id} already confirmed. Idempotent return.")
            return booking

        # Update Payment record
        payment = db.query(Payment).filter(Payment.booking_id == booking.id).first()
        now = datetime.utcnow()
        if payment:
            payment.payment_status = "PAID"
            payment.status = "PAID"
            payment.verified_by = admin_user.email
            payment.verified_at = now
            payment.updated_at = now

        booking.payment_status = "PAID"
        booking.booking_status = "CONFIRMED"
        booking.verified_by = admin_user.email
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

            # Audit log for ticket generation
            db.add(AuditLog(
                user_id=admin_user.id,
                action="TICKETS_GENERATED",
                entity_type="booking",
                entity_id=booking.booking_id,
                details=json.dumps({"ticket_count": booking.ticket_count})
            ))

        # Audit log for payment approval
        audit = AuditLog(
            user_id=admin_user.id,
            action="PAYMENT_APPROVED",
            entity_type="payment",
            entity_id=booking.booking_id,
            details=json.dumps({
                "approved_by": admin_user.email,
                "amount": booking.amount,
                "utr_number": booking.utr_number,
                "ticket_count": booking.ticket_count,
                "timestamp": now.isoformat()
            })
        )
        db.add(audit)

        db.commit()
        db.refresh(booking)

        # Send confirmation email with PDF tickets attached
        try:
            email_service.send_confirmation_email(booking.booking_id, db)
            db.add(AuditLog(
                user_id=admin_user.id,
                action="CONFIRMATION_EMAIL_SENT",
                entity_type="booking",
                entity_id=booking.booking_id,
                details=json.dumps({"recipient": booking.email})
            ))
            db.commit()
        except Exception as e:
            app_logger.error(f"Error dispatching confirmation email for {booking.booking_id}: {e}")

        # Send owner alert notification
        try:
            email_service.send_owner_notification(booking.booking_id, db)
        except Exception as e:
            app_logger.error(f"Error dispatching owner alert for {booking.booking_id}: {e}")

        app_logger.info(f"[PAYMENT APPROVED] Booking {booking_id} verified by {admin_user.email}. Tickets issued.")
        return booking

    def reject_payment(
        self,
        booking_id: str,
        reason: str,
        admin_user: User,
        db: Session
    ) -> Booking:
        """
        Admin action: Rejects the submitted UPI payment proof.
        Marks payment as REJECTED and booking as PAYMENT_FAILED.
        Does NOT generate tickets or send confirmation email.
        Allows customer to retry payment submission if appropriate.
        """
        booking = db.query(Booking).filter(Booking.booking_id == booking_id).with_for_update().first()
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found.")

        if booking.booking_status == "CONFIRMED" and booking.payment_status == "PAID":
            raise HTTPException(
                status_code=400,
                detail="Cannot reject a booking that has already been approved and confirmed."
            )

        now = datetime.utcnow()
        clean_reason = reason.strip() or "Payment verification failed: transaction not found in bank account."

        payment = db.query(Payment).filter(Payment.booking_id == booking.id).first()
        if payment:
            payment.payment_status = "REJECTED"
            payment.status = "REJECTED"
            payment.rejection_reason = clean_reason
            payment.verified_by = admin_user.email
            payment.verified_at = now
            payment.updated_at = now

        booking.payment_status = "REJECTED"
        booking.booking_status = "PAYMENT_FAILED"
        booking.rejection_reason = clean_reason
        booking.verified_by = admin_user.email
        booking.verified_at = now
        booking.updated_at = now

        audit = AuditLog(
            user_id=admin_user.id,
            action="PAYMENT_REJECTED",
            entity_type="payment",
            entity_id=booking.booking_id,
            details=json.dumps({
                "rejected_by": admin_user.email,
                "reason": clean_reason,
                "amount": booking.amount,
                "utr_number": booking.utr_number,
                "timestamp": now.isoformat()
            })
        )
        db.add(audit)

        db.commit()
        db.refresh(booking)

        app_logger.info(f"[PAYMENT REJECTED] Booking {booking_id} rejected by {admin_user.email}. Reason: {clean_reason}")
        return booking
