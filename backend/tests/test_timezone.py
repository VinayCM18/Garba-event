import pytest
import sys
import os
from datetime import datetime, timezone, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.timezone import (
    UTC,
    IST,
    ensure_utc,
    utc_to_ist,
    format_ist_datetime,
    UtcDatetime,
)
from app.schemas.booking import BookingDetailResponse
from app.schemas.admin import AuditLogItem, PaymentVerificationItem, CheckInLogItem
from app.schemas.ticket import TicketResponse


def test_utc_to_ist_conversion():
    """Verify known test case: 2026-10-02 07:17 UTC must map to 12:47 PM IST."""
    utc_dt = datetime(2026, 10, 2, 7, 17, 0)
    ist_dt = utc_to_ist(utc_dt)
    
    assert ist_dt.hour == 12
    assert ist_dt.minute == 47
    assert ist_dt.day == 2
    assert ist_dt.month == 10
    assert ist_dt.year == 2026
    
    formatted = format_ist_datetime(utc_dt)
    assert formatted == "02 Oct 2026, 12:47 PM"


def test_midnight_boundary_1830_utc():
    """Verify 18:30 UTC (Oct 1) transitions to 00:00 AM IST (Oct 2)."""
    utc_dt = datetime(2026, 10, 1, 18, 30, 0)
    ist_dt = utc_to_ist(utc_dt)
    
    assert ist_dt.day == 2
    assert ist_dt.hour == 0
    assert ist_dt.minute == 0
    
    formatted = format_ist_datetime(utc_dt)
    assert formatted == "02 Oct 2026, 12:00 AM"


def test_day_boundary_2000_utc():
    """Verify 20:00 UTC (Oct 1) transitions to 01:30 AM IST (Oct 2)."""
    utc_dt = datetime(2026, 10, 1, 20, 0, 0)
    ist_dt = utc_to_ist(utc_dt)
    
    assert ist_dt.day == 2
    assert ist_dt.hour == 1
    assert ist_dt.minute == 30
    
    formatted = format_ist_datetime(utc_dt)
    assert formatted == "02 Oct 2026, 01:30 AM"


def test_morning_boundaries():
    """Verify 00:00 UTC and 05:30 UTC conversions."""
    # 00:00 UTC -> 05:30 AM IST
    dt_zero = datetime(2026, 10, 2, 0, 0, 0)
    assert format_ist_datetime(dt_zero) == "02 Oct 2026, 05:30 AM"
    
    # 05:30 UTC -> 11:00 AM IST
    dt_five_thirty = datetime(2026, 10, 2, 5, 30, 0)
    assert format_ist_datetime(dt_five_thirty) == "02 Oct 2026, 11:00 AM"


def test_utc_datetime_schema_serialization():
    """Verify Pydantic models with UtcDatetime serialize naive datetimes as ISO 8601 with 'Z'."""
    naive_dt = datetime(2026, 10, 2, 7, 17, 0)
    
    ticket = TicketResponse(
        ticket_id="TKT-001",
        booking_id="GN-2026-00001",
        customer_name="Test Customer",
        event_name="NAVRANG 2026",
        ticket_status="VALID",
        checkin_status=False,
        checked_in_at=None,
        created_at=naive_dt,
    )
    dumped = ticket.model_dump(mode="json")
    assert dumped["created_at"] == "2026-10-02T07:17:00Z"
    
    audit = AuditLogItem(
        id=1,
        action="LOGIN",
        entity_type="user",
        timestamp=naive_dt,
    )
    audit_dumped = audit.model_dump(mode="json")
    assert audit_dumped["timestamp"] == "2026-10-02T07:17:00Z"


def test_ensure_utc_idempotence():
    """Verify ensure_utc handles aware and naive datetimes correctly."""
    naive = datetime(2026, 10, 2, 7, 17, 0)
    aware_utc = ensure_utc(naive)
    assert aware_utc.tzinfo == UTC
    
    # Passing an already aware datetime returns UTC
    re_ensured = ensure_utc(aware_utc)
    assert re_ensured == aware_utc
