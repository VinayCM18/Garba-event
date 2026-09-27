from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from app.database import get_db
from app.models.user import User
from app.models.audit_log import AuditLog
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse
from app.utils.security import verify_password, create_access_token
from app.middleware.auth import get_current_user
from app.config import settings

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, response: Response, request: Request, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    user = db.query(User).filter(func.lower(User.email) == email).first()
    
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    if not user or not verify_password(payload.password, user.password_hash):
        # Audit failed login attempt
        audit = AuditLog(
            user_id=user.id if user else None,
            action="LOGIN_FAILED",
            entity_type="user",
            entity_id=email,
            ip_address=client_ip,
            user_agent=user_agent,
            details='{"reason": "Invalid credentials"}'
        )
        db.add(audit)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled. Please contact the administrator."
        )

    # Update last login
    user.last_login_at = datetime.utcnow()

    # Generate token
    token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role},
        expires_delta=token_expires
    )

    # Set secure HTTP-only cookie
    response.set_cookie(
        key="admin_access_token",
        value=token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=False if settings.ENVIRONMENT == "development" else True
    )

    # Audit success
    audit = AuditLog(
        user_id=user.id,
        action="LOGIN_SUCCESS",
        entity_type="user",
        entity_id=str(user.id),
        ip_address=client_ip,
        user_agent=user_agent,
        details=f'{{"role": "{user.role}"}}'
    )
    db.add(audit)
    db.commit()

    return TokenResponse(
        access_token=token,
        role=user.role,
        name=user.name,
        email=user.email
    )

@router.post("/logout")
def logout(response: Response, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response.delete_cookie("admin_access_token")
    audit = AuditLog(
        user_id=current_user.id,
        action="LOGOUT",
        entity_type="user",
        entity_id=str(current_user.id)
    )
    db.add(audit)
    db.commit()
    return {"message": "Successfully logged out."}

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
