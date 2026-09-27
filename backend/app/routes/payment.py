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
    ticket_count: int = Query(1, ge=1, le=10),
    db: Session = Depends(get_db)
):
    """Calculates server-side ticket pricing breakdown using the active payment provider."""
    return booking_service.calculate_pricing(db=db, ticket_count=ticket_count)

@router.post("/create-order", response_model=CreateOrderResponse)
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
        db=db,
        idempotency_key=payload.idempotency_key
    )

    return CreateOrderResponse(
        payment_method=order_info.get("payment_method", getattr(booking, "payment_method", "UPI_MANUAL")),
        payment_id=order_info.get("payment_id", f"PAY-{booking.booking_id}"),
        booking_id=booking.booking_id,
        amount=order_info.get("amount", booking.amount),
        currency=order_info.get("currency", "INR"),
        ticket_price=order_info.get("ticket_price", booking.ticket_price),
        ticket_count=order_info.get("ticket_count", booking.ticket_count),
        regular_amount=order_info.get("regular_amount", getattr(booking, "regular_amount", booking.ticket_count * 599.0)),
        group_discount=order_info.get("group_discount", getattr(booking, "group_discount", 0.0)),
        ticket_subtotal=order_info.get("ticket_subtotal", getattr(booking, "ticket_subtotal", booking.amount)),
        payment_fee=order_info.get("payment_fee", getattr(booking, "payment_fee", 0.0)),
        gst_amount=order_info.get("gst_amount", getattr(booking, "gst_amount", 0.0)),
        customer_name=booking.customer_name,
        customer_email=booking.email,
        customer_phone=booking.phone,
        is_group_offer=order_info.get("is_group_offer", (getattr(booking, "group_discount", 0.0) or 0) > 0),
        offer_name=order_info.get("offer_name", "BUY 10, PAY FOR 9" if (getattr(booking, "group_discount", 0.0) or 0) > 0 else None),
        free_tickets=order_info.get("free_tickets", 1 if (getattr(booking, "group_discount", 0.0) or 0) > 0 else 0),
        # UPI Manual details
        upi_id=order_info.get("upi_id"),
        upi_qr_image_url=order_info.get("upi_qr_image_url", "/api/payments/qr-image"),
        upi_payment_instructions=order_info.get("upi_payment_instructions"),
        # Razorpay details
        razorpay_order_id=order_info.get("razorpay_order_id"),
        key_id=order_info.get("key_id"),
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
    """Serves the active UPI QR code image prominently."""
    setting = db.query(EventSetting).first()
    qr_file = getattr(setting, "upi_qr_image", None)

    candidates = [
        qr_file,
        os.path.join(QR_DIR, "upi_qr.jpg"),
        os.path.join("uploads", "qr", "upi_qr.jpg"),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "frontend", "public", "upi_qr_code.jpg"))
    ]

    for cand in candidates:
        if cand and os.path.isfile(cand):
            media_type = "image/jpeg"
            if cand.lower().endswith(".png"):
                media_type = "image/png"
            elif cand.lower().endswith(".webp"):
                media_type = "image/webp"
            return FileResponse(cand, media_type=media_type)

    raise HTTPException(status_code=404, detail="UPI QR code image not found.")

@router.post("/verify", response_model=VerifyPaymentResponse)
def verify_payment(payload: VerifyPaymentRequest, db: Session = Depends(get_db)):
    """Verifies Razorpay payment signature and confirms booking."""
    is_valid = payment_service.verify_payment(
        order_id=payload.razorpay_order_id or "",
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
    booking = booking_service.confirm_booking_and_generate_tickets(
        booking_id=payload.booking_id,
        razorpay_payment_id=payload.razorpay_payment_id,
        razorpay_signature=payload.razorpay_signature,
        db=db,
        payment_method="RAZORPAY"
    )

    return VerifyPaymentResponse(
        success=True,
        message="Payment verified successfully. Tickets issued!",
        booking_id=booking.booking_id,
        payment_status=booking.payment_status,
        booking_status=booking.booking_status
    )

@router.post("/webhook")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(None),
    db: Session = Depends(get_db)
):
    """Handles incoming Razorpay asynchronous webhooks with signature verification."""
    body_bytes = await request.body()
    result = payment_service.process_webhook(body_bytes, x_razorpay_signature, db)
    return result
