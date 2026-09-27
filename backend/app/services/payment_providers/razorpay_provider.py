import uuid
import json
import razorpay
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.config import settings
from app.models.booking import Booking
from app.models.payment import Payment
from app.models.event_setting import EventSetting
from app.services.payment_providers.base import BasePaymentProvider
from app.utils.security import verify_razorpay_signature, verify_razorpay_webhook_signature
from app.utils.logger import app_logger

class RazorpayPaymentProvider(BasePaymentProvider):
    provider_code = "RAZORPAY"

    def _get_credentials(self, db: Session):
        """Resolves Razorpay API credentials dynamically from database settings or environment."""
        setting = db.query(EventSetting).first()
        key_id = (getattr(setting, "razorpay_key_id", None) or "").strip() if setting else ""
        if not key_id:
            key_id = (settings.RAZORPAY_KEY_ID or "").strip()

        key_secret = (getattr(setting, "razorpay_key_secret", None) or "").strip() if setting else ""
        if not key_secret:
            key_secret = (settings.RAZORPAY_KEY_SECRET or "").strip()

        webhook_secret = (getattr(setting, "razorpay_webhook_secret", None) or "").strip() if setting else ""
        if not webhook_secret:
            webhook_secret = (settings.RAZORPAY_WEBHOOK_SECRET or "").strip()

        is_mock = (
            not key_id
            or "placeholder" in key_id.lower()
            or not key_secret
            or "placeholder" in key_secret.lower()
        )
        return key_id, key_secret, webhook_secret, is_mock

    def calculate_pricing(self, db: Session, ticket_count: int) -> Dict[str, Any]:
        """Calculates ticket subtotal + 2% Razorpay processing fee + 18% GST."""
        event_setting = db.query(EventSetting).first()
        ticket_price = float(event_setting.ticket_price) if event_setting and event_setting.ticket_price is not None else 599.0
        group_offer_enabled = bool(event_setting.group_offer_enabled) if event_setting and hasattr(event_setting, "group_offer_enabled") else True
        group_offer_size = int(event_setting.group_offer_size) if event_setting and hasattr(event_setting, "group_offer_size") and event_setting.group_offer_size else 10
        group_offer_free_tickets = int(event_setting.group_offer_free_tickets) if event_setting and hasattr(event_setting, "group_offer_free_tickets") and event_setting.group_offer_free_tickets else 1

        regular_amount = round(ticket_price * ticket_count, 2)

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

        # Optional processing fee if configured, default 0 for simplicity or 2% if specified
        fee_rate = 0.02 if getattr(event_setting, "convenience_fee", 0.0) > 0 else 0.0
        payment_fee = round(ticket_subtotal * fee_rate, 2)
        gst_amount = round(payment_fee * 0.18, 2)
        total_amount = round(ticket_subtotal + payment_fee + gst_amount, 2)

        return {
            "ticket_price": ticket_price,
            "ticket_count": ticket_count,
            "regular_amount": regular_amount,
            "group_discount": group_discount,
            "ticket_subtotal": ticket_subtotal,
            "payment_fee": payment_fee,
            "gst_amount": gst_amount,
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
        """Creates an order via Razorpay API (or simulation in test mode)."""
        key_id, key_secret, _, is_mock = self._get_credentials(db)
        amount_paise = int(round(booking.amount * 100))

        order_id = ""
        if is_mock:
            order_id = f"order_mock_{uuid.uuid4().hex[:14]}"
            app_logger.info(f"[SIMULATED PAYMENT] Created mock order {order_id} for INR {booking.amount}")
        else:
            try:
                client = razorpay.Client(auth=(key_id, key_secret))
                order_data = {
                    "amount": amount_paise,
                    "currency": "INR",
                    "receipt": booking.booking_id,
                    "notes": {"booking_id": booking.booking_id}
                }
                rzp_order = client.order.create(data=order_data)
                order_id = rzp_order["id"]
                app_logger.info(f"[REAL RAZORPAY] Created live order {order_id} for INR {booking.amount}")
            except Exception as e:
                app_logger.error(f"Razorpay order creation failed: {e}")
                raise HTTPException(status_code=502, detail=f"Failed to initialize payment gateway: {e}")

        # Update payment record
        payment = db.query(Payment).filter(Payment.booking_id == booking.id).first()
        if not payment:
            payment = Payment(
                payment_id=f"PAY-RZP-{booking.booking_id}",
                booking_id=booking.id,
                razorpay_order_id=order_id,
                payment_method="RAZORPAY",
                amount=booking.amount,
                currency="INR",
                payment_status="PENDING",
                status="PENDING",
                idempotency_key=idempotency_key
            )
            db.add(payment)
        else:
            payment.payment_id = f"PAY-RZP-{booking.booking_id}"
            payment.razorpay_order_id = order_id
            payment.payment_method = "RAZORPAY"
            payment.amount = booking.amount
            payment.payment_status = "PENDING"
            payment.status = "PENDING"
            payment.idempotency_key = idempotency_key

        booking.razorpay_order_id = order_id
        booking.payment_method = "RAZORPAY"
        booking.payment_status = "PENDING"
        booking.booking_status = "PAYMENT_PENDING"
        db.commit()
        db.refresh(booking)

        return {
            "payment_method": "RAZORPAY",
            "razorpay_order_id": order_id,
            "booking_id": booking.booking_id,
            "amount": booking.amount,
            "currency": "INR",
            "key_id": key_id if not is_mock else "rzp_test_simulation",
            "is_simulation": is_mock
        }

    def verify_payment(self, db: Session, **kwargs) -> Dict[str, Any]:
        """Verifies HMAC signature of Razorpay payment."""
        order_id = kwargs.get("order_id", "")
        payment_id = kwargs.get("payment_id", "")
        signature = kwargs.get("signature", "")

        key_id, key_secret, _, is_mock = self._get_credentials(db)

        if is_mock or order_id.startswith("order_mock_"):
            if signature.startswith("sim_sig_") or signature == "test_success_sig" or len(signature) >= 10:
                app_logger.info(f"[SIMULATED PAYMENT] Verified signature for {order_id}")
                return {"verified": True, "is_mock": True}
            return {"verified": False, "is_mock": True}

        is_valid = verify_razorpay_signature(order_id, payment_id, signature, key_secret=key_secret)
        if not is_valid:
            app_logger.warning(f"Razorpay signature mismatch for order: {order_id}")
            return {"verified": False, "is_mock": False}
        return {"verified": True, "is_mock": False}

    def process_webhook(self, body_bytes: bytes, signature: str, db: Session) -> dict:
        """Handles incoming Razorpay asynchronous webhooks."""
        _, _, webhook_secret, is_mock = self._get_credentials(db)
        if not is_mock and webhook_secret:
            if not verify_razorpay_webhook_signature(body_bytes, signature, webhook_secret=webhook_secret):
                app_logger.warning("Razorpay webhook signature verification failed!")
                raise HTTPException(status_code=400, detail="Invalid webhook signature")

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
                return {"status": "unmatched", "order_id": order_id, "event": event_type}

            if event_type in ["payment.captured", "order.paid"]:
                if booking.booking_status == "CONFIRMED" and booking.payment_status == "PAID":
                    return {"status": "already_confirmed", "booking_id": booking.booking_id}

                from app.services.booking_service import booking_service
                confirmed_booking = booking_service.confirm_booking_and_generate_tickets(
                    booking_id=booking.booking_id,
                    razorpay_payment_id=payment_id,
                    razorpay_signature="webhook_verified",
                    db=db,
                    payment_method=payment_entity.get("method", "razorpay_webhook")
                )
                return {
                    "status": "confirmed",
                    "booking_id": confirmed_booking.booking_id,
                    "payment_status": confirmed_booking.payment_status
                }

            elif event_type in ["payment.failed"]:
                if booking.payment_status != "PAID":
                    booking.payment_status = "FAILED"
                    db.commit()
                return {"status": "payment_failed", "booking_id": booking.booking_id}

            return {"status": "ignored", "event": event_type, "booking_id": booking.booking_id}
        except HTTPException:
            raise
        except Exception as e:
            app_logger.error(f"Error handling webhook: {e}")
            raise HTTPException(status_code=400, detail="Webhook payload error")
