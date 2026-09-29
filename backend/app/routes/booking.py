from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.booking import Booking
from app.models.event_setting import EventSetting
from app.schemas.booking import BookingDetailResponse
from app.schemas.ticket import TicketResponse
from app.services.ticket_service import ticket_service
from app.services.qr_service import qr_service
from app.config import settings

router = APIRouter(prefix="/api/bookings", tags=["Bookings"])

@router.get("/public-config")
def get_public_config(db: Session = Depends(get_db)):
    """Fetch public event details and live ticket availability."""
    event_setting = db.query(EventSetting).first()
    if not event_setting:
        event_setting = EventSetting()
        db.add(event_setting)
        db.commit()
        db.refresh(event_setting)

    sold_count = db.query(func.coalesce(func.sum(Booking.ticket_count), 0)).filter(
        Booking.booking_status == "CONFIRMED",
        Booking.payment_status == "PAID"
    ).scalar() or 0

    remaining = max(0, event_setting.total_capacity - sold_count)

    return {
        "event_name": event_setting.event_name,
        "event_tagline": event_setting.event_tagline,
        "event_date": event_setting.event_date,
        "event_time": event_setting.event_time,
        "venue_name": event_setting.venue_name,
        "venue_address": event_setting.venue_address,
        "venue_city": event_setting.venue_city,
        "ticket_price": event_setting.ticket_price,
        "convenience_fee": event_setting.convenience_fee,
        "total_capacity": event_setting.total_capacity,
        "remaining_tickets": remaining,
        "sold_tickets": sold_count,
        "max_per_booking": event_setting.max_per_booking,
        "booking_open": event_setting.booking_open and remaining > 0,
        "contact_email": event_setting.contact_email,
        "contact_phone": event_setting.contact_phone,
        "rules_text": event_setting.rules_text,
        "group_offer_enabled": getattr(event_setting, "group_offer_enabled", True),
        "group_offer_size": getattr(event_setting, "group_offer_size", 10),
        "group_offer_free_tickets": getattr(event_setting, "group_offer_free_tickets", 1),
        "group_offer_discount": round(float(event_setting.ticket_price) * getattr(event_setting, "group_offer_free_tickets", 1), 2),
        "group_offer_regular_total": round(float(event_setting.ticket_price) * getattr(event_setting, "group_offer_size", 10), 2),
        "group_offer_subtotal": round(float(event_setting.ticket_price) * (getattr(event_setting, "group_offer_size", 10) - getattr(event_setting, "group_offer_free_tickets", 1)), 2),
        # Payment Provider Details
        "payment_method": getattr(event_setting, "payment_method", None) or settings.PAYMENT_METHOD or "UPI_MANUAL",
        "upi_id": getattr(event_setting, "upi_id", None) or settings.UPI_ID or "samaymadhyastha2005@oksbi",
        "upi_qr_image_url": "/api/payments/qr-image",
        "upi_payment_instructions": getattr(event_setting, "upi_payment_instructions", None) or settings.UPI_PAYMENT_INSTRUCTIONS
    }

@router.get("/{booking_id}", response_model=BookingDetailResponse)
def get_booking(booking_id: str, db: Session = Depends(get_db)):
    """Fetch public booking status and digital tickets for confirmation page."""
    booking = db.query(Booking).filter(Booking.booking_id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking reference not found.")

    tickets_data = []
    for t in booking.tickets:
        tickets_data.append(TicketResponse(
            ticket_id=t.ticket_id,
            booking_id=booking.booking_id,
            customer_name=t.customer_name,
            event_name=t.event_name,
            ticket_status=t.ticket_status,
            checkin_status=t.checkin_status,
            checked_in_at=t.checked_in_at,
            created_at=t.created_at,
            qr_token_raw=t.qr_token_raw,
            qr_code_base64=qr_service.generate_qr_base64(t.qr_token_raw),
            ticket_url=f"{settings.FRONTEND_URL}/ticket/{t.qr_token_raw}"
        ))

    reg_amt = getattr(booking, "regular_amount", 0.0) or round(booking.ticket_count * booking.ticket_price, 2)
    grp_disc = getattr(booking, "group_discount", 0.0) or 0.0
    is_grp = grp_disc > 0 or (booking.ticket_count == 10 and grp_disc > 0)

    return BookingDetailResponse(
        id=booking.id,
        booking_id=booking.booking_id,
        customer_name=booking.customer_name,
        email=booking.email,
        phone=booking.phone,
        ticket_count=booking.ticket_count,
        ticket_price=booking.ticket_price,
        regular_amount=reg_amt,
        group_discount=grp_disc,
        ticket_subtotal=booking.ticket_subtotal or (reg_amt - grp_disc),
        convenience_fee=booking.convenience_fee or 0.0,
        payment_fee=booking.payment_fee or 0.0,
        gst_amount=booking.gst_amount or 0.0,
        amount=booking.amount,
        currency=booking.currency,
        is_group_offer=is_grp,
        offer_name="BUY 10, PAY FOR 9" if is_grp else None,
        payment_method=booking.payment_method or "UPI_MANUAL",
        utr_number=booking.utr_number,
        payment_screenshot=booking.payment_screenshot,
        verified_by=booking.verified_by,
        verified_at=booking.verified_at,
        rejection_reason=booking.rejection_reason,
        razorpay_order_id=booking.razorpay_order_id,
        razorpay_payment_id=booking.razorpay_payment_id,
        payment_status=booking.payment_status,
        booking_status=booking.booking_status,
        email_status=booking.email_status,
        email_sent_at=booking.email_sent_at,
        created_at=booking.created_at,
        tickets=tickets_data
    )

@router.get("/{booking_id}/pdf")
def download_booking_pdf(booking_id: str, db: Session = Depends(get_db)):
    """Generates and downloads bundled PDF tickets for the booking."""
    booking = db.query(Booking).filter(Booking.booking_id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found.")

    if booking.booking_status != "CONFIRMED" or booking.payment_status != "PAID":
        raise HTTPException(status_code=400, detail="Cannot generate tickets for unconfirmed booking.")

    event_setting = db.query(EventSetting).first() or EventSetting()
    pdf_bytes = ticket_service.generate_booking_bundle_pdf(booking, event_setting)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="GarbaNight_{booking.booking_id}_Tickets.pdf"'
        }
    )

@router.post("/{booking_id}/resend-email")
def resend_booking_email(booking_id: str, db: Session = Depends(get_db)):
    """Resends confirmation email with digital tickets to attendee."""
    booking = db.query(Booking).filter(Booking.booking_id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found.")

    if booking.booking_status != "CONFIRMED" or booking.payment_status != "PAID":
        raise HTTPException(status_code=400, detail="Cannot send tickets for unconfirmed booking.")

    from app.services.email_service import EmailService
    dispatched = EmailService.send_confirmation_email(booking.booking_id, db)
    return {
        "success": dispatched,
        "email": booking.email,
        "message": f"Tickets have been dispatched to {booking.email}" if dispatched else "Email queued or SMTP pending configuration."
    }

@router.get("/status/lookup", response_model=BookingDetailResponse)
def lookup_booking_status(
    booking_id: str,
    contact: str = None,
    db: Session = Depends(get_db)
):
    """Customer lookup for booking status using Booking ID and optional Phone/Email verification."""
    clean_id = (booking_id or "").strip().upper()
    query = db.query(Booking).filter(func.upper(Booking.booking_id) == clean_id)
    if contact and contact.strip():
        c = contact.strip().lower()
        from sqlalchemy import or_
        query = query.filter(
            or_(
                func.lower(Booking.email) == c,
                Booking.phone == c,
                Booking.phone.like(f"%{c[-10:]}")
            )
        )

    booking = query.first()
    if not booking:
        raise HTTPException(status_code=404, detail="No booking found matching the provided Booking ID and contact detail.")

    return get_booking(booking.booking_id, db)


