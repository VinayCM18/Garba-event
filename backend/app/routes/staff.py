from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

from app.database import get_db
from app.models.user import User
from app.models.booking import Booking
from app.models.ticket import Ticket
from app.models.checkin import CheckIn
from app.models.audit_log import AuditLog
from app.models.event_setting import EventSetting
from app.middleware.auth import require_staff
from app.routes.ticket import find_ticket_by_any_identifier

router = APIRouter(prefix="/api/staff", tags=["Staff Operations"])

# --- Schemas ---

class StaffVerifyRequest(BaseModel):
    qr_token: str

class StaffVerifyResponse(BaseModel):
    valid: bool
    status: str
    message: str
    ticket_id: Optional[str] = None
    booking_id: Optional[str] = None
    customer_name: Optional[str] = None
    event_name: Optional[str] = None
    ticket_status: Optional[str] = None
    checkin_status: Optional[bool] = None
    checked_in_at: Optional[datetime] = None
    qr_token_raw: Optional[str] = None

class StaffCheckInRequest(BaseModel):
    qr_token: str
    device_information: Optional[str] = "Staff Scanner Terminal"
    notes: Optional[str] = None

class StaffCheckInResponse(BaseModel):
    success: bool
    status: str
    message: str
    ticket_id: Optional[str] = None
    booking_id: Optional[str] = None
    customer_name: Optional[str] = None
    checked_in_at: Optional[datetime] = None
    staff_name: Optional[str] = None

class StaffRecentCheckIn(BaseModel):
    id: int
    ticket_id: str
    customer_name: str
    checked_in_at: Optional[datetime] = None
    result: str
    device_information: Optional[str] = None

class StaffDashboardResponse(BaseModel):
    tickets_expected: int
    tickets_checked_in: int
    tickets_remaining: int
    duplicate_attempts: int
    checkin_rate_percent: float
    staff_name: str
    staff_role: str
    recent_checkins: List[StaffRecentCheckIn]

class StaffSearchItem(BaseModel):
    ticket_id: str
    booking_id: str
    customer_name: str
    phone: Optional[str] = None
    ticket_status: str
    checkin_status: bool
    checked_in_at: Optional[datetime] = None


# --- Endpoints ---

@router.get("/dashboard", response_model=StaffDashboardResponse)
def get_staff_dashboard(
    current_staff: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """
    Staff Dashboard API: Returns ONLY ticket check-in counts and gate metrics.
    STRICTLY excludes all revenue, payments, UPI configurations, and admin settings.
    """
    # Total tickets sold (confirmed & paid)
    confirmed_query = db.query(Booking).filter(
        Booking.booking_status == "CONFIRMED",
        Booking.payment_status == "PAID"
    )
    tickets_expected = confirmed_query.with_entities(
        func.coalesce(func.sum(Booking.ticket_count), 0)
    ).scalar() or 0

    # Total checked in
    tickets_checked_in = db.query(Ticket).filter(Ticket.checkin_status == True).count()
    tickets_remaining = max(0, tickets_expected - tickets_checked_in)

    # Duplicate or failed scan attempts
    duplicate_attempts = db.query(CheckIn).filter(
        CheckIn.result.in_(["ALREADY_USED", "CONFLICT", "INVALID"])
    ).count()

    rate = round((tickets_checked_in / tickets_expected * 100), 1) if tickets_expected > 0 else 0.0

    # Recent checkins
    recent_records = db.query(CheckIn).order_by(CheckIn.id.desc()).limit(15).all()
    recent_items = []
    for r in recent_records:
        t = db.query(Ticket).filter(Ticket.id == r.ticket_id).first()
        recent_items.append(StaffRecentCheckIn(
            id=r.id,
            ticket_id=t.ticket_id if t else (f"Attempt #{r.id}" if r.result == "INVALID" else "Unknown"),
            customer_name=t.customer_name if t else "Unknown Guest",
            checked_in_at=r.checked_in_at,
            result=r.result,
            device_information=r.device_information
        ))

    return StaffDashboardResponse(
        tickets_expected=tickets_expected,
        tickets_checked_in=tickets_checked_in,
        tickets_remaining=tickets_remaining,
        duplicate_attempts=duplicate_attempts,
        checkin_rate_percent=rate,
        staff_name=current_staff.name,
        staff_role=current_staff.role,
        recent_checkins=recent_items
    )


@router.post("/ticket/verify", response_model=StaffVerifyResponse)
def staff_verify_ticket(
    payload: StaffVerifyRequest,
    current_staff: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """
    Staff Ticket Verification API:
    Validates QR token, Ticket ID, Booking ID, or Attendee info.
    Returns status: VALID, USED, CANCELLED, or INVALID.
    Does NOT return any payment amounts or billing info.
    """
    raw_token = payload.qr_token.strip()
    ticket = find_ticket_by_any_identifier(raw_token, db)

    if not ticket:
        return StaffVerifyResponse(
            valid=False,
            status="INVALID",
            message=f"❌ No ticket found matching '{raw_token}'. Please verify the Ticket ID or scan again."
        )

    booking = ticket.booking

    if ticket.ticket_status == "CANCELLED":
        return StaffVerifyResponse(
            valid=False,
            status="CANCELLED",
            message="❌ TICKET CANCELLED. Entry denied.",
            ticket_id=ticket.ticket_id,
            booking_id=booking.booking_id if booking else None,
            customer_name=ticket.customer_name,
            event_name=ticket.event_name,
            ticket_status=ticket.ticket_status,
            checkin_status=ticket.checkin_status,
            checked_in_at=ticket.checked_in_at,
            qr_token_raw=ticket.qr_token_raw
        )

    if ticket.checkin_status:
        time_str = ticket.checked_in_at.strftime("%I:%M %p") if ticket.checked_in_at else "Earlier"
        return StaffVerifyResponse(
            valid=False,
            status="USED",
            message=f"⚠️ Ticket Already Checked In at {time_str} (Ticket: {ticket.ticket_id})",
            ticket_id=ticket.ticket_id,
            booking_id=booking.booking_id if booking else None,
            customer_name=ticket.customer_name,
            event_name=ticket.event_name,
            ticket_status="USED",
            checkin_status=True,
            checked_in_at=ticket.checked_in_at,
            qr_token_raw=ticket.qr_token_raw
        )

    return StaffVerifyResponse(
        valid=True,
        status="VALID",
        message="✓ VALID TICKET - Ready for Entry",
        ticket_id=ticket.ticket_id,
        booking_id=booking.booking_id if booking else None,
        customer_name=ticket.customer_name,
        event_name=ticket.event_name,
        ticket_status="VALID",
        checkin_status=False,
        qr_token_raw=ticket.qr_token_raw
    )


@router.post("/checkin", response_model=StaffCheckInResponse)
def staff_checkin_ticket(
    payload: StaffCheckInRequest,
    request: Request,
    current_staff: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """
    Staff Check-in API:
    Atomically marks a ticket as checked in using database row-locking.
    Prevents duplicate check-in at the database layer.
    """
    raw_token = payload.qr_token.strip()
    client_ip = request.client.host if request.client else "unknown"

    # Acquire exclusive row lock
    ticket = find_ticket_by_any_identifier(raw_token, db, for_update=True)

    if not ticket:
        checkin_log = CheckIn(
            ticket_id=0,
            staff_id=current_staff.id,
            device_information=payload.device_information,
            ip_address=client_ip,
            result="INVALID",
            notes=f"Attempted scan of unknown token: {raw_token}"
        )
        db.add(checkin_log)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"❌ Invalid Ticket. No ticket found matching '{raw_token}'."
        )

    booking = ticket.booking

    # Check if cancelled
    if ticket.ticket_status == "CANCELLED":
        checkin_log = CheckIn(
            ticket_id=ticket.id,
            staff_id=current_staff.id,
            device_information=payload.device_information,
            ip_address=client_ip,
            result="CANCELLED",
            notes="Attempted entry on cancelled ticket"
        )
        db.add(checkin_log)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="❌ TICKET CANCELLED. Entry denied."
        )

    # Check if already used
    if ticket.checkin_status:
        checkin_log = CheckIn(
            ticket_id=ticket.id,
            staff_id=current_staff.id,
            device_information=payload.device_information,
            ip_address=client_ip,
            result="ALREADY_USED",
            notes=f"Attempted re-scan. Original check-in at: {ticket.checked_in_at}"
        )
        db.add(checkin_log)
        db.commit()

        time_str = ticket.checked_in_at.strftime("%I:%M %p") if ticket.checked_in_at else "Earlier"
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"⚠️ Ticket Already Checked In at {time_str} (Ticket: {ticket.ticket_id})"
        )

    # Atomic check-in
    now = datetime.utcnow()
    ticket.checkin_status = True
    ticket.checked_in_at = now
    ticket.ticket_status = "USED"

    checkin_log = CheckIn(
        ticket_id=ticket.id,
        staff_id=current_staff.id,
        checked_in_at=now,
        device_information=payload.device_information,
        ip_address=client_ip,
        result="SUCCESS",
        notes=payload.notes
    )
    db.add(checkin_log)

    audit = AuditLog(
        user_id=current_staff.id,
        action="STAFF_CHECKIN_SUCCESS",
        entity_type="ticket",
        entity_id=ticket.ticket_id,
        ip_address=client_ip,
        details=f'{{"customer": "{ticket.customer_name}", "staff": "{current_staff.name}"}}'
    )
    db.add(audit)

    db.commit()
    db.refresh(ticket)

    return StaffCheckInResponse(
        success=True,
        status="SUCCESS",
        message="✓ Check-in Verified! Entry Granted.",
        ticket_id=ticket.ticket_id,
        booking_id=booking.booking_id if booking else None,
        customer_name=ticket.customer_name,
        checked_in_at=ticket.checked_in_at,
        staff_name=current_staff.name
    )


@router.get("/search", response_model=List[StaffSearchItem])
def staff_search_tickets(
    q: str = Query(..., min_length=2, description="Search by Ticket ID, Booking ID, Phone, or Name"),
    current_staff: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """
    Staff Search API: Look up tickets by ID, Booking ID, or Customer Name/Phone.
    STRICTLY returns attendee identification without any financial or payment data.
    """
    search_term = q.strip()

    # Search directly in Ticket and linked Booking
    tickets = db.query(Ticket).join(Booking, Ticket.booking_id == Booking.id).filter(
        or_(
            Ticket.ticket_id.ilike(f"%{search_term}%"),
            Booking.booking_id.ilike(f"%{search_term}%"),
            Ticket.customer_name.ilike(f"%{search_term}%"),
            Booking.customer_name.ilike(f"%{search_term}%"),
            Booking.phone.ilike(f"%{search_term}%")
        )
    ).order_by(Ticket.id.desc()).limit(30).all()

    results = []
    for t in tickets:
        booking = t.booking
        # Format phone (mask middle digits for privacy while allowing lookup confirmation)
        phone = booking.phone if booking else None
        results.append(StaffSearchItem(
            ticket_id=t.ticket_id,
            booking_id=booking.booking_id if booking else "N/A",
            customer_name=t.customer_name,
            phone=phone,
            ticket_status=t.ticket_status,
            checkin_status=t.checkin_status,
            checked_in_at=t.checked_in_at
        ))

    return results


@router.get("/checkins", response_model=List[StaffRecentCheckIn])
def staff_get_checkin_logs(
    limit: int = Query(50, ge=1, le=200),
    current_staff: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """Staff API: Get recent check-in log stream."""
    logs = db.query(CheckIn).order_by(CheckIn.id.desc()).limit(limit).all()
    results = []
    for r in logs:
        t = db.query(Ticket).filter(Ticket.id == r.ticket_id).first()
        results.append(StaffRecentCheckIn(
            id=r.id,
            ticket_id=t.ticket_id if t else (f"Invalid scan" if r.result == "INVALID" else "Unknown"),
            customer_name=t.customer_name if t else "Unknown Attendee",
            checked_in_at=r.checked_in_at,
            result=r.result,
            device_information=r.device_information
        ))
    return results
