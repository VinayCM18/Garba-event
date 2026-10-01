from pydantic_settings import BaseSettings
from typing import Optional, List
import os
import secrets

# ---------------------------------------------------------------------------
# Insecure placeholder detection
# ---------------------------------------------------------------------------
_INSECURE_MARKERS = {
    "garba-night-super-secret-jwt-key-2026-production",
    "garba-night-qr-crypt-salt-2026",
    "changeme",
    "secret",
    "password",
    "",
}


class Settings(BaseSettings):
    # App Settings
    PROJECT_NAME: str = "NAVRANG 2026"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # URLs
    FRONTEND_URL: str = "http://localhost:5173"
    BACKEND_URL: str = "http://localhost:8000"

    # Database (Default to SQLite if Postgres not set; supports postgresql://)
    DATABASE_URL: str = "sqlite:///./garba_night.db"

    # Security — MUST be set via environment variables in production
    # Generate with: python -c "import secrets; print(secrets.token_hex(32))"
    JWT_SECRET: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    QR_SECRET_SALT: str = ""

    # Payment Provider Settings (Pluggable: "RAZORPAY" or "UPI_MANUAL")
    PAYMENT_METHOD: Optional[str] = None
    PAYMENT_PROVIDER: Optional[str] = None
    UPI_ID: str = ""
    UPI_QR_IMAGE: str = "uploads/qr/upi_qr.jpg"
    UPI_PAYMENT_INSTRUCTIONS: str = (
        "Scan using GPay | PhonePe | Paytm | Any UPI App. "
        "After completing payment, enter your UTR / Transaction ID to confirm."
    )

    # Razorpay Payment Gateway (Used when PAYMENT_METHOD="RAZORPAY")
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""
    RAZORPAY_MODE: str = "TEST"  # "TEST" or "LIVE"

    # Tax & Gateway Fee Configuration
    TAX_INCLUDED: bool = True
    TAX_RATE: float = 0.0
    PASS_GATEWAY_FEE_TO_CUSTOMER: bool = False  # No tax/fee added to ticket price
    GATEWAY_FEE_RATE: float = 0.0
    GATEWAY_FEE_GST_RATE: float = 0.0

    # Email Delivery (Resend API, SMTP, or Console)
    EMAIL_PROVIDER: str = "resend"  # "resend" | "smtp" | "console"
    RESEND_API_KEY: Optional[str] = None
    SMTP_HOST: Optional[str] = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_USE_TLS: bool = True
    FROM_EMAIL: str = ""
    FROM_NAME: str = "NAVRANG 2026"
    ALLOW_PLACEHOLDER_EMAILS: bool = False  # Blocks accidental delivery to example.com/test.com dummy addresses

    OWNER_NOTIFICATION_EMAIL: str = ""
    OWNER_NOTIFICATION_PHONE: str = ""
    OWNER_NOTIFICATION_ENABLED: bool = True
    OWNER_WEBHOOK_URL: Optional[str] = None
    ADMIN_NOTIFICATION_EMAIL: str = ""

    # Default Event Configuration
    DEFAULT_EVENT_NAME: str = "NAVRANG 2026"
    DEFAULT_EVENT_DATE: str = "October 17, 2026"
    DEFAULT_EVENT_TIME: str = "06:30 PM - 10:00 PM"
    DEFAULT_EVENT_VENUE: str = "The Green Acres, Mysuru"
    DEFAULT_TICKET_PRICE: float = 599.00
    DEFAULT_CONVENIENCE_FEE: float = 0.00
    DEFAULT_TOTAL_CAPACITY: int = 1500
    DEFAULT_MAX_PER_BOOKING: int = 10

    # Reservation Timeout (Minutes)
    PAYMENT_RESERVATION_MINUTES: int = 15

    class Config:
        env_file = ".env"
        extra = "ignore"

    _cached_dev_jwt: Optional[str] = None
    _cached_dev_qr: Optional[str] = None

    # ------------------------------------------------------------------
    # Runtime secret validation
    # ------------------------------------------------------------------
    def effective_jwt_secret(self) -> str:
        """Return the JWT secret, caching an ephemeral one in dev only."""
        if self.JWT_SECRET and self.JWT_SECRET not in _INSECURE_MARKERS:
            return self.JWT_SECRET
        if self.ENVIRONMENT == "production":
            raise RuntimeError(
                "JWT_SECRET must be set to a strong random value in production. "
                "Run: python -c \"import secrets; print(secrets.token_hex(32))\" "
                "and set the result as JWT_SECRET in your environment."
            )
        # Development fallback — cached per-process so sessions survive API calls
        if not self._cached_dev_jwt:
            self._cached_dev_jwt = secrets.token_hex(32)
            import warnings
            warnings.warn(
                "JWT_SECRET not set — using an ephemeral per-process secret. "
                "Tokens will be invalidated on server restart. "
                "Set JWT_SECRET in backend/.env for persistent sessions.",
                stacklevel=2,
            )
        return self._cached_dev_jwt

    def effective_qr_salt(self) -> str:
        """Return the QR secret salt, caching an ephemeral one in dev only."""
        if self.QR_SECRET_SALT and self.QR_SECRET_SALT not in _INSECURE_MARKERS:
            return self.QR_SECRET_SALT
        if self.ENVIRONMENT == "production":
            raise RuntimeError(
                "QR_SECRET_SALT must be set to a strong random value in production."
            )
        if not self._cached_dev_qr:
            self._cached_dev_qr = secrets.token_hex(16)
            import warnings
            warnings.warn(
                "QR_SECRET_SALT not set — using an ephemeral per-process salt. "
                "QR codes will be invalidated on server restart. "
                "Set QR_SECRET_SALT in backend/.env.",
                stacklevel=2,
            )
        return self._cached_dev_qr


settings = Settings()
