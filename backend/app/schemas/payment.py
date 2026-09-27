from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class CalculateFeeRequest(BaseModel):
    ticket_count: int = Field(..., ge=1, le=10)

class CalculateFeeResponse(BaseModel):
    ticket_price: float
    ticket_count: int
    regular_amount: float = 0.0
    group_discount: float = 0.0
    ticket_subtotal: float
    payment_fee: float
    gst_amount: float
    total_amount: float
    currency: str = "INR"
    is_group_offer: bool = False
    offer_name: Optional[str] = None
    free_tickets: int = 0

class CreateOrderRequest(BaseModel):
    customer_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: str = Field(..., min_length=10, max_length=15)
    ticket_count: int = Field(..., ge=1, le=10)
    idempotency_key: Optional[str] = None

class CreateOrderResponse(BaseModel):
    payment_method: str = "UPI_MANUAL" # "UPI_MANUAL" or "RAZORPAY"
    booking_id: str
    amount: float
    currency: str = "INR"
    ticket_price: float
    ticket_count: int
    regular_amount: float = 0.0
    group_discount: float = 0.0
    ticket_subtotal: float
    payment_fee: float = 0.0
    gst_amount: float = 0.0
    customer_name: str
    customer_email: str
    customer_phone: str
    is_group_offer: bool = False
    offer_name: Optional[str] = None
    free_tickets: int = 0
    
    # Manual UPI Fields
    payment_id: Optional[str] = None
    upi_id: Optional[str] = None
    upi_qr_image_url: Optional[str] = None
    upi_payment_instructions: Optional[str] = None
    
    # Razorpay Fields (Optional when UPI_MANUAL)
    razorpay_order_id: Optional[str] = None
    key_id: Optional[str] = None
    is_simulation: bool = False

class SubmitPaymentProofResponse(BaseModel):
    success: bool
    message: str
    booking_id: str
    booking_status: str
    payment_status: str
    utr_number: str

class VerifyPaymentRequest(BaseModel):
    booking_id: str
    razorpay_order_id: Optional[str] = None
    razorpay_payment_id: Optional[str] = None
    razorpay_signature: Optional[str] = None

class VerifyPaymentResponse(BaseModel):
    success: bool
    message: str
    booking_id: str
    payment_status: str
    booking_status: str

