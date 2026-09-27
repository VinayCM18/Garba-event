from fastapi import APIRouter, Request, Header, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.payment_service import payment_service

router = APIRouter(prefix="/api/webhook", tags=["Webhooks"])

@router.post("/razorpay")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(None),
    db: Session = Depends(get_db)
):
    """Direct webhook endpoint for Razorpay."""
    body_bytes = await request.body()
    return payment_service.process_webhook(body_bytes, x_razorpay_signature, db)
