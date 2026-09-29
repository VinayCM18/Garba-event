from typing import Optional, List, Dict, Any
import csv
import io
import os
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_
from datetime import datetime, timedelta
from app.database import get_db
from app.models.user import User
from app.models.booking import Booking
from app.models.ticket import Ticket
from app.models.payment import Payment
from app.models.checkin import CheckIn
from app.models.audit_log import AuditLog
from app.models.event_setting import EventSetting
from app.schemas.admin import (
    DashboardAnalyticsResponse,
    DashboardStatsResponse,
    DailyStatItem,
    HourlyCheckInItem,
    EventSettingResponse,
    EventSettingUpdateRequest,
    PaymentVerificationItem,
    PaymentRejectRequest,
    CheckInLogItem,
    AuditLogItem,
    TestEmailRequest,
    RecentNotificationItem
)
from app.schemas.booking import BookingListResponse, BookingDetailResponse
from app.schemas.ticket import TicketResponse
from app.services.email_service import email_service
from app.services.qr_service import qr_service
from app.middleware.auth import require_admin, require_super_admin, require_staff
from app.config import settings

router = APIRouter(prefix="/api/admin", tags=["Admin Operations"])

@router.get("/dashboard", response_model=DashboardStatsResponse)
def get_dashboard_stats(current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Fetch real-time KPI metrics for admin overview."""
    event_setting = db.query(EventSetting).first() or EventSetting()

    # Confirmed bookings & tickets
    confirmed_query = db.query(Booking).filter(
        Booking.booking_status == "CONFIRMED",
        Booking.payment_status == "PAID"
    )

    tickets_sold = confirmed_query.with_entities(func.coalesce(func.sum(Booking.ticket_count), 0)).scalar() or 0
    revenue = confirmed_query.with_entities(func.coalesce(func.sum(Booking.amount), 0.0)).scalar() or 0.0
    total_bookings = confirmed_query.count()

    # Checked In tickets
    checked_in = db.query(Ticket).filter(Ticket.checkin_status == True).count()

    remaining_tickets = max(0, event_setting.total_capacity - tickets_sold)
    checkin_rate = round((checked_in / tickets_sold * 100), 1) if tickets_sold > 0 else 0.0

    return DashboardStatsResponse(
        tickets_sold=tickets_sold,
        revenue=revenue,
        total_bookings=total_bookings,
        checked_in=checked_in,
        remaining_tickets=remaining_tickets,
        total_capacity=event_setting.total_capacity,
        checkin_rate_percentage=checkin_rate
    )

@router.get("/analytics", response_model=DashboardAnalyticsResponse)
def get_analytics(current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Fetch time-series charts data for revenue, sales, and check-ins."""
    event_setting = db.query(EventSetting).first() or EventSetting()

    # Confirmed KPIs
    confirmed_query = db.query(Booking).filter(
        Booking.booking_status == "CONFIRMED",
        Booking.payment_status == "PAID"
    )
    tickets_sold = confirmed_query.with_entities(func.coalesce(func.sum(Booking.ticket_count), 0)).scalar() or 0
    revenue = confirmed_query.with_entities(func.coalesce(func.sum(Booking.amount), 0.0)).scalar() or 0.0
    total_bookings = confirmed_query.count()
    checked_in = db.query(Ticket).filter(Ticket.checkin_status == True).count()
    remaining = max(0, event_setting.total_capacity - tickets_sold)
    checkin_rate = round((checked_in / tickets_sold * 100), 1) if tickets_sold > 0 else 0.0

    # Sales trend for the last 7 days
    sales_trend: list[DailyStatItem] = []
    now = datetime.utcnow()
    for i in range(6, -1, -1):
        day_date = (now - timedelta(days=i)).date()
        day_start = datetime.combine(day_date, datetime.min.time())
        day_end = datetime.combine(day_date, datetime.max.time())

        day_bookings = db.query(Booking).filter(
            Booking.booking_status == "CONFIRMED",
            Booking.payment_status == "PAID",
            Booking.created_at >= day_start,
            Booking.created_at <= day_end
        )
        day_rev = day_bookings.with_entities(func.coalesce(func.sum(Booking.amount), 0.0)).scalar() or 0.0
        day_tkts = day_bookings.with_entities(func.coalesce(func.sum(Booking.ticket_count), 0)).scalar() or 0
        day_count = day_bookings.count()

        sales_trend.append(DailyStatItem(
            date=day_date.strftime("%b %d"),
            revenue=day_rev,
            tickets=day_tkts,
            bookings=day_count
        ))

    # Hourly checkin trend for event night (18:00 to 02:00)
    checkin_trend: list[HourlyCheckInItem] = []
    hours = ["06 PM", "07 PM", "08 PM", "09 PM", "10 PM", "11 PM", "12 AM", "01 AM", "02 AM"]
    for hour_label in hours:
        # Count checkins for that bucket
        checkin_trend.append(HourlyCheckInItem(
            hour=hour_label,
            count=0 # Will populate dynamically from checkins
        ))

    # Populate real check-in counts from db
    checkin_records = db.query(CheckIn).filter(CheckIn.result == "SUCCESS").all()
    for ci in checkin_records:
        h = ci.checked_in_at.strftime("%I %p")
        for item in checkin_trend:
            if item.hour == h:
                item.count += 1
                break

    stats = DashboardStatsResponse(
        tickets_sold=tickets_sold,
        revenue=revenue,
        total_bookings=total_bookings,
        checked_in=checked_in,
        remaining_tickets=remaining,
        total_capacity=event_setting.total_capacity,
        checkin_rate_percentage=checkin_rate
    )

    return DashboardAnalyticsResponse(
        stats=stats,
        sales_trend=sales_trend,
        checkin_trend=checkin_trend
    )

@router.get("/bookings", response_model=BookingListResponse)
def list_bookings(
    page: int = Query(1, ge=1),
    per_page: int = Query(15, ge=1, le=100),
    search: str = Query("", max_length=100),
    payment_status: str = Query("", max_length=50),
    booking_status: str = Query("", max_length=50),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """List bookings with search, status filtering, and pagination."""
    query = db.query(Booking)

    if search.strip():
        term = f"%{search.strip()}%"
        # Also check tickets matching ticket_id
        matching_booking_ids = db.query(Ticket.booking_id).filter(Ticket.ticket_id.ilike(term)).subquery()
        query = query.filter(
            or_(
                Booking.booking_id.ilike(term),
                Booking.customer_name.ilike(term),
                Booking.email.ilike(term),
                Booking.phone.ilike(term),
                Booking.id.in_(matching_booking_ids)
            )
        )

    if payment_status.strip():
        query = query.filter(Booking.payment_status == payment_status.strip().upper())

    if booking_status.strip():
        query = query.filter(Booking.booking_status == booking_status.strip().upper())

    total = query.count()
    total_pages = max(1, (total + per_page - 1) // per_page)
    offset = (page - 1) * per_page

    bookings = query.order_by(desc(Booking.created_at)).offset(offset).limit(per_page).all()

    items = []
    for b in bookings:
        tickets_list = []
        for t in b.tickets:
            tickets_list.append(TicketResponse(
                ticket_id=t.ticket_id,
                booking_id=b.booking_id,
                customer_name=t.customer_name,
                event_name=t.event_name,
                ticket_status=t.ticket_status,
                checkin_status=t.checkin_status,
                checked_in_at=t.checked_in_at,
                created_at=t.created_at,
                qr_token_raw=t.qr_token_raw,
                ticket_url=f"{settings.FRONTEND_URL}/ticket/{t.qr_token_raw}"
            ))

        reg_amt = getattr(b, "regular_amount", 0.0) or round(b.ticket_count * b.ticket_price, 2)
        grp_disc = getattr(b, "group_discount", 0.0) or 0.0
        is_grp = grp_disc > 0 or (b.ticket_count == 10 and grp_disc > 0)

        items.append(BookingDetailResponse(
            id=b.id,
            booking_id=b.booking_id,
            customer_name=b.customer_name,
            email=b.email,
            phone=b.phone,
            ticket_count=b.ticket_count,
            ticket_price=b.ticket_price,
            regular_amount=reg_amt,
            group_discount=grp_disc,
            ticket_subtotal=b.ticket_subtotal or (reg_amt - grp_disc),
            convenience_fee=b.convenience_fee or 0.0,
            payment_fee=b.payment_fee or 0.0,
            gst_amount=b.gst_amount or 0.0,
            amount=b.amount,
            currency=b.currency,
            is_group_offer=is_grp,
            offer_name="BUY 10, PAY FOR 9" if is_grp else None,
            payment_method=b.payment_method or "UPI_MANUAL",
            utr_number=b.utr_number,
            payment_screenshot=b.payment_screenshot,
            verified_by=b.verified_by,
            verified_at=b.verified_at,
            rejection_reason=b.rejection_reason,
            razorpay_order_id=b.razorpay_order_id,
            razorpay_payment_id=b.razorpay_payment_id,
            payment_status=b.payment_status,
            booking_status=b.booking_status,
            email_status=b.email_status,
            email_sent_at=b.email_sent_at,
            email_error=b.email_error,
            owner_notified=b.owner_notified,
            owner_notified_at=b.owner_notified_at,
            owner_notify_error=b.owner_notify_error,
            created_at=b.created_at,
            tickets=tickets_list
        ))

    return BookingListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages
    )

@router.get("/bookings/{booking_id}", response_model=BookingDetailResponse)
def get_booking_details(
    booking_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Retrieve full details of a specific booking."""
    booking = db.query(Booking).filter(
        or_(Booking.booking_id == booking_id, Booking.id == int(booking_id) if booking_id.isdigit() else False)
    ).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found.")

    tickets_list = []
    for t in booking.tickets:
        tickets_list.append(TicketResponse(
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
        email_error=booking.email_error,
        owner_notified=booking.owner_notified,
        owner_notified_at=booking.owner_notified_at,
        owner_notify_error=booking.owner_notify_error,
        created_at=booking.created_at,
        tickets=tickets_list
    )

@router.post("/bookings/{booking_id}/resend-email")
def resend_email(
    booking_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Admin triggered resend of confirmation email to customer."""
    booking = db.query(Booking).filter(Booking.booking_id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found.")

    success = email_service.send_confirmation_email(booking_id, db)
    db.refresh(booking)
    if not success:
        return {
            "success": False,
            "message": booking.email_error or "Customer email delivery failed. Please configure SMTP in Admin Settings."
        }
    return {"success": True, "message": f"Confirmation email successfully sent to {booking.email}."}

@router.post("/bookings/{booking_id}/resend-owner-alert")
def resend_owner_alert(
    booking_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Admin triggered resend of booking alert to owner."""
    booking = db.query(Booking).filter(Booking.booking_id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found.")

    success = email_service.send_owner_notification(booking_id, db)
    db.refresh(booking)
    if not success:
        return {
            "success": False,
            "message": booking.owner_notify_error or "Owner alert delivery failed. Please configure SMTP in Admin Settings."
        }
    return {"success": True, "message": "Owner alert notification dispatched successfully."}

@router.post("/bookings/{booking_id}/cancel")
def cancel_booking(
    booking_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Cancels a booking and invalidates all associated tickets."""
    booking = db.query(Booking).filter(Booking.booking_id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found.")

    booking.booking_status = "CANCELLED"
    booking.payment_status = "CANCELLED"
    for t in booking.tickets:
        t.ticket_status = "CANCELLED"

    audit = AuditLog(
        user_id=current_user.id,
        action="BOOKING_CANCELLED",
        entity_type="booking",
        entity_id=booking.booking_id,
        details=f'{{"cancelled_by": "{current_user.name}"}}'
    )
    db.add(audit)
    db.commit()
    return {"success": True, "message": f"Booking {booking_id} cancelled successfully."}

@router.get("/checkins", response_model=list[CheckInLogItem])
def list_checkins(
    limit: int = Query(50, le=200),
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """List recent checkin scans and validation attempts."""
    records = db.query(CheckIn).order_by(desc(CheckIn.checked_in_at)).limit(limit).all()
    output = []
    for r in records:
        ticket = r.ticket
        booking = ticket.booking if ticket else None
        staff = r.staff
        output.append(CheckInLogItem(
            id=r.id,
            ticket_id=ticket.ticket_id if ticket else "UNKNOWN",
            booking_id=booking.booking_id if booking else "N/A",
            customer_name=ticket.customer_name if ticket else "N/A",
            staff_name=staff.name if staff else "System",
            result=r.result,
            checked_in_at=r.checked_in_at,
            ip_address=r.ip_address,
            device_information=r.device_information
        ))
    return output

@router.get("/audit-logs", response_model=list[AuditLogItem])
def list_audit_logs(
    limit: int = Query(50, le=200),
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """List system and security audit logs."""
    logs = db.query(AuditLog).order_by(desc(AuditLog.timestamp)).limit(limit).all()
    output = []
    for l in logs:
        user = l.user
        output.append(AuditLogItem(
            id=l.id,
            user_email=user.email if user else "System/Public",
            action=l.action,
            entity_type=l.entity_type,
            entity_id=l.entity_id,
            ip_address=l.ip_address,
            user_agent=l.user_agent,
            details=l.details,
            timestamp=l.timestamp or datetime.utcnow()
        ))
    return output

@router.get("/export")
def export_bookings_csv(
    payment_status: str = Query("", max_length=50),
    booking_status: str = Query("", max_length=50),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Exports filtered bookings as a CSV spreadsheet."""
    query = db.query(Booking)
    if payment_status.strip():
        query = query.filter(Booking.payment_status == payment_status.strip().upper())
    if booking_status.strip():
        query = query.filter(Booking.booking_status == booking_status.strip().upper())

    bookings = query.order_by(desc(Booking.created_at)).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Booking ID", "Customer Name", "Email", "Phone",
        "Ticket Count", "Ticket Price (INR)", "Regular Amount (INR)", "Group Discount (INR)", "Offer Name",
        "Subtotal (INR)", "Payment Fee (INR)", "GST (INR)", "Total Paid (INR)",
        "Payment Status", "Booking Status", "Razorpay Payment ID",
        "Email Status", "Created At"
    ])

    for b in bookings:
        reg = getattr(b, "regular_amount", 0.0) or round(b.ticket_count * b.ticket_price, 2)
        disc = getattr(b, "group_discount", 0.0) or 0.0
        offer = "BUY 10, PAY FOR 9" if disc > 0 else "None"
        subtotal = b.ticket_subtotal or (reg - disc)
        fee = b.payment_fee or 0.0
        gst = b.gst_amount or 0.0
        writer.writerow([
            b.booking_id,
            b.customer_name,
            b.email,
            b.phone,
            b.ticket_count,
            b.ticket_price,
            reg,
            disc,
            offer,
            subtotal,
            fee,
            gst,
            b.amount,
            b.payment_status,
            b.booking_status,
            b.razorpay_payment_id or "N/A",
            b.email_status,
            b.created_at.strftime("%Y-%m-%d %H:%M:%S")
        ])

    csv_data = output.getvalue()
    filename = f"garba_night_bookings_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@router.get("/settings", response_model=EventSettingResponse)
def get_settings(current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Fetch event settings including owner notification, SMTP dispatch, and Razorpay configuration."""
    event_setting = db.query(EventSetting).first()
    if not event_setting:
        event_setting = EventSetting()
        db.add(event_setting)
        db.commit()
        db.refresh(event_setting)

    smtp_pwd_present = bool((event_setting.smtp_password or "").strip() or settings.SMTP_PASSWORD)
    rzp_secret_present = bool((event_setting.razorpay_key_secret or "").strip() or (settings.RAZORPAY_KEY_SECRET and "placeholder" not in settings.RAZORPAY_KEY_SECRET))
    rzp_webhook_present = bool((event_setting.razorpay_webhook_secret or "").strip() or (settings.RAZORPAY_WEBHOOK_SECRET and "placeholder" not in settings.RAZORPAY_WEBHOOK_SECRET))

    return EventSettingResponse(
        event_name=event_setting.event_name,
        event_tagline=event_setting.event_tagline,
        event_date=event_setting.event_date,
        event_time=event_setting.event_time,
        venue_name=event_setting.venue_name,
        venue_address=event_setting.venue_address,
        venue_city=event_setting.venue_city,
        ticket_price=event_setting.ticket_price,
        convenience_fee=event_setting.convenience_fee,
        total_capacity=event_setting.total_capacity,
        max_per_booking=event_setting.max_per_booking,
        booking_open=event_setting.booking_open,
        contact_email=event_setting.contact_email,
        contact_phone=event_setting.contact_phone,
        rules_text=event_setting.rules_text,
        group_offer_enabled=getattr(event_setting, "group_offer_enabled", True),
        group_offer_size=getattr(event_setting, "group_offer_size", 10),
        group_offer_free_tickets=getattr(event_setting, "group_offer_free_tickets", 1),
        group_offer_discount=round(float(event_setting.ticket_price) * getattr(event_setting, "group_offer_free_tickets", 1), 2),
        owner_notification_email=getattr(event_setting, "owner_notification_email", None) or settings.OWNER_NOTIFICATION_EMAIL or "vinay18744@gmail.com",
        owner_notification_phone=getattr(event_setting, "owner_notification_phone", None) or settings.OWNER_NOTIFICATION_PHONE or "+91 98765 43210",
        owner_notification_enabled=getattr(event_setting, "owner_notification_enabled", True),
        owner_webhook_url=getattr(event_setting, "owner_webhook_url", None) or settings.OWNER_WEBHOOK_URL,
        smtp_host=getattr(event_setting, "smtp_host", None) or settings.SMTP_HOST or "smtp.gmail.com",
        smtp_port=getattr(event_setting, "smtp_port", None) or settings.SMTP_PORT or 587,
        smtp_username=getattr(event_setting, "smtp_username", None) or settings.SMTP_USERNAME or "",
        smtp_password_set=smtp_pwd_present,
        smtp_from_email=getattr(event_setting, "smtp_from_email", None) or settings.FROM_EMAIL or "tickets@garbanight.in",
        smtp_from_name=getattr(event_setting, "smtp_from_name", None) or settings.FROM_NAME or "NAVRANG 2026",
        smtp_use_tls=getattr(event_setting, "smtp_use_tls", True),
        # Payment Provider & Manual UPI Settings
        payment_method=getattr(event_setting, "payment_method", None) or settings.PAYMENT_METHOD or "UPI_MANUAL",
        upi_id=getattr(event_setting, "upi_id", None) or settings.UPI_ID or "samaymadhyastha2005@oksbi",
        upi_qr_image=getattr(event_setting, "upi_qr_image", None) or settings.UPI_QR_IMAGE or "uploads/qr/upi_qr.jpg",
        upi_payment_instructions=getattr(event_setting, "upi_payment_instructions", None) or settings.UPI_PAYMENT_INSTRUCTIONS,
        razorpay_key_id=getattr(event_setting, "razorpay_key_id", None) or (settings.RAZORPAY_KEY_ID if "placeholder" not in settings.RAZORPAY_KEY_ID else ""),
        razorpay_key_secret_set=rzp_secret_present,
        razorpay_webhook_secret_set=rzp_webhook_present
    )

@router.put("/settings", response_model=EventSettingResponse)
def update_settings(
    payload: EventSettingUpdateRequest,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """Update event configuration, owner alert rules, and credentials (SUPER_ADMIN only)."""
    event_setting = db.query(EventSetting).first()
    if not event_setting:
        event_setting = EventSetting()
        db.add(event_setting)

    update_data = payload.dict(exclude_unset=True)
    audit_data = {}
    for key, value in update_data.items():
        if value is not None:
            # If passwords/secrets are empty string, don't overwrite existing
            if key in ["smtp_password", "razorpay_key_secret", "razorpay_webhook_secret"]:
                if str(value).strip():
                    setattr(event_setting, key, str(value).strip())
                    audit_data[key] = "********"
            else:
                setattr(event_setting, key, value)
                audit_data[key] = value

    audit = AuditLog(
        user_id=current_user.id,
        action="SETTINGS_UPDATED",
        entity_type="event_setting",
        entity_id=str(event_setting.id),
        details=str(audit_data)
    )
    db.add(audit)
    db.commit()
    db.refresh(event_setting)

    smtp_pwd_present = bool((event_setting.smtp_password or "").strip() or settings.SMTP_PASSWORD)
    rzp_secret_present = bool((event_setting.razorpay_key_secret or "").strip() or (settings.RAZORPAY_KEY_SECRET and "placeholder" not in settings.RAZORPAY_KEY_SECRET))
    rzp_webhook_present = bool((event_setting.razorpay_webhook_secret or "").strip() or (settings.RAZORPAY_WEBHOOK_SECRET and "placeholder" not in settings.RAZORPAY_WEBHOOK_SECRET))

    return EventSettingResponse(
        event_name=event_setting.event_name,
        event_tagline=event_setting.event_tagline,
        event_date=event_setting.event_date,
        event_time=event_setting.event_time,
        venue_name=event_setting.venue_name,
        venue_address=event_setting.venue_address,
        venue_city=event_setting.venue_city,
        ticket_price=event_setting.ticket_price,
        convenience_fee=event_setting.convenience_fee,
        total_capacity=event_setting.total_capacity,
        max_per_booking=event_setting.max_per_booking,
        booking_open=event_setting.booking_open,
        contact_email=event_setting.contact_email,
        contact_phone=event_setting.contact_phone,
        rules_text=event_setting.rules_text,
        group_offer_enabled=getattr(event_setting, "group_offer_enabled", True),
        group_offer_size=getattr(event_setting, "group_offer_size", 10),
        group_offer_free_tickets=getattr(event_setting, "group_offer_free_tickets", 1),
        group_offer_discount=round(float(event_setting.ticket_price) * getattr(event_setting, "group_offer_free_tickets", 1), 2),
        owner_notification_email=getattr(event_setting, "owner_notification_email", None) or settings.OWNER_NOTIFICATION_EMAIL or "vinay18744@gmail.com",
        owner_notification_phone=getattr(event_setting, "owner_notification_phone", None) or settings.OWNER_NOTIFICATION_PHONE or "+91 98765 43210",
        owner_notification_enabled=getattr(event_setting, "owner_notification_enabled", True),
        owner_webhook_url=getattr(event_setting, "owner_webhook_url", None) or settings.OWNER_WEBHOOK_URL,
        smtp_host=getattr(event_setting, "smtp_host", None) or settings.SMTP_HOST or "smtp.gmail.com",
        smtp_port=getattr(event_setting, "smtp_port", None) or settings.SMTP_PORT or 587,
        smtp_username=getattr(event_setting, "smtp_username", None) or settings.SMTP_USERNAME or "",
        smtp_password_set=smtp_pwd_present,
        smtp_from_email=getattr(event_setting, "smtp_from_email", None) or settings.FROM_EMAIL or "tickets@garbanight.in",
        smtp_from_name=getattr(event_setting, "smtp_from_name", None) or settings.FROM_NAME or "NAVRANG 2026",
        smtp_use_tls=getattr(event_setting, "smtp_use_tls", True),
        # Payment Provider & Manual UPI Settings
        payment_method=getattr(event_setting, "payment_method", None) or settings.PAYMENT_METHOD or "UPI_MANUAL",
        upi_id=getattr(event_setting, "upi_id", None) or settings.UPI_ID or "samaymadhyastha2005@oksbi",
        upi_qr_image=getattr(event_setting, "upi_qr_image", None) or settings.UPI_QR_IMAGE or "uploads/qr/upi_qr.jpg",
        upi_payment_instructions=getattr(event_setting, "upi_payment_instructions", None) or settings.UPI_PAYMENT_INSTRUCTIONS,
        razorpay_key_id=getattr(event_setting, "razorpay_key_id", None) or (settings.RAZORPAY_KEY_ID if "placeholder" not in settings.RAZORPAY_KEY_ID else ""),
        razorpay_key_secret_set=rzp_secret_present,
        razorpay_webhook_secret_set=rzp_webhook_present
    )

@router.post("/test-email")
def test_email(
    payload: TestEmailRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Test SMTP connection and dispatch verification test email."""
    result = email_service.test_smtp_connection(payload.to_email, db)
    return result

@router.get("/notifications/recent", response_model=list[RecentNotificationItem])
def get_recent_notifications(
    limit: int = Query(10, le=50),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Fetch recent booking alerts for the admin dashboard."""
    bookings = db.query(Booking).filter(
        Booking.payment_status == "PAID",
        Booking.booking_status == "CONFIRMED"
    ).order_by(desc(Booking.created_at)).limit(limit).all()

    return [
        RecentNotificationItem(
            id=b.id,
            booking_id=b.booking_id,
            customer_name=b.customer_name,
            email=b.email,
            phone=b.phone,
            ticket_count=b.ticket_count,
            amount=b.amount,
            payment_status=b.payment_status,
            booking_status=b.booking_status,
            email_status=b.email_status,
            owner_notified=b.owner_notified,
            created_at=b.created_at
        )
        for b in bookings
    ]

@router.get("/payments/verification", response_model=list[PaymentVerificationItem])
def list_payment_verifications(
    status: str = Query("ALL", max_length=50),
    limit: int = Query(50, le=200),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Lists payments for administrative verification.
    Displays Booking ID, Customer, Phone, Email, Tickets, Amount, UTR, Screenshot status.
    """
    query = db.query(Booking)
    if status.upper() in ["PENDING", "VERIFICATION_PENDING"]:
        query = query.filter(
            or_(
                Booking.booking_status == "PAYMENT_VERIFICATION_PENDING",
                Booking.payment_status == "VERIFICATION_PENDING"
            )
        )
    elif status.upper() in ["PAID", "CONFIRMED"]:
        query = query.filter(Booking.payment_status == "PAID")
    elif status.upper() == "REJECTED":
        query = query.filter(Booking.payment_status == "REJECTED")
    else:
        # Default ALL: show manual UPI bookings, with VERIFICATION_PENDING first
        query = query.filter(
            or_(
                Booking.payment_method == "UPI_MANUAL",
                Booking.utr_number.isnot(None),
                Booking.payment_status == "VERIFICATION_PENDING"
            )
        )

    # Sort so VERIFICATION_PENDING is on top, then most recent
    bookings = query.order_by(
        desc(Booking.payment_status == "VERIFICATION_PENDING"),
        desc(Booking.updated_at)
    ).limit(limit).all()

    items = []
    for b in bookings:
        items.append(PaymentVerificationItem(
            id=b.id,
            booking_id=b.booking_id,
            customer_name=b.customer_name,
            phone=b.phone,
            email=b.email,
            ticket_count=b.ticket_count,
            amount=b.amount,
            currency=b.currency,
            payment_method=b.payment_method or "UPI_MANUAL",
            utr_number=b.utr_number,
            has_screenshot=bool(b.payment_screenshot),
            screenshot_url=f"/api/admin/payments/{b.booking_id}/screenshot" if b.payment_screenshot else None,
            payment_status=b.payment_status,
            booking_status=b.booking_status,
            submitted_at=b.updated_at,
            verified_by=b.verified_by,
            verified_at=b.verified_at,
            rejection_reason=b.rejection_reason,
            created_at=b.created_at
        ))
    return items

@router.get("/payments/{booking_id}/screenshot")
def get_payment_screenshot(
    booking_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Secure authenticated access to customer payment screenshot.
    Only authenticated administrators can view screenshots.
    Guarantees no directory traversal or guessing.
    """
    booking = db.query(Booking).filter(
        or_(Booking.booking_id == booking_id, Booking.id == int(booking_id) if booking_id.isdigit() else False)
    ).first()
    
    screenshot_filename = None
    if booking and booking.payment_screenshot:
        screenshot_filename = booking.payment_screenshot
    else:
        payment = db.query(Payment).filter(
            or_(Payment.booking_id == (booking.id if booking else -1), Payment.payment_id == booking_id)
        ).first()
        if payment and payment.payment_screenshot:
            screenshot_filename = payment.payment_screenshot

    if not screenshot_filename:
        raise HTTPException(status_code=404, detail="Payment screenshot not found.")

    base_name = os.path.basename(screenshot_filename)
    screenshots_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "uploads", "screenshots"))
    file_path = os.path.abspath(os.path.join(screenshots_dir, base_name))

    if not file_path.startswith(screenshots_dir) or not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Screenshot file does not exist on disk.")

    media_type = "image/jpeg"
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".png":
        media_type = "image/png"
    elif ext == ".webp":
        media_type = "image/webp"

    return FileResponse(
        file_path,
        media_type=media_type,
        headers={
            "Cache-Control": "private, no-store, must-revalidate",
            "Content-Disposition": f'inline; filename="{base_name}"'
        }
    )

@router.post("/payments/{booking_id}/approve")
def approve_payment(
    booking_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Admin verifies and approves manual UPI payment.
    Marks payment as PAID, booking as CONFIRMED, generates valid QR tickets, and sends email.
    """
    from app.services.payment_service import payment_service
    confirmed_booking = payment_service.approve_manual_payment(
        booking_id=booking_id,
        admin_user=current_user,
        db=db
    )
    return {
        "success": True,
        "message": f"Payment for booking {booking_id} verified and approved successfully! Tickets issued and email sent.",
        "booking_id": confirmed_booking.booking_id,
        "payment_status": confirmed_booking.payment_status,
        "booking_status": confirmed_booking.booking_status,
        "verified_by": confirmed_booking.verified_by,
        "verified_at": confirmed_booking.verified_at
    }

@router.post("/payments/{booking_id}/reject")
def reject_payment(
    booking_id: str,
    payload: PaymentRejectRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Admin rejects manual UPI payment.
    Marks payment as REJECTED and booking as PAYMENT_FAILED with reason.
    Does NOT issue tickets or send confirmation email.
    """
    from app.services.payment_service import payment_service
    rejected_booking = payment_service.reject_manual_payment(
        booking_id=booking_id,
        reason=payload.reason,
        admin_user=current_user,
        db=db
    )
    return {
        "success": True,
        "message": f"Payment for booking {booking_id} has been marked as REJECTED.",
        "booking_id": rejected_booking.booking_id,
        "payment_status": rejected_booking.payment_status,
        "booking_status": rejected_booking.booking_status,
        "rejection_reason": rejected_booking.rejection_reason
    }

@router.post("/settings/upload-qr")
async def upload_upi_qr_image(
    file: UploadFile = File(...),
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """Admin upload of official UPI QR code image."""
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
        raise HTTPException(status_code=400, detail="Invalid QR image format. Use JPG, PNG, or WebP.")

    file_bytes = await file.read()
    if len(file_bytes) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image exceeds 5MB limit.")

    try:
        from PIL import Image
        img = Image.open(io.BytesIO(file_bytes))
        img.verify()
    except Exception:
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid image.")

    qr_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "uploads", "qr"))
    os.makedirs(qr_dir, exist_ok=True)
    target_path = os.path.join(qr_dir, "upi_qr.jpg")
    with open(target_path, "wb") as f:
        f.write(file_bytes)

    # Also sync to frontend public for fallback convenience
    public_qr = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "frontend", "public", "upi_qr_code.jpg"))
    try:
        with open(public_qr, "wb") as f:
            f.write(file_bytes)
    except Exception:
        pass

    setting = db.query(EventSetting).first()
    if not setting:
        setting = EventSetting()
        db.add(setting)
    setting.upi_qr_image = "uploads/qr/upi_qr.jpg"
    db.commit()

    return {"success": True, "message": "UPI QR image uploaded successfully!", "url": "/api/payments/qr-image"}

from app.models.ticket_phase import TicketPhase
from pydantic import BaseModel

class TicketPhaseUpdateRequest(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    status: Optional[str] = None # ACTIVE, LOCKED, SOLD_OUT
    total_inventory: Optional[int] = None
    badge_text: Optional[str] = None
    description: Optional[str] = None
    group_offer_eligible: Optional[bool] = None

@router.get("/ticket-phases")
def get_admin_ticket_phases(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Lists all configured ticket phases with live sold and remaining counts."""
    phases = db.query(TicketPhase).order_by(TicketPhase.display_order.asc()).all()
    result = []
    for p in phases:
        sold = db.query(func.coalesce(func.sum(Booking.ticket_count), 0)).filter(
            Booking.booking_status == "CONFIRMED",
            Booking.payment_status == "PAID",
            Booking.ticket_phase == p.phase_code
        ).scalar() or 0
        result.append({
            "id": p.id,
            "phase_code": p.phase_code,
            "name": p.name,
            "price": float(p.price),
            "status": p.status,
            "total_inventory": p.total_inventory,
            "sold_count": sold,
            "remaining_tickets": max(0, p.total_inventory - sold),
            "display_order": p.display_order,
            "badge_text": p.badge_text,
            "description": p.description,
            "group_offer_eligible": p.group_offer_eligible,
            "tax_included": p.tax_included
        })
    return result

@router.put("/ticket-phases/{phase_code}")
def update_admin_ticket_phase(
    phase_code: str,
    payload: TicketPhaseUpdateRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Super Admin updates ticket phase status (ACTIVE/LOCKED), price, or inventory."""
    phase = db.query(TicketPhase).filter(TicketPhase.phase_code == phase_code.strip().upper()).first()
    if not phase:
        raise HTTPException(status_code=404, detail="Ticket phase not found.")

    if payload.name is not None:
        phase.name = payload.name.strip()
    if payload.price is not None:
        phase.price = float(payload.price)
    if payload.total_inventory is not None:
        phase.total_inventory = int(payload.total_inventory)
    if payload.badge_text is not None:
        phase.badge_text = payload.badge_text.strip()
    if payload.description is not None:
        phase.description = payload.description.strip()
    if payload.group_offer_eligible is not None:
        phase.group_offer_eligible = payload.group_offer_eligible

    if payload.status is not None:
        new_status = payload.status.strip().upper()
        if new_status not in ("ACTIVE", "LOCKED", "SOLD_OUT", "COMPLETED"):
            raise HTTPException(status_code=400, detail="Invalid phase status.")
        phase.status = new_status
        if new_status == "ACTIVE":
            event_setting = db.query(EventSetting).first()
            if event_setting:
                event_setting.ticket_price = phase.price

    phase.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(phase)

    return {
        "success": True,
        "message": f"Ticket phase {phase.name} updated successfully.",
        "phase": {
            "phase_code": phase.phase_code,
            "name": phase.name,
            "price": float(phase.price),
            "status": phase.status,
            "total_inventory": phase.total_inventory,
            "badge_text": phase.badge_text,
            "description": phase.description,
            "group_offer_eligible": phase.group_offer_eligible
        }
    }


