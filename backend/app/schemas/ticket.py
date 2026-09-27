from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

class TicketResponse(BaseModel):
    ticket_id: str
    booking_id: str
    customer_name: str
    event_name: str
    ticket_status: str
    checkin_status: bool
    checked_in_at: Optional[datetime] = None
    created_at: datetime
    qr_token_raw: Optional[str] = None
    qr_code_base64: Optional[str] = None
    ticket_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class VerifyQRRequest(BaseModel):
    qr_token: str

class VerifyQRResponse(BaseModel):
    valid: bool
    status: str  # VALID, USED, INVALID, CANCELLED
    message: str
    ticket_id: Optional[str] = None
    booking_id: Optional[str] = None
    customer_name: Optional[str] = None
    event_name: Optional[str] = None
    ticket_status: Optional[str] = None
    checkin_status: Optional[bool] = None
    checked_in_at: Optional[datetime] = None
    qr_token_raw: Optional[str] = None

class CheckInRequest(BaseModel):
    qr_token: str
    device_information: Optional[str] = "Scanner Web Camera"
    notes: Optional[str] = None

class CheckInResponse(BaseModel):
    success: bool
    status: str # SUCCESS, ALREADY_USED, INVALID, CANCELLED
    message: str
    ticket_id: Optional[str] = None
    booking_id: Optional[str] = None
    customer_name: Optional[str] = None
    checked_in_at: Optional[datetime] = None
    staff_name: Optional[str] = None
