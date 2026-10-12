from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, Query
from sqlalchemy.orm import Session
from datetime import datetime
import re
import urllib.parse
import json
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

def find_ticket_by_any_identifier(raw_identifier: str, db: Session, for_update: bool = False, is_staff: bool = True) -> Optional[Ticket]:
    """Intelligently resolves a ticket from any user-provided identifier or scanned payload.
    - Public access (is_staff=False): ONLY high-entropy cryptographic QR tokens are accepted.
    - Staff access (is_staff=True): Allows Ticket ID, Booking ID, attendee phone, or email lookup at entry gates.
    """
    if not raw_identifier:
        return None
    token = str(raw_identifier).strip().strip("'\"")
    if not token:
        return None

    # 1. Handle JSON string payloads if emitted by smart optical scanners
    if token.startswith("{") and token.endswith("}"):
        try:
            parsed_json = json.loads(token)
            if isinstance(parsed_json, dict):
                token = str(
                    parsed_json.get("qr_token")
                    or parsed_json.get("ticket_id")
                    or parsed_json.get("token")
                    or parsed_json.get("id")
                    or token
                ).strip().strip("'\"")
        except Exception:
            pass

    # 2. Extract token from URL strings (supports http, https, custom schemes, query params, fragments)
    if "://" in token or token.startswith("www."):
        full_url = token if "://" in token else f"https://{token}"
        try:
            parsed_url = urllib.parse.urlparse(full_url)
            # Check query params first (e.g., ?token=... or ?qr_token=... or ?ticket_id=...)
            qs = urllib.parse.parse_qs(parsed_url.query)
            if "token" in qs and qs["token"]:
                token = qs["token"][0].strip()
            elif "qr_token" in qs and qs["qr_token"]:
                token = qs["qr_token"][0].strip()
            elif "ticket_id" in qs and qs["ticket_id"]:
                token = qs["ticket_id"][0].strip()
            else:
                path = parsed_url.path.rstrip("/")
                if "/tickets/view/" in path:
                    token = path.split("/tickets/view/")[-1].strip()
                elif "/ticket/" in path:
                    token = path.split("/ticket/")[-1].strip()
                elif "/tickets/" in path:
                    token = path.split("/tickets/")[-1].strip()
                elif "/success/" in path:
                    token = path.split("/success/")[-1].strip()
                else:
                    path_parts = [p for p in path.split("/") if p]
                    if path_parts:
                        token = path_parts[-1].strip()
        except Exception:
            pass

    # Handle remaining URL path markers if scheme was omitted
    if "/tickets/view/" in token:
        token = token.split("/tickets/view/")[-1]
    elif "/ticket/" in token:
        token = token.split("/ticket/")[-1]
    elif "/tickets/" in token:
        token = token.split("/tickets/")[-1]
    elif "/success/" in token:
        token = token.split("/success/")[-1]

    # Clean query params, fragments, trailing slashes, surrounding quotes
    token = token.split("?")[0].split("#")[0].rstrip("/").strip().strip("'\"")
    if not token:
        return None

    token_hash = hash_qr_token(token)

    query = db.query(Ticket)
    if for_update:
        query = query.with_for_update()

    # Priority 1: Exact match on high-entropy raw QR token or token hash
    ticket = query.filter(
        (Ticket.qr_token_raw == token) | (Ticket.qr_token_hash == token_hash)
    ).first()
    if ticket:
        return ticket

    # Priority 1b: Case-insensitive match on raw QR token (for barcode scanners altering case)
    ticket = query.filter(Ticket.qr_token_raw.ilike(token)).first()
    if ticket:
        return ticket

    # Public callers are strictly restricted to high-entropy tokens to prevent enumeration attacks
    if not is_staff:
        return None

    # Priority 2: Direct match on Ticket ID (staff only, e.g. GN26-TKT-000145-01)
    ticket = query.filter(Ticket.ticket_id.ilike(token)).first()
    if ticket:
        return ticket

    # Priority 3: Match on Booking ID (staff only, e.g. GN-2026-000145)
    booking = db.query(Booking).filter(Booking.booking_id.ilike(token)).first()
    if booking and booking.tickets:
        unclaimed = [t for t in booking.tickets if not t.checkin_status and t.ticket_status == "VALID"]
        target_id = unclaimed[0].id if unclaimed else booking.tickets[0].id
        return query.filter(Ticket.id == target_id).first()

    # Priority 4: Attendee 10-digit phone number match (staff only)
    clean_numeric = re.sub(r'[^0-9]', '', token)
    if len(clean_numeric) >= 10:
        booking = db.query(Booking).filter(Booking.phone.ilike(f"%{clean_numeric}%")).order_by(Booking.id.desc()).first()
        if booking and booking.tickets:
            unclaimed = [t for t in booking.tickets if not t.checkin_status and t.ticket_status == "VALID"]
            target_id = unclaimed[0].id if unclaimed else booking.tickets[0].id
            return query.filter(Ticket.id == target_id).first()

    # Priority 5: Attendee email match (staff only)
    if "@" in token and "." in token:
        booking = db.query(Booking).filter(Booking.email.ilike(token)).order_by(Booking.id.desc()).first()
        if booking and booking.tickets:
            unclaimed = [t for t in booking.tickets if not t.checkin_status and t.ticket_status == "VALID"]
            target_id = unclaimed[0].id if unclaimed else booking.tickets[0].id
            return query.filter(Ticket.id == target_id).first()

    # Priority 6: Ticket ID partial numeric match (e.g. attendee types '145-01' or '000145-01')
    # Guard: only if token doesn't begin with raw token prefix 'GN26_' to prevent random digit collisions
    if len(clean_numeric) >= 4 and not token.upper().startswith("GN26_"):
        ticket = query.filter(Ticket.ticket_id.ilike(f"%{clean_numeric}%")).first()
        if ticket:
            return ticket
        booking = db.query(Booking).filter(Booking.booking_id.ilike(f"%{clean_numeric}%")).first()
        if booking and booking.tickets:
            unclaimed = [t for t in booking.tickets if not t.checkin_status and t.ticket_status == "VALID"]
            target_id = unclaimed[0].id if unclaimed else booking.tickets[0].id
            return query.filter(Ticket.id == target_id).first()

    return None

@router.get("/api/tickets/view/{qr_token}", response_model=TicketResponse)
def view_ticket_by_token(qr_token: str, db: Session = Depends(get_db)):
    """Public digital ticket view for customer via secret high-entropy token only."""
    ticket = find_ticket_by_any_identifier(qr_token, db, is_staff=False)

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
def download_single_ticket_pdf(
    ticket_id: str,
    token: Optional[str] = Query(None),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Downloads single ticket PDF with access token or staff authorization check."""
    ticket = db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found.")

    # Validate access: either valid high-entropy token or authenticated staff/admin session
    is_authorized = False
    if token and (token.strip() == ticket.qr_token_raw or hash_qr_token(token.strip()) == ticket.qr_token_hash):
        is_authorized = True
    else:
        # Check bearer auth or cookies for staff/admin
        try:
            auth_header = request.headers.get("Authorization") if request else None
            cookie_token = request.cookies.get("admin_access_token") if request else None
            jwt_raw = auth_header.replace("Bearer ", "").strip() if (auth_header and auth_header.startswith("Bearer ")) else cookie_token
            if jwt_raw:
                from app.utils.security import decode_access_token
                payload = decode_access_token(jwt_raw)
                if payload and payload.get("role") in ["SUPER_ADMIN", "ADMIN", "CHECKIN_STAFF", "STAFF"]:
                    is_authorized = True
        except Exception:
            pass

    if not is_authorized:
        raise HTTPException(
            status_code=403,
            detail="Secure ticket access token required." if not token else "Invalid ticket access token."
        )

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

@router.get("/api/tickets/{ticket_id}/pass.jpg")
def download_single_ticket_pass_image(
    ticket_id: str,
    token: Optional[str] = Query(None),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Downloads or views the official NAVRANG 2026 festive pass image."""
    ticket = db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found.")

    is_authorized = False
    if token and (token.strip() == ticket.qr_token_raw or hash_qr_token(token.strip()) == ticket.qr_token_hash):
        is_authorized = True
    else:
        try:
            auth_header = request.headers.get("Authorization") if request else None
            cookie_token = request.cookies.get("admin_access_token") if request else None
            jwt_raw = auth_header.replace("Bearer ", "").strip() if (auth_header and auth_header.startswith("Bearer ")) else cookie_token
            if jwt_raw:
                from app.utils.security import decode_access_token
                payload = decode_access_token(jwt_raw)
                if payload and payload.get("role") in ["SUPER_ADMIN", "ADMIN", "CHECKIN_STAFF", "STAFF"]:
                    is_authorized = True
        except Exception:
            pass

    if not is_authorized:
        # Also allow viewing if accessed with valid session or direct verification
        if not token:
            raise HTTPException(status_code=403, detail="Secure ticket access token required.")

    booking = ticket.booking
    event_setting = db.query(EventSetting).first() or EventSetting()

    img_bytes = ticket_service.generate_ticket_image_bytes(booking, ticket, event_setting)
    return Response(
        content=img_bytes,
        media_type="image/jpeg",
        headers={
            "Content-Disposition": f'inline; filename="NAVRANG2026_Pass_{ticket.ticket_id}.jpg"'
        }
    )

@router.post("/api/qr/verify", response_model=VerifyQRResponse)
def verify_qr(
    payload: VerifyQRRequest,
    current_staff: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """Checks QR token or Ticket ID for authenticated gate staff and returns status (VALID, USED, CANCELLED, INVALID)."""
    raw_token = payload.qr_token.strip()
    event_setting = db.query(EventSetting).first() or EventSetting()

    # Search for ticket as staff
    ticket = find_ticket_by_any_identifier(raw_token, db, is_staff=True)

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
        from app.utils.timezone import utc_to_ist
        time_str = utc_to_ist(ticket.checked_in_at).strftime("%I:%M %p") if ticket.checked_in_at else "Earlier"
        return VerifyQRResponse(
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

    return VerifyQRResponse(
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
    ticket = find_ticket_by_any_identifier(raw_token, db, for_update=True, is_staff=True)

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

        from app.utils.timezone import utc_to_ist
        time_str = utc_to_ist(ticket.checked_in_at).strftime("%I:%M %p") if ticket.checked_in_at else "Earlier"
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
