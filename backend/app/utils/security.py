import hashlib
import hmac
import secrets
import jwt
import bcrypt
from datetime import datetime, timedelta
from app.config import settings

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    encoded_jwt = jwt.encode(to_encode, settings.effective_jwt_secret(), algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.effective_jwt_secret(), algorithms=[settings.JWT_ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None

def generate_secure_token(prefix: str = "GN26") -> str:
    """Generate a cryptographically secure, unguessable token for QR codes and tickets."""
    random_part = secrets.token_urlsafe(32)
    return f"{prefix}_{random_part}"

def hash_qr_token(raw_token: str) -> str:
    """Hash the raw QR token with SHA-256 and app salt.
    The database only stores this hash to prevent DB leak attacks."""
    salted = f"{raw_token}:{settings.effective_qr_salt()}"
    return hashlib.sha256(salted.encode("utf-8")).hexdigest()

def verify_razorpay_signature(order_id: str, payment_id: str, signature: str, key_secret: str = None) -> bool:
    """Verify Razorpay payment signature using HMAC SHA256."""
    secret_str = key_secret or settings.RAZORPAY_KEY_SECRET
    if not secret_str:
        return False
    msg = f"{order_id}|{payment_id}".encode("utf-8")
    secret = secret_str.encode("utf-8")
    generated_signature = hmac.new(secret, msg, hashlib.sha256).hexdigest()
    return hmac.compare_digest(generated_signature, signature)

def verify_razorpay_webhook_signature(body: bytes, signature: str, webhook_secret: str = None) -> bool:
    """Verify Razorpay webhook signature."""
    secret_str = webhook_secret or settings.RAZORPAY_WEBHOOK_SECRET
    if not secret_str:
        return False
    secret = secret_str.encode("utf-8")
    generated_signature = hmac.new(secret, body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(generated_signature, signature)
