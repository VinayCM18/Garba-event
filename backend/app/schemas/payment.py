from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any

class CartItemInput(BaseModel):
    offer_id: str
    quantity: int = Field(1, ge=1, le=50)

class ChildInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    age: int = Field(..., ge=5, le=12)

class CalculateFeeRequest(BaseModel):
    ticket_count: Optional[int] = Field(default=1, ge=1, le=500)
    ticket_phase: Optional[str] = "EARLY_BIRD"
    offer_id: Optional[str] = None
    quantity: Optional[int] = Field(default=1, ge=1, le=50)
    items: Optional[List[CartItemInput]] = None

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
    offer_id: Optional[str] = None
    offer_title: Optional[str] = None
    passes_count: Optional[int] = None
    unit_count: Optional[int] = 1
    unit_price: Optional[float] = None
    is_kids: bool = False
    id_proof_note: Optional[str] = None
    items: Optional[List[Dict[str, Any]]] = None
    total_passes: Optional[int] = None
    is_mixed_cart: bool = False

class CreateOrderRequest(BaseModel):
    customer_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: str = Field(..., min_length=10, max_length=15)
    ticket_count: Optional[int] = Field(default=None, ge=1, le=500)
    ticket_phase: Optional[str] = "EARLY_BIRD"
    idempotency_key: Optional[str] = None
    offer_id: Optional[str] = None
    quantity: Optional[int] = Field(default=1, ge=1, le=50)
    child_name: Optional[str] = None
    child_age: Optional[int] = None
    items: Optional[List[CartItemInput]] = None
    children: Optional[List[ChildInput]] = None

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
    offer_id: Optional[str] = None
    offer_title: Optional[str] = None
    passes_count: Optional[int] = None
    child_name: Optional[str] = None
    child_age: Optional[int] = None
    items: Optional[List[Dict[str, Any]]] = None
    total_passes: Optional[int] = None
    is_mixed_cart: bool = False
    children_details: Optional[List[Dict[str, Any]]] = None
    
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

