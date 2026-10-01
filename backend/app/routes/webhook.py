from typing import Optional
from fastapi import APIRouter, Request, Header, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.routes.payment import razorpay_webhook

router = APIRouter(prefix="/api/webhook", tags=["Webhooks"])

@router.post(
    "/razorpay",
    deprecated=True,
    summary="Legacy Razorpay Webhook Endpoint (Internally delegates to canonical /api/payments/webhook)"
)
async def legacy_razorpay_webhook(
    request: Request,
    x_razorpay_signature: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Legacy Webhook Endpoint.
    Canonical endpoint is `/api/payments/webhook`.
    This endpoint safely delegates internally to the canonical handler in app.routes.payment
    for backward compatibility with legacy configurations.
    """
    return await razorpay_webhook(request, x_razorpay_signature, db)

