from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models.user import User
from app.utils.security import decode_access_token

security = HTTPBearer(auto_error=False)

def get_current_user(
    request: Request,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    token = None
    if auth and auth.credentials:
        token = auth.credentials.strip()
    elif "authorization" in request.headers:
        auth_header = request.headers.get("authorization", "").strip()
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()
        elif auth_header:
            token = auth_header
    elif "admin_access_token" in request.cookies:
        token = request.cookies.get("admin_access_token")
    
    if not token or token.lower() in ("null", "undefined", ""):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token.",
            headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
        )
    
    user_id = payload.get("sub")
    try:
        user_id_int = int(user_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject.",
            headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
        )

    user = db.query(User).filter(User.id == user_id_int, User.is_active == True).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or disabled.",
        )
    return user

def get_optional_current_user(
    request: Request,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    token = None
    if auth and auth.credentials:
        token = auth.credentials.strip()
    elif "authorization" in request.headers:
        auth_header = request.headers.get("authorization", "").strip()
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()
        elif auth_header:
            token = auth_header
    elif "admin_access_token" in request.cookies:
        token = request.cookies.get("admin_access_token")
    
    if not token or token.lower() in ("null", "undefined", ""):
        return None
    
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        return None
    
    try:
        user_id_int = int(payload.get("sub"))
        return db.query(User).filter(User.id == user_id_int, User.is_active == True).first()
    except Exception:
        return None

def require_roles(allowed_roles: List[str]):
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Insufficient privileges. Required role in {allowed_roles}.",
            )
        return current_user
    return role_checker

# Predefined role dependencies
require_super_admin = require_roles(["SUPER_ADMIN"])
require_admin = require_roles(["SUPER_ADMIN", "ADMIN"])
require_staff = require_roles(["SUPER_ADMIN", "ADMIN", "CHECKIN_STAFF", "STAFF"])
