from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class CalculateFeeRequest(BaseModel):
    ticket_count: int = Field(..., ge=1, le=10)
    ticket_phase: Optional[str] = "EARLY_BIRD"

class CalculateFeeResponse(BaseModel):
    ticket_price: float
    ticket_count: int
    ticket_phase: Optional[str] = "EARLY_BIRD"
    phase_name: Optional[str] = "Early Bird"
    regular_amount: float = 0.0
    group_discount: float = 0.0
    ticket_subtotal: float
    payment_fee: float = 0.0
    gst_amount: float = 0.0
    tax_amount: float = 0.0
    base_amount: float = 0.0
    tax_rate: float = 0.18
    tax_included: bool = True
    tax_label: str = "Taxes included"
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
    ticket_phase: Optional[str] = "EARLY_BIRD"
    idempotency_key: Optional[str] = None

class CreateOrderResponse(BaseModel):
    payment_method: str = "RAZORPAY" # "RAZORPAY" or "UPI_MANUAL"
    booking_id: str
    ticket_phase: Optional[str] = "EARLY_BIRD"
    phase_name: Optional[str] = "Early Bird"
    amount: float
    currency: str = "INR"
    ticket_price: float
    ticket_count: int
    regular_amount: float = 0.0
    group_discount: float = 0.0
    ticket_subtotal: float
    payment_fee: float = 0.0
    gst_amount: float = 0.0
    tax_amount: float = 0.0
    base_amount: float = 0.0
    tax_rate: float = 0.18
    tax_included: bool = True
    tax_label: str = "Taxes included"
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
    
    # Razorpay Fields
    razorpay_order_id: Optional[str] = None
    key_id: Optional[str] = None
    razorpay_mode: Optional[str] = "TEST"
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

