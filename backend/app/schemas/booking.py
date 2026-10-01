from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from app.schemas.ticket import TicketResponse

class BookingCreateRequest(BaseModel):
    customer_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: str = Field(..., min_length=10, max_length=15)
    ticket_count: int = Field(..., ge=1, le=10)
    idempotency_key: Optional[str] = None

class BookingDetailResponse(BaseModel):
    id: int
    booking_id: str
    customer_name: str
    email: str
    phone: str
    ticket_count: int
    ticket_price: float
    regular_amount: float = 0.0
    group_discount: float = 0.0
    ticket_subtotal: float = 0.0
    convenience_fee: float = 0.0
    payment_fee: float = 0.0
    gst_amount: float = 0.0
    amount: float
    currency: str = "INR"
    is_group_offer: bool = False
    offer_name: Optional[str] = None
    offer_id: Optional[str] = None
    offer_title: Optional[str] = None
    child_name: Optional[str] = None
    child_age: Optional[int] = None
    ticket_phase: Optional[str] = "EARLY_BIRD"
    payment_method: str = "UPI_MANUAL"
    utr_number: Optional[str] = None
    payment_screenshot: Optional[str] = None
    verified_by: Optional[str] = None
    verified_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    razorpay_order_id: Optional[str] = None
    razorpay_payment_id: Optional[str] = None
    payment_status: str
    booking_status: str
    email_status: str
    email_sent_at: Optional[datetime] = None
    email_error: Optional[str] = None
    admin_email_status: Optional[str] = "PENDING"
    admin_email_sent_at: Optional[datetime] = None
    admin_email_error: Optional[str] = None
    owner_notified: bool = False
    owner_notified_at: Optional[datetime] = None
    owner_notify_error: Optional[str] = None
    created_at: datetime
    tickets: List[TicketResponse] = []

    model_config = ConfigDict(from_attributes=True)

class BookingListResponse(BaseModel):
    items: List[BookingDetailResponse]
    total: int
    page: int
    per_page: int
    total_pages: int
