import os
import io
import time
import uuid
from typing import Optional
from PIL import Image

from fastapi import APIRouter, Depends, HTTPException, Request, Header, Query, Form, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.models.event_setting import EventSetting
from app.schemas.payment import (
    CalculateFeeRequest,
    CalculateFeeResponse,
    CreateOrderRequest,
    CreateOrderResponse,
    SubmitPaymentProofResponse,
    VerifyPaymentRequest,
    VerifyPaymentResponse
)
from app.services.booking_service import booking_service
from app.services.payment_service import payment_service
from app.utils.validators import validate_indian_phone, validate_email_format, normalize_indian_phone

router = APIRouter(prefix="/api/payments", tags=["Payments"])

SCREENSHOTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "uploads", "screenshots"))
QR_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "uploads", "qr"))

@router.get("/calculate", response_model=CalculateFeeResponse)
def calculate_fee(
    ticket_count: Optional[int] = Query(None, ge=1, le=500),
    ticket_phase: Optional[str] = Query("EARLY_BIRD"),
    offer_id: Optional[str] = Query(None),
    quantity: Optional[int] = Query(1, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Calculates server-side ticket pricing breakdown using the active payment provider, ticket phase, or offer."""
    return booking_service.calculate_pricing(
        db=db,
        ticket_count=ticket_count or 1,
        ticket_phase=ticket_phase,
        offer_id=offer_id,
        quantity=quantity or 1
    )

@router.post("/calculate", response_model=CalculateFeeResponse)
def calculate_fee_post(payload: CalculateFeeRequest, db: Session = Depends(get_db)):
    """Calculates server-side ticket pricing breakdown for a mixed cart or single offer via POST."""
    return booking_service.calculate_pricing(
        db=db,
        ticket_count=payload.ticket_count or 1,
        ticket_phase=payload.ticket_phase,
        offer_id=payload.offer_id,
        quantity=payload.quantity or 1,
        items=payload.items
    )

@router.get("/create-order")
@router.get("/create-order/")
def get_create_order_info():
    """Informational endpoint if visited directly via browser GET."""
    return {
        "status": "ready",
        "service": "Create Payment Order API",
        "note": "This endpoint requires an HTTP POST request with booking payload. Please complete bookings via the website."
    }

@router.post("/create-order", response_model=CreateOrderResponse)
@router.post("/create-order/", response_model=CreateOrderResponse)
def create_payment_order(payload: CreateOrderRequest, db: Session = Depends(get_db)):
    """Initiates a booking and returns checkout parameters (UPI QR or Razorpay)."""
    if not validate_email_format(payload.email):
        raise HTTPException(status_code=400, detail="Invalid email format.")

    if not validate_indian_phone(payload.phone):
        raise HTTPException(
            status_code=400,
            detail="Invalid Indian phone number. Please enter a valid 10-digit mobile number."
        )

    phone_clean = normalize_indian_phone(payload.phone)

    booking, order_info = booking_service.initiate_order(
        customer_name=payload.customer_name,
        email=payload.email,
        phone=phone_clean,
        ticket_count=payload.ticket_count,
        ticket_phase=getattr(payload, "ticket_phase", "EARLY_BIRD") or "EARLY_BIRD",
        db=db,
        idempotency_key=payload.idempotency_key,
        offer_id=payload.offer_id,
        quantity=payload.quantity or 1,
        child_name=payload.child_name,
        child_age=payload.child_age,
        items=payload.items,
        children=payload.children
    )

    active_method = order_info.get("payment_method", getattr(booking, "payment_method", "RAZORPAY"))
    is_razorpay = (active_method or "").strip().upper() in ("RAZORPAY", "RZP")
    razorpay_mode = (
        order_info.get("razorpay_mode")
        or os.environ.get("RAZORPAY_MODE")
        or getattr(settings, "RAZORPAY_MODE", "TEST")
    ).strip().upper()

    return CreateOrderResponse(
        payment_method="RAZORPAY" if is_razorpay else "UPI_MANUAL",
        payment_id=order_info.get("payment_id", f"PAY-{booking.booking_id}"),
        booking_id=booking.booking_id,
        ticket_phase=order_info.get("ticket_phase", getattr(booking, "ticket_phase", "EARLY_BIRD")),
        phase_name=order_info.get("phase_name", "Early Bird"),
        amount=order_info.get("amount", booking.amount),
        currency=order_info.get("currency", "INR"),
        ticket_price=order_info.get("ticket_price", booking.ticket_price),
        ticket_count=order_info.get("ticket_count", booking.ticket_count),
        regular_amount=order_info.get("regular_amount", getattr(booking, "regular_amount", booking.ticket_count * 599.0)),
        group_discount=order_info.get("group_discount", getattr(booking, "group_discount", 0.0)),
        ticket_subtotal=order_info.get("ticket_subtotal", getattr(booking, "ticket_subtotal", booking.amount)),
        payment_fee=order_info.get("payment_fee", getattr(booking, "payment_fee", 0.0)),
        gst_amount=order_info.get("gst_amount", getattr(booking, "gst_amount", 0.0)),
        tax_amount=order_info.get("tax_amount", 0.0),
        base_amount=order_info.get("base_amount", 0.0),
        tax_rate=order_info.get("tax_rate", 0.18),
        tax_included=order_info.get("tax_included", True),
        tax_label=order_info.get("tax_label", "Taxes included"),
        customer_name=booking.customer_name,
        customer_email=booking.email,
        customer_phone=booking.phone,
        is_group_offer=order_info.get("is_group_offer", (getattr(booking, "group_discount", 0.0) or 0) > 0),
        offer_name=order_info.get("offer_name", "Group of 10" if (getattr(booking, "group_discount", 0.0) or 0) > 0 else None),
        offer_id=booking.offer_id,
        offer_title=booking.offer_title,
        passes_count=booking.ticket_count,
        child_name=booking.child_name,
        child_age=booking.child_age,
        free_tickets=order_info.get("free_tickets", 0),
        items=order_info.get("items"),
        total_passes=order_info.get("total_passes", booking.ticket_count),
        is_mixed_cart=order_info.get("is_mixed_cart", False),
        children_details=order_info.get("children_details"),
        # UPI Manual details (strictly suppressed for Razorpay orders)
        upi_id=None if is_razorpay else order_info.get("upi_id"),
        upi_qr_image_url=None if is_razorpay else order_info.get("upi_qr_image_url", "/api/payments/qr-image"),
        upi_payment_instructions=None if is_razorpay else order_info.get("upi_payment_instructions"),
        # Razorpay details
        razorpay_order_id=order_info.get("razorpay_order_id"),
        key_id=order_info.get("key_id"),
        razorpay_mode=razorpay_mode,
        is_simulation=order_info.get("is_simulation", False)
    )

@router.post("/submit-manual-proof", response_model=SubmitPaymentProofResponse)
async def submit_manual_payment_proof(
    booking_id: str = Form(...),
    utr_number: str = Form(...),
    screenshot: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """
    Submits customer UTR and optional screenshot for manual UPI verification.
    Validates file format, size, and image integrity strictly.
    """
    screenshot_filename = None
    if screenshot and screenshot.filename:
        # Validate file extension
        ext = os.path.splitext(screenshot.filename)[1].lower()
        if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid screenshot format. Only JPG, PNG, and WebP image files are allowed."
            )

        # Validate MIME content type
        if screenshot.content_type not in ["image/jpeg", "image/png", "image/webp", "image/jpg"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid file type. Only JPEG, PNG, or WebP image files are permitted."
            )

        # Read content and validate max file size (5MB)
        file_bytes = await screenshot.read()
        max_size = 5 * 1024 * 1024
        if len(file_bytes) > max_size:
            raise HTTPException(
                status_code=400,
                detail="Screenshot file exceeds the 5MB maximum limit."
            )

        # Strict Image Verification with PIL: Reject executables, scripts, or corrupt files
        try:
            img = Image.open(io.BytesIO(file_bytes))
            img.verify()
        except Exception:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is not a valid image or is corrupted."
            )

        # Save securely with non-guessable random UUID filename in private directory
        os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
        screenshot_filename = f"proof_{uuid.uuid4().hex}_{int(time.time())}{ext}"
        saved_path = os.path.join(SCREENSHOTS_DIR, screenshot_filename)
        with open(saved_path, "wb") as f:
            f.write(file_bytes)

    # Submit proof via payment service
    updated_booking = payment_service.submit_manual_proof(
        booking_id=booking_id,
        utr_number=utr_number,
        screenshot_filename=screenshot_filename,
        db=db
    )

    return SubmitPaymentProofResponse(
        success=True,
        message="We have received your payment details. Your booking will be confirmed after payment verification.",
        booking_id=updated_booking.booking_id,
        booking_status=updated_booking.booking_status,
        payment_status=updated_booking.payment_status,
        utr_number=updated_booking.utr_number or utr_number
    )

@router.get("/qr-image")
def get_upi_qr_image(db: Session = Depends(get_db)):
    """Serves the active UPI QR code image or generates one dynamically."""
    setting = db.query(EventSetting).first()
    qr_file = getattr(setting, "upi_qr_image", None)

    candidates = [
        qr_file,
        os.path.join(QR_DIR, "upi_qr.jpg"),
        os.path.join("uploads", "qr", "upi_qr.jpg"),
    ]

    for cand in candidates:
        if cand and os.path.isfile(cand):
            media_type = "image/jpeg"
            if cand.lower().endswith(".png"):
                media_type = "image/png"
            elif cand.lower().endswith(".webp"):
                media_type = "image/webp"
            return FileResponse(cand, media_type=media_type)

    # Dynamic UPI QR generation fallback
    import qrcode
    from fastapi.responses import Response

    upi_id = (getattr(setting, "upi_id", None) or "").strip() or settings.UPI_ID or "samaymadhyastha2005@oksbi"
    event_name = (getattr(setting, "event_name", None) or "").strip() or "NAVRANG 2026"
    upi_url = f"upi://pay?pa={upi_id}&pn={event_name}&cu=INR"

    img = qrcode.make(upi_url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return Response(content=buf.getvalue(), media_type="image/png")

@router.post("/verify", response_model=VerifyPaymentResponse)
def verify_payment(payload: VerifyPaymentRequest, db: Session = Depends(get_db)):
    """Verifies Razorpay payment signature and confirms booking."""
    from app.models.booking import Booking
    booking = db.query(Booking).filter(Booking.booking_id == payload.booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found.")

    # Idempotency check: If already confirmed, return success directly
    if booking.booking_status == "CONFIRMED" and booking.payment_status in ["PAID", "CAPTURED"]:
        return VerifyPaymentResponse(
            success=True,
            message="Payment already verified and confirmed. Tickets issued!",
            booking_id=booking.booking_id,
            payment_status=booking.payment_status,
            booking_status=booking.booking_status
        )

    # Validate Order ID
    expected_order_id = booking.razorpay_order_id or ""
    incoming_order_id = payload.razorpay_order_id or expected_order_id

    if expected_order_id and incoming_order_id != expected_order_id:
        raise HTTPException(
            status_code=400,
            detail="Payment verification failed: Razorpay order ID mismatch."
        )

    is_valid = payment_service.verify_payment(
        order_id=incoming_order_id,
        payment_id=payload.razorpay_payment_id or "",
        signature=payload.razorpay_signature or "",
        db=db
    )

    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail="Payment verification failed: Invalid transaction signature."
        )

    # Confirm booking atomically and generate tickets
    confirmed_booking = booking_service.confirm_booking_and_generate_tickets(
        booking_id=payload.booking_id,
        razorpay_payment_id=payload.razorpay_payment_id,
        razorpay_signature=payload.razorpay_signature,
        db=db,
        payment_method="RAZORPAY"
    )

    return VerifyPaymentResponse(
        success=True,
        message="Payment verified successfully. Tickets issued!",
        booking_id=confirmed_booking.booking_id,
        payment_status=confirmed_booking.payment_status,
        booking_status=confirmed_booking.booking_status
    )

@router.post("/webhook", summary="Canonical Razorpay Webhook Endpoint")
@router.post(
    "/razorpay/webhook",
    deprecated=True,
    summary="Legacy Razorpay Webhook Endpoint (Alias to /api/payments/webhook)"
)
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Handles incoming Razorpay asynchronous webhooks with HMAC-SHA256 signature verification.

    Canonical Endpoint: /api/payments/webhook
    Legacy Aliases:
      - /api/payments/razorpay/webhook (same router alias)
      - /api/webhook/razorpay (legacy router internal delegation)

    Supported Events:
      - payment.captured (confirms booking & generates QR tickets)
      - order.paid (confirms booking & generates QR tickets)
      - payment.failed (updates booking to PAYMENT_FAILED & releases reservation hold)

    Guarantees:
      - HMAC-SHA256 signature verification via RAZORPAY_WEBHOOK_SECRET
      - Idempotent processing of duplicate events
      - Amount validation against database booking amount (in paise)
    """
    signature = (
        x_razorpay_signature
        or request.headers.get("x-razorpay-signature")
        or request.headers.get("X-Razorpay-Signature")
    )
    body_bytes = await request.body()
    result = payment_service.process_webhook(body_bytes, signature, db)
    return result

@router.post("/retry/{booking_id}", response_model=CreateOrderResponse)
def retry_payment(booking_id: str, db: Session = Depends(get_db)):
    """Re-initiates payment order for an existing pending or failed booking."""
    from app.models.booking import Booking
    booking = db.query(Booking).filter(Booking.booking_id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found.")

    if booking.booking_status == "CONFIRMED" and booking.payment_status in ["PAID", "CAPTURED"]:
        raise HTTPException(status_code=400, detail="This booking has already been verified and confirmed.")

    # Re-verify capacity
    is_avail, remaining, _ = booking_service.check_capacity(db, requested_tickets=booking.ticket_count)
    if not is_avail:
        raise HTTPException(status_code=400, detail=f"Only {remaining} tickets remaining. Cannot fulfill order.")

    provider = payment_service.get_provider(db)
    order_info = provider.initiate_payment(booking=booking, db=db)
    pricing = provider.calculate_pricing(db, booking.ticket_count)

    return CreateOrderResponse(
        payment_method=order_info.get("payment_method", "RAZORPAY"),
        payment_id=order_info.get("payment_id", f"PAY-{booking.booking_id}"),
        booking_id=booking.booking_id,
        amount=order_info.get("amount", booking.amount),
        currency=order_info.get("currency", "INR"),
        ticket_price=pricing.get("ticket_price", booking.ticket_price),
        ticket_count=booking.ticket_count,
        regular_amount=pricing.get("regular_amount", getattr(booking, "regular_amount", booking.ticket_count * 599.0)),
        group_discount=pricing.get("group_discount", getattr(booking, "group_discount", 0.0)),
        ticket_subtotal=pricing.get("ticket_subtotal", getattr(booking, "ticket_subtotal", booking.amount)),
        payment_fee=pricing.get("payment_fee", 0.0),
        gst_amount=pricing.get("gst_amount", 0.0),
        tax_amount=pricing.get("tax_amount", 0.0),
        base_amount=pricing.get("base_amount", 0.0),
        tax_rate=pricing.get("tax_rate", 0.18),
        tax_included=pricing.get("tax_included", True),
        tax_label=pricing.get("tax_label", "Taxes included"),
        customer_name=booking.customer_name,
        customer_email=booking.email,
        customer_phone=booking.phone,
        is_group_offer=pricing.get("is_group_offer", False),
        offer_name=pricing.get("offer_name"),
        free_tickets=pricing.get("free_tickets", 0),
        razorpay_order_id=order_info.get("razorpay_order_id"),
        key_id=order_info.get("key_id"),
        razorpay_mode=(
            order_info.get("razorpay_mode")
            or os.environ.get("RAZORPAY_MODE")
            or getattr(settings, "RAZORPAY_MODE", "TEST")
        ).strip().upper(),
        is_simulation=False
    )

@router.post("/fail/{booking_id}")
def mark_payment_failed(booking_id: str, reason: Optional[str] = None, db: Session = Depends(get_db)):
    """Marks a booking payment as failed if customer aborts or gateway declines."""
    from app.models.booking import Booking
    from app.models.payment import Payment
    booking = db.query(Booking).filter(Booking.booking_id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found.")

    if booking.booking_status != "CONFIRMED":
        booking.payment_status = "FAILED"
        booking.booking_status = "PAYMENT_FAILED"
        booking.reservation_expires_at = None
        payment = db.query(Payment).filter(Payment.booking_id == booking.id).first()
        if payment:
            payment.payment_status = "FAILED"
            payment.status = "FAILED"
            if reason:
                payment.rejection_reason = reason
        db.commit()
    return {"status": "ok", "booking_id": booking.booking_id, "payment_status": "FAILED"}

