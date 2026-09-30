from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class DashboardStatsResponse(BaseModel):
    tickets_sold: int
    revenue: float
    total_bookings: int
    checked_in: int
    remaining_tickets: int
    total_capacity: int
    checkin_rate_percentage: float

class DailyStatItem(BaseModel):
    date: str
    revenue: float
    tickets: int
    bookings: int

class HourlyCheckInItem(BaseModel):
    hour: str
    count: int

class DashboardAnalyticsResponse(BaseModel):
    stats: DashboardStatsResponse
    sales_trend: List[DailyStatItem]
    checkin_trend: List[HourlyCheckInItem]

class EventSettingResponse(BaseModel):
    event_name: str
    event_tagline: str
    event_date: str
    event_time: str
    venue_name: str
    venue_address: str
    venue_city: str
    ticket_price: float
    convenience_fee: float
    total_capacity: int
    max_per_booking: int
    booking_open: bool
    contact_email: str
    contact_phone: str
    rules_text: str
    
    # Group Offer Settings
    group_offer_enabled: bool = True
    group_offer_size: int = 10
    group_offer_free_tickets: int = 1
    group_offer_discount: float = 599.0

    # Owner & Email Dispatch Configuration
    email_provider: str = "resend" # "resend", "smtp", or "console"
    resend_api_key_set: bool = False
    owner_notification_email: str = ""
    owner_notification_phone: str = ""
    owner_notification_enabled: bool = True
    owner_webhook_url: Optional[str] = None
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password_set: bool = False
    smtp_from_email: str = "tickets@garbanight.in"
    smtp_from_name: str = "NAVRANG 2026"
    smtp_use_tls: bool = True

    # Payment Provider & Manual UPI Settings
    payment_method: str = "UPI_MANUAL"
    upi_id: str = "samaymadhyastha2005@oksbi"
    upi_qr_image: str = "uploads/qr/upi_qr.jpg"
    upi_payment_instructions: str = "Scan using GPay | PhonePe | Paytm | Any UPI App. After completing payment, enter your UTR / Transaction ID to confirm."

    # Razorpay Payment Gateway
    razorpay_key_id: Optional[str] = None
    razorpay_key_secret_set: bool = False
    razorpay_webhook_secret_set: bool = False

    model_config = ConfigDict(from_attributes=True)

class EventSettingUpdateRequest(BaseModel):
    event_name: Optional[str] = None
    event_tagline: Optional[str] = None
    event_date: Optional[str] = None
    event_time: Optional[str] = None
    venue_name: Optional[str] = None
    venue_address: Optional[str] = None
    venue_city: Optional[str] = None
    ticket_price: Optional[float] = None
    convenience_fee: Optional[float] = None
    total_capacity: Optional[int] = None
    max_per_booking: Optional[int] = None
    booking_open: Optional[bool] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    rules_text: Optional[str] = None
    
    # Group Offer Settings
    group_offer_enabled: Optional[bool] = None
    group_offer_size: Optional[int] = None
    group_offer_free_tickets: Optional[int] = None

    # Owner & Email Dispatch Configuration
    email_provider: Optional[str] = None
    resend_api_key: Optional[str] = None
    owner_notification_email: Optional[str] = None
    owner_notification_phone: Optional[str] = None
    owner_notification_enabled: Optional[bool] = None
    owner_webhook_url: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from_email: Optional[str] = None
    smtp_from_name: Optional[str] = None
    smtp_use_tls: Optional[bool] = None

    # Payment Provider & Manual UPI Settings
    payment_method: Optional[str] = None
    upi_id: Optional[str] = None
    upi_qr_image: Optional[str] = None
    upi_payment_instructions: Optional[str] = None

    # Razorpay Payment Gateway
    razorpay_key_id: Optional[str] = None
    razorpay_key_secret: Optional[str] = None
    razorpay_webhook_secret: Optional[str] = None

class PaymentVerificationItem(BaseModel):
    id: int
    booking_id: str
    customer_name: str
    phone: str
    email: str
    ticket_count: int
    amount: float
    currency: str = "INR"
    payment_method: str = "UPI_MANUAL"
    utr_number: Optional[str] = None
    has_screenshot: bool = False
    screenshot_url: Optional[str] = None
    payment_status: str
    booking_status: str
    submitted_at: Optional[datetime] = None
    verified_by: Optional[str] = None
    verified_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_at: datetime

class PaymentRejectRequest(BaseModel):
    reason: str

class TestEmailRequest(BaseModel):
    to_email: Optional[str] = None

class RecentNotificationItem(BaseModel):
    id: int
    booking_id: str
    customer_name: str
    email: str
    phone: str
    ticket_count: int
    amount: float
    payment_status: str
    booking_status: str
    email_status: str
    owner_notified: bool
    created_at: datetime

class CheckInLogItem(BaseModel):
    id: int
    ticket_id: str
    booking_id: str
    customer_name: str
    staff_name: Optional[str] = None
    result: str
    checked_in_at: datetime
    ip_address: Optional[str] = None
    device_information: Optional[str] = None

class AuditLogItem(BaseModel):
    id: int
    user_email: Optional[str] = None
    action: str
    entity_type: str
    entity_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    details: Optional[str] = None
    timestamp: datetime
