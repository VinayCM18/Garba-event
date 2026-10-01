import os
import uuid
import json
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.utils.logger import app_logger

try:
    import razorpay
    RAZORPAY_IMPORT_ERROR = None
except Exception as exc:
    razorpay = None
    RAZORPAY_IMPORT_ERROR = f"{type(exc).__name__}: {exc}"

if razorpay is not None:
    app_logger.info("Razorpay Python SDK imported successfully.")
else:
    app_logger.error(
        f"Razorpay Python SDK import failed: {RAZORPAY_IMPORT_ERROR}"
    )

from app.config import settings
from app.models.booking import Booking
from app.models.payment import Payment
from app.models.event_setting import EventSetting
from app.services.payment_providers.base import BasePaymentProvider
from app.utils.security import verify_razorpay_signature, verify_razorpay_webhook_signature

class RazorpayPaymentProvider(BasePaymentProvider):
    provider_code = "RAZORPAY"

    def _get_credentials(self, db: Optional[Session] = None):
        """
        Resolves Razorpay API credentials with strict priority:
        1. Environment variables (os.environ, then settings) have highest priority:
           - RAZORPAY_KEY_ID
           - RAZORPAY_KEY_SECRET
           - RAZORPAY_MODE
        2. When RAZORPAY_MODE=LIVE:
           - MUST use Railway environment variables (RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET).
           - MUST NOT use SQLite EventSetting, config defaults, cached configuration, or test fallback.
           - RAZORPAY_KEY_ID MUST start with "rzp_live_". If it starts with "rzp_test_", raise a configuration error.
        3. When RAZORPAY_MODE=TEST:
           - Priority 1: Environment variables RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET.
           - Priority 2: Database EventSetting values if environment variables are not set.
           - Keys starting with "rzp_test_" are allowed.
        """
        # Resolve mode: environment variable has highest priority
        raw_mode = (
            os.environ.get("RAZORPAY_MODE")
            or getattr(settings, "RAZORPAY_MODE", None)
            or "TEST"
        )
        mode = str(raw_mode).strip().strip("'\"").upper() if raw_mode else "TEST"

        # Resolve credentials from environment variables first (highest priority)
        env_key_id = (os.environ.get("RAZORPAY_KEY_ID") or "").strip().strip("'\"")
        env_key_secret = (os.environ.get("RAZORPAY_KEY_SECRET") or "").strip().strip("'\"")
        env_webhook_secret = (os.environ.get("RAZORPAY_WEBHOOK_SECRET") or "").strip().strip("'\"")

        setting = db.query(EventSetting).first() if db else None

        if mode == "LIVE":
            # In LIVE mode, strictly enforce environment variables; DO NOT use SQLite EventSetting fallback
            key_id = env_key_id
            key_secret = env_key_secret
            webhook_secret = env_webhook_secret

            # Validation 1: Missing key_id in LIVE mode
            if not key_id:
                err_msg = "Razorpay LIVE mode requires RAZORPAY_KEY_ID environment variable to be configured."
                app_logger.error(f"[RAZORPAY CONFIG ERROR] {err_msg}")
                raise HTTPException(status_code=500, detail=err_msg)

            # Validation 2: Rejection of test key in LIVE mode
            if key_id.startswith("rzp_test_"):
                err_msg = (
                    "Razorpay LIVE mode requires a live API key beginning with rzp_live_. "
                    f"Found test key prefix '{key_id[:9]}'. Do NOT use test keys in LIVE mode."
                )
                app_logger.error(f"[RAZORPAY CONFIG ERROR] {err_msg}")
                raise HTTPException(status_code=500, detail=err_msg)

            # Validation 3: Key must start with rzp_live_
            if not key_id.startswith("rzp_live_"):
                err_msg = (
                    "Razorpay LIVE mode requires a live API key beginning with rzp_live_. "
                    f"Provided key begins with '{key_id[:9] if len(key_id) >= 9 else key_id}'."
                )
                app_logger.error(f"[RAZORPAY CONFIG ERROR] {err_msg}")
                raise HTTPException(status_code=500, detail=err_msg)

            # Validation 4: Missing key_secret in LIVE mode
            if not key_secret:
                err_msg = "Razorpay LIVE mode requires RAZORPAY_KEY_SECRET environment variable to be configured."
                app_logger.error(f"[RAZORPAY CONFIG ERROR] {err_msg}")
                raise HTTPException(status_code=500, detail=err_msg)

        else:
            # TEST mode: Environment variables take priority; DB EventSetting is only a fallback
            db_key_id = (getattr(setting, "razorpay_key_id", None) if setting else None) or ""
            key_id = env_key_id or str(db_key_id).strip().strip("'\"")

            # Validation: TEST mode must reject live keys
            if key_id.startswith("rzp_live_"):
                err_msg = (
                    "Razorpay TEST mode requires a test API key beginning with rzp_test_. "
                    f"Found live API key beginning with '{key_id[:9]}'. Do NOT use live keys in TEST mode."
                )
                app_logger.error(f"[RAZORPAY CONFIG ERROR] {err_msg}")
                raise HTTPException(status_code=500, detail=err_msg)

            if key_id and not key_id.startswith("rzp_test_"):
                err_msg = (
                    "Razorpay TEST mode requires a test API key beginning with rzp_test_. "
                    f"Provided key begins with '{key_id[:9] if len(key_id) >= 9 else key_id}'."
                )
                app_logger.error(f"[RAZORPAY CONFIG ERROR] {err_msg}")
                raise HTTPException(status_code=500, detail=err_msg)

            db_key_secret = (getattr(setting, "razorpay_key_secret", None) if setting else None) or ""
            key_secret = env_key_secret or str(db_key_secret).strip().strip("'\"")

            db_wh_secret = (getattr(setting, "razorpay_webhook_secret", None) if setting else None) or ""
            webhook_secret = env_webhook_secret or str(db_wh_secret).strip().strip("'\"")

        return key_id, key_secret, webhook_secret, mode

    def calculate_pricing(
        self,
        db: Session,
        ticket_count: int = 1,
        ticket_phase_code: Optional[str] = None,
        offer_id: Optional[str] = None,
        quantity: Optional[int] = 1
    ) -> Dict[str, Any]:
        """
        Calculates exact ticket pricing and gateway fee breakdown based on ticket offer or ticket phase.
        When offer_id is provided, delegates to authoritative calculate_offer_pricing.
        """
        if offer_id:
            from app.models.offers import calculate_offer_pricing
            return calculate_offer_pricing(offer_id=offer_id, quantity=quantity or 1, db=db)

        event_setting = db.query(EventSetting).first() if db else None

        # Resolve ticket phase
        from app.models.ticket_phase import TicketPhase
        phase = None
        has_phases = bool(db and db.query(TicketPhase).count() > 0)
        if ticket_phase_code and db:
            phase = db.query(TicketPhase).filter(TicketPhase.phase_code == ticket_phase_code.strip().upper()).first()
            if not phase and has_phases:
                raise HTTPException(
                    status_code=400,
                    detail=f"Ticket phase '{ticket_phase_code}' was not found."
                )
            if phase and phase.status != "ACTIVE":
                raise HTTPException(
                    status_code=400,
                    detail=f"Ticket phase '{phase.name}' is currently {phase.status.lower()} and cannot be purchased."
                )

        if not phase and db and has_phases:
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

        # Apply group promotion (e.g. 10 tickets for price of 9)
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

        # Gateway fee calculation
        pass_fee_env = os.environ.get("PASS_GATEWAY_FEE_TO_CUSTOMER")
        if pass_fee_env is not None:
            pass_fee = pass_fee_env.strip().lower() in ("true", "1", "yes")
        else:
            pass_fee = getattr(settings, "PASS_GATEWAY_FEE_TO_CUSTOMER", False)
            if isinstance(pass_fee, str):
                pass_fee = pass_fee.strip().lower() in ("true", "1", "yes")

        raw_fee_rate = os.environ.get("GATEWAY_FEE_RATE")
        if raw_fee_rate is not None and raw_fee_rate.strip() != "":
            fee_rate = float(raw_fee_rate)
        elif getattr(settings, "GATEWAY_FEE_RATE", None) is not None and getattr(settings, "GATEWAY_FEE_RATE", 0.0) > 0:
            fee_rate = float(settings.GATEWAY_FEE_RATE)
        elif pass_fee:
            fee_rate = 0.02
        else:
            fee_rate = 0.0

        raw_fee_gst = os.environ.get("GATEWAY_FEE_GST_RATE")
        if raw_fee_gst is not None and raw_fee_gst.strip() != "":
            fee_gst_rate = float(raw_fee_gst)
        elif getattr(settings, "GATEWAY_FEE_GST_RATE", None) is not None and getattr(settings, "GATEWAY_FEE_GST_RATE", 0.0) > 0:
            fee_gst_rate = float(settings.GATEWAY_FEE_GST_RATE)
        elif fee_rate > 0:
            fee_gst_rate = 0.18
        else:
            fee_gst_rate = 0.0

        if pass_fee and fee_rate > 0:
            payment_fee = round(ticket_subtotal * fee_rate, 2)
            gst_amount = round(payment_fee * fee_gst_rate, 2)
        else:
            payment_fee = 0.0
            gst_amount = 0.0

        total_amount = round(ticket_subtotal + payment_fee + gst_amount, 2)

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
            "tax_amount": gst_amount,
            "base_amount": ticket_subtotal,
            "tax_rate": fee_gst_rate,
            "tax_included": False,
            "tax_label": "Razorpay Fee + GST",
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
        """Creates a verified order via Razorpay API in Test or Live mode."""
        key_id, key_secret, _, mode = self._get_credentials(db)

        if not key_id or not key_secret:
            raise HTTPException(
                status_code=500,
                detail="Razorpay API credentials (RAZORPAY_KEY_ID & RAZORPAY_KEY_SECRET) are not configured. Please set them in your Railway environment variables or Admin Settings."
            )

        if razorpay is None:
            raise HTTPException(
                status_code=500,
                detail=(
                    "Razorpay SDK import failed on server. "
                    f"Import error: {RAZORPAY_IMPORT_ERROR}"
                )
            )

        # Amount in paise (1 INR = 100 paise)
        amount_paise = int(round(booking.amount * 100))

        try:
            client = razorpay.Client(auth=(key_id, key_secret))
            order_data = {
                "amount": amount_paise,
                "currency": "INR",
                "receipt": booking.booking_id,
                "notes": {
                    "booking_id": booking.booking_id,
                    "customer_name": booking.customer_name,
                    "email": booking.email,
                    "phone": booking.phone,
                    "ticket_count": str(booking.ticket_count),
                    "mode": mode,
                    "pricing": "tax_inclusive"
                }
            }
            rzp_order = client.order.create(data=order_data)
            order_id = rzp_order["id"]
            app_logger.info(f"[RAZORPAY {mode}] Created real order {order_id} for booking {booking.booking_id} (INR {booking.amount})")
        except HTTPException:
            raise
        except Exception as e:
            app_logger.error(f"Razorpay order creation failed: {e}")
            raise HTTPException(status_code=502, detail=f"Failed to initialize payment gateway: {str(e)}")

        # Update payment record
        now = datetime.utcnow()
        payment = db.query(Payment).filter(Payment.booking_id == booking.id).first()
        if not payment:
            payment = Payment(
                payment_id=f"PAY-RZP-{booking.booking_id}",
                booking_id=booking.id,
                razorpay_order_id=order_id,
                payment_method="RAZORPAY",
                amount=booking.amount,
                currency="INR",
                payment_status="CREATED",
                status="PENDING",
                idempotency_key=idempotency_key,
                created_at=now,
                updated_at=now
            )
            db.add(payment)
        else:
            payment.payment_id = f"PAY-RZP-{booking.booking_id}"
            payment.razorpay_order_id = order_id
            payment.payment_method = "RAZORPAY"
            payment.amount = booking.amount
            payment.payment_status = "CREATED"
            payment.status = "PENDING"
            payment.idempotency_key = idempotency_key
            payment.updated_at = now

        booking.razorpay_order_id = order_id
        booking.payment_method = "RAZORPAY"
        booking.payment_status = "PENDING"
        booking.booking_status = "PAYMENT_PENDING"
        booking.updated_at = now
        db.commit()
        db.refresh(booking)

        return {
            "payment_method": "RAZORPAY",
            "razorpay_order_id": order_id,
            "booking_id": booking.booking_id,
            "amount": booking.amount,
            "currency": "INR",
            "key_id": key_id,
            "razorpay_mode": mode,
            "is_simulation": False
        }

    def verify_payment(self, db: Session, **kwargs) -> bool:
        """Verifies HMAC SHA256 signature of Razorpay payment."""
        order_id = kwargs.get("order_id", "")
        payment_id = kwargs.get("payment_id", "")
        signature = kwargs.get("signature", "")

        key_id, key_secret, _, mode = self._get_credentials(db)

        if not key_secret:
            app_logger.error("RAZORPAY_KEY_SECRET is not configured for signature verification!")
            return False

        if not order_id or not payment_id or not signature:
            app_logger.warning("Missing order_id, payment_id, or signature in payment verification.")
            return False

        is_valid = verify_razorpay_signature(order_id, payment_id, signature, key_secret=key_secret)
        if not is_valid:
            app_logger.warning(f"[RAZORPAY {mode}] Signature mismatch for order: {order_id}, payment: {payment_id}")
            return False

        app_logger.info(f"[RAZORPAY {mode}] Signature verified successfully for order: {order_id}")
        return True

    def process_webhook(self, body_bytes: bytes, signature: str, db: Session) -> dict:
        """Handles incoming Razorpay asynchronous webhooks with signature verification."""
        _, _, webhook_secret, mode = self._get_credentials(db)

        if not webhook_secret:
            app_logger.error("RAZORPAY_WEBHOOK_SECRET is not configured.")
            raise HTTPException(status_code=500, detail="Razorpay webhook secret not configured on server.")

        if not signature:
            app_logger.warning("Missing x-razorpay-signature header on webhook request.")
            raise HTTPException(status_code=400, detail="Missing webhook signature header.")

        if not verify_razorpay_webhook_signature(body_bytes, signature, webhook_secret=webhook_secret):
            app_logger.warning("Razorpay webhook signature verification failed!")
            raise HTTPException(status_code=400, detail="Invalid webhook signature.")

        try:
            event = json.loads(body_bytes.decode("utf-8"))
            event_type = event.get("event")
            payload = event.get("payload", {})

            payment_entity = payload.get("payment", {}).get("entity", {})
            order_entity = payload.get("order", {}).get("entity", {})

            order_id = payment_entity.get("order_id") or order_entity.get("id")
            payment_id = payment_entity.get("id", "webhook_captured")
            notes = payment_entity.get("notes", {}) or order_entity.get("notes", {})
            booking_id_hint = notes.get("booking_id")

            booking = None
            if order_id:
                booking = db.query(Booking).filter(Booking.razorpay_order_id == order_id).first()
            if not booking and booking_id_hint:
                booking = db.query(Booking).filter(Booking.booking_id == booking_id_hint).first()

            if not booking:
                app_logger.warning(f"Webhook received for unknown booking (order: {order_id}, hint: {booking_id_hint})")
                return {"status": "unmatched", "order_id": order_id, "event": event_type}

            if event_type in ["payment.captured", "order.paid"]:
                # Idempotency check: If already confirmed, don't duplicate tickets or emails
                if booking.booking_status == "CONFIRMED" and booking.payment_status in ["PAID", "CAPTURED"]:
                    app_logger.info(f"Webhook: Booking {booking.booking_id} already confirmed, skipping duplicate.")
                    return {"status": "already_confirmed", "booking_id": booking.booking_id}

                # Verify amount in paise if present in payment or order entity
                check_amount = None
                if payment_entity and "amount" in payment_entity and payment_entity["amount"] is not None:
                    check_amount = payment_entity["amount"]
                elif order_entity and "amount" in order_entity and order_entity["amount"] is not None:
                    check_amount = order_entity["amount"]
                elif order_entity and "amount_paid" in order_entity and order_entity["amount_paid"] is not None:
                    check_amount = order_entity["amount_paid"]

                if check_amount is not None:
                    expected_paise = int(round(booking.amount * 100))
                    actual_paise = int(check_amount)
                    if actual_paise != expected_paise:
                        app_logger.error(f"Webhook amount mismatch for {booking.booking_id}: expected {expected_paise} paise, got {actual_paise} paise")
                        raise HTTPException(status_code=400, detail="Payment amount mismatch in webhook.")

                from app.services.booking_service import booking_service
                confirmed_booking = booking_service.confirm_booking_and_generate_tickets(
                    booking_id=booking.booking_id,
                    razorpay_payment_id=payment_id,
                    razorpay_signature="webhook_verified",
                    db=db,
                    payment_method=payment_entity.get("method", "RAZORPAY")
                )

                # Update payment record explicitly to CAPTURED
                payment = db.query(Payment).filter(Payment.booking_id == confirmed_booking.id).first()
                if payment:
                    payment.payment_status = "CAPTURED"
                    payment.status = "PAID"
                    payment.razorpay_payment_id = payment_id
                    payment.raw_response = body_bytes.decode("utf-8", errors="ignore")
                    payment.verified_at = datetime.utcnow()
                    db.commit()

                app_logger.info(f"[RAZORPAY {mode}] Confirmed booking {confirmed_booking.booking_id} via webhook ({event_type})")
                return {
                    "status": "confirmed",
                    "booking_id": confirmed_booking.booking_id,
                    "payment_status": "CAPTURED"
                }

            elif event_type in ["payment.failed"]:
                if booking.payment_status not in ["PAID", "CAPTURED"]:
                    booking.payment_status = "FAILED"
                    booking.booking_status = "PAYMENT_FAILED"
                    booking.reservation_expires_at = None
                    payment = db.query(Payment).filter(Payment.booking_id == booking.id).first()
                    if payment:
                        payment.payment_status = "FAILED"
                        payment.status = "FAILED"
                        payment.raw_response = body_bytes.decode("utf-8", errors="ignore")
                    db.commit()
                app_logger.info(f"[RAZORPAY {mode}] Marked booking {booking.booking_id} as PAYMENT_FAILED via webhook")
                return {"status": "payment_failed", "booking_id": booking.booking_id}

            return {"status": "ignored", "event": event_type, "booking_id": booking.booking_id}
        except HTTPException:
            raise
        except Exception as e:
            app_logger.error(f"Error handling Razorpay webhook: {e}")
            raise HTTPException(status_code=400, detail="Webhook payload processing error.")

