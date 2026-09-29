from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.orm import Session
from datetime import datetime
import re
from app.database import get_db
from app.models.ticket import Ticket
from app.models.booking import Booking
from app.models.checkin import CheckIn
from app.models.audit_log import AuditLog
from app.models.event_setting import EventSetting
from app.models.user import User
from app.schemas.ticket import (
    VerifyQRRequest,
    VerifyQRResponse,
    CheckInRequest,
    CheckInResponse,
    TicketResponse
)
from app.services.qr_service import qr_service
from app.services.ticket_service import ticket_service
from app.utils.security import hash_qr_token
from app.middleware.auth import require_staff
from app.config import settings

from typing import Optional

router = APIRouter(prefix="", tags=["Tickets & QR Verification"])

def find_ticket_by_any_identifier(raw_identifier: str, db: Session, for_update: bool = False) -> Optional[Ticket]:
    """Intelligently resolves a ticket from any user-provided identifier or scanned payload:
    - Raw cryptographic token (e.g. GN26_...)
    - SHA-256 token hash
    - Full ticket URL (e.g. /ticket/GN26_... or /tickets/view/... or /success/...)
    - Ticket ID (e.g. GN26-TKT-070591-01 or 070591-01)
    - Booking Reference ID (e.g. GN-2026-70591 or 70591)
    - Customer mobile phone number or email address
    """
    if not raw_identifier:
        return None
    token = raw_identifier.strip()
    
    # 1. Clean URLs if full address was scanned
    if "/ticket/" in token:
        token = token.split("/ticket/")[1].split("?")[0].split("#")[0].strip()
    elif "/tickets/view/" in token:
        token = token.split("/tickets/view/")[1].split("?")[0].split("#")[0].strip()
    elif "/success/" in token:
        token = token.split("/success/")[1].split("?")[0].split("#")[0].strip()

    token_hash = hash_qr_token(token)

    query = db.query(Ticket)
    if for_update:
        query = query.with_for_update()

    # Priority 1: Match by raw QR token or token hash
    ticket = query.filter(
        (Ticket.qr_token_raw == token) | (Ticket.qr_token_hash == token_hash)
    ).first()
    if ticket:
        return ticket

    # Priority 2: Direct match on Ticket ID (exact or case-insensitive)
    ticket = query.filter(Ticket.ticket_id.ilike(token)).first()
    if ticket:
        return ticket

    # Priority 3: Match on Booking ID (e.g. GN-2026-70591)
    booking = db.query(Booking).filter(Booking.booking_id.ilike(token)).first()
    if booking and booking.tickets:
        unclaimed = [t for t in booking.tickets if not t.checkin_status and t.ticket_status == "VALID"]
        target_id = unclaimed[0].id if unclaimed else booking.tickets[0].id
        return query.filter(Ticket.id == target_id).first()

    # Priority 4: Partial numeric or stripped search (e.g. 070591-01 or 70591)
    clean_numeric = re.sub(r'[^0-9]', '', token)
    if len(clean_numeric) >= 4:
        ticket = query.filter(Ticket.ticket_id.ilike(f"%{clean_numeric}%")).first()
        if ticket:
            return ticket
        booking = db.query(Booking).filter(Booking.booking_id.ilike(f"%{clean_numeric}%")).first()
        if booking and booking.tickets:
            unclaimed = [t for t in booking.tickets if not t.checkin_status and t.ticket_status == "VALID"]
            target_id = unclaimed[0].id if unclaimed else booking.tickets[0].id
            return query.filter(Ticket.id == target_id).first()

    # Priority 5: Customer phone match
    if len(clean_numeric) >= 10:
        booking = db.query(Booking).filter(Booking.phone.ilike(f"%{clean_numeric}%")).order_by(Booking.id.desc()).first()
        if booking and booking.tickets:
            unclaimed = [t for t in booking.tickets if not t.checkin_status and t.ticket_status == "VALID"]
            target_id = unclaimed[0].id if unclaimed else booking.tickets[0].id
            return query.filter(Ticket.id == target_id).first()

    # Priority 6: Customer email match
    if "@" in token and "." in token:
        booking = db.query(Booking).filter(Booking.email.ilike(token)).order_by(Booking.id.desc()).first()
        if booking and booking.tickets:
            unclaimed = [t for t in booking.tickets if not t.checkin_status and t.ticket_status == "VALID"]
            target_id = unclaimed[0].id if unclaimed else booking.tickets[0].id
            return query.filter(Ticket.id == target_id).first()

    return None

@router.get("/api/tickets/view/{qr_token}", response_model=TicketResponse)
def view_ticket_by_token(qr_token: str, db: Session = Depends(get_db)):
    """Public digital ticket view for customer via secret token, Ticket ID, or Booking ID."""
    ticket = find_ticket_by_any_identifier(qr_token, db)

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found or link has expired.")

    booking = ticket.booking
    qr_base64 = qr_service.generate_qr_base64(ticket.qr_token_raw)

    return TicketResponse(
        ticket_id=ticket.ticket_id,
        booking_id=booking.booking_id if booking else "",
        customer_name=ticket.customer_name,
        event_name=ticket.event_name,
        ticket_status=ticket.ticket_status,
        checkin_status=ticket.checkin_status,
        checked_in_at=ticket.checked_in_at,
        created_at=ticket.created_at,
        qr_token_raw=ticket.qr_token_raw,
        qr_code_base64=qr_base64,
        ticket_url=f"{settings.FRONTEND_URL}/ticket/{ticket.qr_token_raw}"
    )

@router.get("/api/tickets/{ticket_id}/pdf")
def download_single_ticket_pdf(ticket_id: str, db: Session = Depends(get_db)):
    """Downloads single ticket PDF."""
    ticket = db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found.")

    booking = ticket.booking
    event_setting = db.query(EventSetting).first() or EventSetting()

    pdf_bytes = ticket_service.generate_single_ticket_pdf(booking, ticket, event_setting)
    event_slug = re.sub(r'[^a-zA-Z0-9]', '', event_setting.event_name) or "Ticket"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{event_slug}_{ticket.ticket_id}.pdf"'
        }
    )

@router.post("/api/qr/verify", response_model=VerifyQRResponse)
def verify_qr(payload: VerifyQRRequest, db: Session = Depends(get_db)):
    """Checks QR token, Ticket ID, Booking ID, or Attendee info and returns status (VALID, USED, CANCELLED, INVALID)."""
    raw_token = payload.qr_token.strip()
    event_setting = db.query(EventSetting).first() or EventSetting()

    # Search by any valid identifier
    ticket = find_ticket_by_any_identifier(raw_token, db)

    if not ticket:
        return VerifyQRResponse(
            valid=False,
            status="INVALID",
            message=f"❌ No ticket found matching '{raw_token}'. Please verify the Ticket ID or scan again."
        )

    booking = ticket.booking

    if ticket.ticket_status == "CANCELLED":
        return VerifyQRResponse(
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
        return VerifyQRResponse(
            valid=False,
            status="USED",
            message="⚠️ TICKET ALREADY USED",
            ticket_id=ticket.ticket_id,
            booking_id=booking.booking_id if booking else None,
            customer_name=ticket.customer_name,
            event_name=ticket.event_name,
            ticket_status="USED",
            checkin_status=True,
            checked_in_at=ticket.checked_in_at,
            qr_token_raw=ticket.qr_token_raw
        )

    return VerifyQRResponse(
        valid=True,
        status="VALID",
        message="✓ VALID TICKET",
        ticket_id=ticket.ticket_id,
        booking_id=booking.booking_id if booking else None,
        customer_name=ticket.customer_name,
        event_name=ticket.event_name,
        ticket_status="VALID",
        checkin_status=False,
        qr_token_raw=ticket.qr_token_raw
    )

@router.post("/api/qr/checkin", response_model=CheckInResponse)
def checkin_ticket(
    payload: CheckInRequest,
    request: Request,
    current_staff: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """Atomically checks in a ticket. Uses database row-locking to strictly eliminate race conditions."""
    raw_token = payload.qr_token.strip()
    client_ip = request.client.host if request.client else "unknown"

    # Acquire exclusive row lock on the ticket by any identifier
    ticket = find_ticket_by_any_identifier(raw_token, db, for_update=True)

    if not ticket:
        # Record failed attempt
        checkin_log = CheckIn(
            ticket_id=0, # invalid placeholder
            staff_id=current_staff.id,
            device_information=payload.device_information,
            ip_address=client_ip,
            result="INVALID",
            notes=f"Attempted scan of unknown token: {raw_token}"
        )
        db.add(checkin_log)
        db.commit()
        event_setting = db.query(EventSetting).first() or EventSetting()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"❌ No ticket found matching '{raw_token}'."
        )

    booking = ticket.booking

    # Check if CANCELLED
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

    # Check if ALREADY USED (Duplicate Check-in Protection)
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
            detail=f"⚠️ TICKET ALREADY USED! Checked in at {time_str}. Duplicate entry rejected."
        )

    # Valid checkin: Mark ticket as USED atomically
    now = datetime.utcnow()
    ticket.checkin_status = True
    ticket.checked_in_at = now
    ticket.ticket_status = "USED"

    # Record check-in
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

    # Audit log
    audit = AuditLog(
        user_id=current_staff.id,
        action="CHECKIN_SUCCESS",
        entity_type="ticket",
        entity_id=ticket.ticket_id,
        ip_address=client_ip,
        details=f'{{"customer": "{ticket.customer_name}", "booking": "{booking.booking_id if booking else ""}"}}'
    )
    db.add(audit)

    db.commit()
    db.refresh(ticket)

    return CheckInResponse(
        success=True,
        status="SUCCESS",
        message="✓ Check-in recorded successfully! Welcome to NAVRANG 2026!",
        ticket_id=ticket.ticket_id,
        booking_id=booking.booking_id if booking else None,
        customer_name=ticket.customer_name,
        checked_in_at=ticket.checked_in_at,
        staff_name=current_staff.name
    )
