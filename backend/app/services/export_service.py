import csv
import io
import json
from datetime import datetime
from typing import Any, List, Optional, Generator
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc

from app.utils.timezone import format_ist_datetime
from app.models.booking import Booking
from app.models.payment import Payment
from app.models.ticket import Ticket
from app.models.checkin import CheckIn
from app.models.ticket_phase import TicketPhase
from app.models.user import User
from app.models.offers import OFFER_DEFINITIONS
from fastapi.responses import StreamingResponse

CHUNK_SIZE = 500

def sanitize_csv_cell(value: Any) -> Any:
    """
    Sanitizes values against CSV Formula Injection (DDE injection in Excel / Calc).
    If a string cell starts with '=', '+', '-', '@', '\\t', or '\\r', Excel can execute it
    as a formula or command. Prepending a single quote (') neutralizes execution while
    preserving the plain-text display.
    Numeric types (int, float) and booleans are preserved as-is so Excel calculations work.
    """
    if value is None:
        return ""
    if isinstance(value, (int, float, bool)):
        return value
    val_str = str(value)
    if not val_str:
        return ""
    if val_str[0] in ('=', '+', '-', '@', '\t', '\r'):
        return f"'{val_str}"
    stripped = val_str.lstrip()
    if stripped and stripped[0] in ('=', '+', '-', '@'):
        return f"'{val_str}"
    return val_str

def create_csv_streaming_response(headers: List[str], row_generator: Generator[List[Any], None, None], filename: str) -> StreamingResponse:
    """
    Wraps a row generator in a StreamingResponse with UTF-8 BOM for Microsoft Excel.
    Maintains O(1) memory by yielding CSV lines incrementally.
    """
    def iter_csv():
        output = io.StringIO()
        writer = csv.writer(output)
        # Write UTF-8 BOM so Microsoft Excel renders Unicode / symbols correctly
        output.write('\ufeff')
        writer.writerow([sanitize_csv_cell(h) for h in headers])
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)

        for row in row_generator:
            writer.writerow([sanitize_csv_cell(c) for c in row])
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

    return StreamingResponse(
        iter_csv(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )

def stream_bookings_rows(
    db: Session,
    payment_status: Optional[str] = None,
    booking_status: Optional[str] = None,
    offer_id: Optional[str] = None
) -> Generator[List[Any], None, None]:
    """Generates sanitized booking rows chunked by CHUNK_SIZE."""
    query = db.query(Booking)
    if payment_status and payment_status.strip():
        query = query.filter(Booking.payment_status == payment_status.strip().upper())
    if booking_status and booking_status.strip():
        query = query.filter(Booking.booking_status == booking_status.strip().upper())
    if offer_id and offer_id.strip():
        query = query.filter(Booking.offer_id == offer_id.strip())

    offset = 0
    while True:
        batch = query.order_by(desc(Booking.created_at), desc(Booking.id)).limit(CHUNK_SIZE).offset(offset).all()
        if not batch:
            break
        for b in batch:
            reg = getattr(b, "regular_amount", 0.0) or round(b.ticket_count * b.ticket_price, 2)
            disc = getattr(b, "group_discount", 0.0) or 0.0
            subtotal = b.ticket_subtotal or (reg - disc)
            fee = getattr(b, "payment_fee", 0.0) or getattr(b, "convenience_fee", 0.0) or 0.0
            gst = getattr(b, "gst_amount", 0.0) or 0.0
            yield [
                b.booking_id,
                b.customer_name,
                b.phone,
                b.email,
                b.ticket_count,
                b.offer_id or "N/A",
                b.offer_title or b.ticket_phase or "N/A",
                b.ticket_price,
                reg,
                disc,
                subtotal,
                fee,
                gst,
                b.amount,
                b.payment_method,
                b.utr_number or "N/A",
                b.razorpay_order_id or "N/A",
                b.razorpay_payment_id or "N/A",
                b.payment_status,
                b.booking_status,
                b.email_status,
                format_ist_datetime(b.created_at, "%d %b %Y, %I:%M %p"),
                format_ist_datetime(b.updated_at, "%d %b %Y, %I:%M %p") if b.updated_at else "N/A"
            ]
        offset += len(batch)
        if len(batch) < CHUNK_SIZE:
            break

def stream_payments_rows(
    db: Session,
    payment_status: Optional[str] = None,
    payment_method: Optional[str] = None
) -> Generator[List[Any], None, None]:
    """Generates sanitized payment rows chunked by CHUNK_SIZE."""
    query = db.query(Payment).options(joinedload(Payment.booking))
    if payment_status and payment_status.strip():
        query = query.filter(Payment.payment_status == payment_status.strip().upper())
    if payment_method and payment_method.strip():
        query = query.filter(Payment.payment_method == payment_method.strip().upper())

    offset = 0
    while True:
        batch = query.order_by(desc(Payment.created_at), desc(Payment.id)).limit(CHUNK_SIZE).offset(offset).all()
        if not batch:
            break
        for p in batch:
            booking = p.booking
            yield [
                p.payment_id or f"PAY-{p.id}",
                booking.booking_id if booking else (f"ID-{p.booking_id}" if p.booking_id else "N/A"),
                booking.customer_name if booking else "N/A",
                booking.phone if booking else "N/A",
                booking.email if booking else "N/A",
                p.payment_method,
                p.amount,
                p.currency,
                p.payment_status or p.status,
                p.utr_number or "N/A",
                p.razorpay_order_id or "N/A",
                p.razorpay_payment_id or "N/A",
                p.verified_by or "N/A",
                format_ist_datetime(p.verified_at, "%d %b %Y, %I:%M %p") if p.verified_at else "N/A",
                p.rejection_reason or "N/A",
                format_ist_datetime(p.created_at, "%d %b %Y, %I:%M %p")
            ]
        offset += len(batch)
        if len(batch) < CHUNK_SIZE:
            break

def stream_tickets_rows(
    db: Session,
    ticket_status: Optional[str] = None,
    checkin_status: Optional[bool] = None
) -> Generator[List[Any], None, None]:
    """
    Generates sanitized ticket rows chunked by CHUNK_SIZE.
    NEVER exports raw QR verification tokens or cryptographic hashes.
    """
    query = db.query(Ticket).options(joinedload(Ticket.booking))
    if ticket_status and ticket_status.strip():
        query = query.filter(Ticket.ticket_status == ticket_status.strip().upper())
    if checkin_status is not None:
        query = query.filter(Ticket.checkin_status == checkin_status)

    offset = 0
    while True:
        batch = query.order_by(desc(Ticket.created_at), desc(Ticket.id)).limit(CHUNK_SIZE).offset(offset).all()
        if not batch:
            break
        for t in batch:
            booking = t.booking
            yield [
                t.ticket_id,
                booking.booking_id if booking else (f"ID-{t.booking_id}" if t.booking_id else "N/A"),
                t.customer_name,
                t.event_name,
                t.ticket_status,
                "YES" if t.checkin_status else "NO",
                format_ist_datetime(t.checked_in_at, "%d %b %Y, %I:%M %p") if t.checked_in_at else "N/A",
                format_ist_datetime(t.created_at, "%d %b %Y, %I:%M %p")
            ]
        offset += len(batch)
        if len(batch) < CHUNK_SIZE:
            break

def stream_checkins_rows(
    db: Session,
    result: Optional[str] = None
) -> Generator[List[Any], None, None]:
    """Generates sanitized check-in rows chunked by CHUNK_SIZE."""
    query = db.query(CheckIn).options(joinedload(CheckIn.ticket), joinedload(CheckIn.staff))
    if result and result.strip():
        query = query.filter(CheckIn.result == result.strip().upper())

    offset = 0
    while True:
        batch = query.order_by(desc(CheckIn.checked_in_at), desc(CheckIn.id)).limit(CHUNK_SIZE).offset(offset).all()
        if not batch:
            break
        for c in batch:
            ticket = c.ticket
            staff = c.staff
            yield [
                c.id,
                ticket.ticket_id if ticket else "N/A",
                ticket.customer_name if ticket else "N/A",
                staff.name if staff else "Gate Scanner / Auto",
                staff.email if staff else "N/A",
                c.result,
                c.device_information or "N/A",
                c.notes or "N/A",
                format_ist_datetime(c.checked_in_at, "%d %b %Y, %I:%M %p")
            ]
        offset += len(batch)
        if len(batch) < CHUNK_SIZE:
            break

def stream_offers_inventory_rows(db: Session) -> Generator[List[Any], None, None]:
    """Generates authoritative offer and ticket phase inventory rows."""
    phases = db.query(TicketPhase).order_by(TicketPhase.display_order).all()
    for p in phases:
        rem = max(0, p.total_inventory - p.sold_count)
        yield [
            "PHASE",
            p.phase_code,
            p.name,
            1,
            p.price,
            p.status,
            p.total_inventory,
            p.sold_count,
            rem,
            "YES" if p.group_offer_eligible else "NO",
            "NO",
            p.badge_text or "N/A",
            format_ist_datetime(p.updated_at, "%d %b %Y, %I:%M %p") if p.updated_at else "N/A"
        ]

    for offer_id, meta in OFFER_DEFINITIONS.items():
        yield [
            "OFFER",
            offer_id,
            meta.get("title", offer_id),
            meta.get("passes_per_unit", 1),
            meta.get("price_per_unit", 0.0),
            meta.get("phase_code", "EARLY_BIRD"),
            "N/A",
            "N/A",
            "N/A",
            "YES" if meta.get("type") == "GROUP" else "NO",
            "YES" if meta.get("requires_id_proof") else "NO",
            meta.get("badge", "N/A"),
            "CONFIGURED"
        ]

def stream_users_rows(db: Session) -> Generator[List[Any], None, None]:
    """
    Generates sanitized user rows.
    NEVER exports password hashes, salt, or session tokens.
    """
    users = db.query(User).order_by(User.id).all()
    for u in users:
        yield [
            u.id,
            u.name,
            u.email,
            u.role,
            "ACTIVE" if u.is_active else "INACTIVE",
            format_ist_datetime(u.last_login_at, "%d %b %Y, %I:%M %p") if u.last_login_at else "NEVER",
            format_ist_datetime(u.created_at, "%d %b %Y, %I:%M %p")
        ]
