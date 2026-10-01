from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import os
from contextlib import asynccontextmanager
from sqlalchemy import func

from app.config import settings, _INSECURE_MARKERS
from app.database import Base, engine, SessionLocal
from app.models.user import User
from app.models.event_setting import EventSetting
from app.utils.security import get_password_hash
from app.middleware.rate_limit import RateLimitMiddleware

# Routers
from app.routes.auth import router as auth_router
from app.routes.booking import router as booking_router
from app.routes.payment import router as payment_router
from app.routes.ticket import router as ticket_router
from app.routes.admin import router as admin_router
from app.routes.staff import router as staff_router
from app.routes.webhook import router as webhook_router

logger = logging.getLogger("garba_night")

def init_db_defaults():
    """Initializes tables and default superadmin & event settings if database is empty."""
    Base.metadata.create_all(bind=engine)
    from app.database import sync_database_schema
    sync_database_schema()
    db = SessionLocal()
    try:
        # Check event settings
        setting = db.query(EventSetting).first()
        if not setting:
            setting = EventSetting(
                event_name="NAVRANG 2026",
                event_tagline="Celebrate. Dance. Connect.",
                event_date="October 17, 2026",
                event_time="06:30 PM - 10:00 PM",
                venue_name="Green Acres",
                venue_address="Green Acres, Mysuru",
                venue_city="Mysuru",
                ticket_price=599.0,
                convenience_fee=0.0,
                total_capacity=1500,
                max_per_booking=10,
                booking_open=True,
                payment_method="RAZORPAY",
                contact_email="support@garbanight.in",
                contact_phone="+91 98765 43210"
            )
            db.add(setting)
        else:
            if not setting.event_name or "garba" in setting.event_name.lower():
                setting.event_name = "NAVRANG 2026"
            if not setting.event_time or "07:00" in setting.event_time or "7:00" in setting.event_time:
                setting.event_time = "06:30 PM - 10:00 PM"
            if not setting.event_tagline or "cultural gala" in setting.event_tagline.lower():
                setting.event_tagline = "Celebrate. Dance. Connect."
            env_raw = (
                os.environ.get("PAYMENT_PROVIDER")
                or os.environ.get("PAYMENT_METHOD")
                or getattr(settings, "PAYMENT_PROVIDER", None)
                or getattr(settings, "PAYMENT_METHOD", None)
                or ""
            )
            env_norm = env_raw.strip().upper() if isinstance(env_raw, str) else ""
            if env_norm in ("RAZORPAY", "RZP") or (not env_norm and setting.payment_method in (None, "", "UPI_MANUAL")):
                setting.payment_method = "RAZORPAY"

        # Check and seed TicketPhases
        from app.models.ticket_phase import TicketPhase
        if db.query(TicketPhase).count() == 0:
            default_phases = [
                TicketPhase(
                    phase_code="EARLY_BIRD",
                    name="EARLY BIRD",
                    price=599.0,
                    tax_included=True,
                    status="ACTIVE",
                    total_inventory=300,
                    sold_count=0,
                    display_order=1,
                    badge_text="LIVE",
                    description="Phase 1 early-access ticket with all-inclusive venue & celebration pass.",
                    group_offer_eligible=True
                ),
                TicketPhase(
                    phase_code="PHASE_1",
                    name="PHASE 1",
                    price=799.0,
                    tax_included=True,
                    status="LOCKED",
                    total_inventory=500,
                    sold_count=0,
                    display_order=2,
                    badge_text="COMING SOON",
                    description="Standard tier ticket unlocks once Early Bird phase concludes.",
                    group_offer_eligible=False
                ),
                TicketPhase(
                    phase_code="PHASE_2",
                    name="PHASE 2",
                    price=899.0,
                    tax_included=True,
                    status="LOCKED",
                    total_inventory=700,
                    sold_count=0,
                    display_order=3,
                    badge_text="LOCKED",
                    description="Final tier ticket for late registrations.",
                    group_offer_eligible=False
                )
            ]
            for phase in default_phases:
                db.add(phase)

        import warnings

        is_prod = (settings.ENVIRONMENT == "production")

        admin_email = os.environ.get("ADMIN_EMAIL", "admin@garbanight.in").strip()
        admin_name = os.environ.get("ADMIN_NAME", "Head Organizer (Super Admin)")
        staff_email = os.environ.get("STAFF_EMAIL", "staff@garbanight.in").strip()
        staff_name = os.environ.get("STAFF_NAME", "Gate Security Staff")

        # In production, seed passwords MUST come from secure environment variables
        admin_pass = os.environ.get("ADMIN_SEED_PASSWORD") or os.environ.get("ADMIN_PASSWORD")
        staff_pass = os.environ.get("STAFF_SEED_PASSWORD") or os.environ.get("STAFF_PASSWORD")
        vinay_pass = os.environ.get("VINAY_ADMIN_PASSWORD")
        samay_pass = os.environ.get("SAMAY_ADMIN_PASSWORD")

        predictable_passwords = {
            "garbanight@2026",
            "staffentry@2026",
            "admin123",
            "password",
            "admin",
            "staff",
            "123456",
            "12345678",
        }

        seed_targets = [
            (admin_email, admin_pass, admin_name, "SUPER_ADMIN", "ADMIN_SEED_PASSWORD", "GarbaNight@2026"),
            (staff_email, staff_pass, staff_name, "CHECKIN_STAFF", "STAFF_SEED_PASSWORD", "StaffEntry@2026"),
            ("vinay18744@gmail.com", vinay_pass, "Vinay (Super Admin)", "SUPER_ADMIN", "VINAY_ADMIN_PASSWORD", "GarbaNight@2026"),
            ("samaymadhyastha2005@gmail.com", samay_pass, "Samay (Super Admin)", "SUPER_ADMIN", "SAMAY_ADMIN_PASSWORD", "GarbaNight@2026"),
        ]

        for seed_email, seed_pass, seed_name, seed_role, env_var_name, dev_fallback in seed_targets:
            existing = db.query(User).filter(func.lower(User.email) == seed_email.lower()).first()
            if not existing:
                if is_prod:
                    if not seed_pass or len(seed_pass) < 12 or seed_pass.lower() in predictable_passwords:
                        raise RuntimeError(
                            f"CRITICAL CONFIGURATION ERROR: Seed account '{seed_email}' does not exist, but required "
                            f"production environment variable '{env_var_name}' is missing or weak (minimum 12 characters required, "
                            f"predictable default passwords strictly prohibited). Set '{env_var_name}' in Railway environment variables."
                        )
                else:
                    if not seed_pass:
                        seed_pass = dev_fallback

                if seed_pass:
                    new_user = User(
                        email=seed_email.lower(),
                        name=seed_name,
                        password_hash=get_password_hash(seed_pass),
                        role=seed_role,
                        is_active=True
                    )
                    db.add(new_user)
            # CRITICAL: Never overwrite an existing user's password on startup or restart!

        db.commit()
    except Exception as e:
        logger.error(f"Error seeding default database records: {e}")
        db.rollback()
        if settings.ENVIRONMENT == "production":
            raise
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing NAVRANG 2026 Backend...")
    init_db_defaults()

    # Production environment strict validation
    if settings.ENVIRONMENT == "production":
        if settings.DEBUG:
            raise RuntimeError("CRITICAL CONFIGURATION ERROR: DEBUG must be False in production.")
        if not settings.JWT_SECRET or settings.JWT_SECRET in _INSECURE_MARKERS:
            raise RuntimeError("CRITICAL CONFIGURATION ERROR: JWT_SECRET must be set to a strong random value in production.")
        if not settings.QR_SECRET_SALT or settings.QR_SECRET_SALT in _INSECURE_MARKERS:
            raise RuntimeError("CRITICAL CONFIGURATION ERROR: QR_SECRET_SALT must be set to a strong random value in production.")

        rzp_mode = (os.environ.get("RAZORPAY_MODE") or getattr(settings, "RAZORPAY_MODE", "TEST")).strip().strip("'\"").upper()
        raw_key = (os.environ.get("RAZORPAY_KEY_ID") or getattr(settings, "RAZORPAY_KEY_ID", "") or "").strip().strip("'\"")
        raw_secret = (os.environ.get("RAZORPAY_KEY_SECRET") or getattr(settings, "RAZORPAY_KEY_SECRET", "") or "").strip().strip("'\"")
        raw_webhook = (os.environ.get("RAZORPAY_WEBHOOK_SECRET") or getattr(settings, "RAZORPAY_WEBHOOK_SECRET", "") or "").strip().strip("'\"")

        if not raw_key:
            raise RuntimeError("CRITICAL CONFIGURATION ERROR: RAZORPAY_KEY_ID is missing in production.")
        if not raw_secret:
            raise RuntimeError("CRITICAL CONFIGURATION ERROR: RAZORPAY_KEY_SECRET is missing in production.")
        if not raw_webhook:
            raise RuntimeError("CRITICAL CONFIGURATION ERROR: RAZORPAY_WEBHOOK_SECRET is missing in production.")

        if rzp_mode == "LIVE":
            if not raw_key.startswith("rzp_live_"):
                raise RuntimeError("CRITICAL CONFIGURATION ERROR: RAZORPAY_MODE is LIVE but RAZORPAY_KEY_ID does not start with 'rzp_live_'.")
        elif rzp_mode == "TEST":
            if not raw_key.startswith("rzp_test_"):
                raise RuntimeError("CRITICAL CONFIGURATION ERROR: RAZORPAY_MODE is TEST but RAZORPAY_KEY_ID does not start with 'rzp_test_'.")
        else:
            raise RuntimeError(f"CRITICAL CONFIGURATION ERROR: Invalid RAZORPAY_MODE '{rzp_mode}'. Must be TEST or LIVE.")

    # Safe Razorpay configuration startup logging
    try:
        rzp_mode = (os.environ.get("RAZORPAY_MODE") or getattr(settings, "RAZORPAY_MODE", "TEST")).strip().strip("'\"").upper()
        raw_key = (os.environ.get("RAZORPAY_KEY_ID") or getattr(settings, "RAZORPAY_KEY_ID", "") or "").strip().strip("'\"")

        if rzp_mode == "LIVE":
            key_type = "LIVE" if raw_key.startswith("rzp_live_") else ("TEST" if raw_key.startswith("rzp_test_") else "UNKNOWN")
            key_prefix = raw_key[:9] if len(raw_key) >= 9 else (raw_key if raw_key else "NONE")
            logger.info(f"Razorpay mode: {rzp_mode}")
            logger.info(f"Razorpay key type: {key_type}")
            logger.info(f"Razorpay key prefix: {key_prefix}")
            if key_type != "LIVE":
                logger.warning(
                    f"CONFIGURATION WARNING: RAZORPAY_MODE is LIVE but key type is {key_type} (prefix: {key_prefix}). "
                    "LIVE mode requires a key starting with rzp_live_ in Railway environment variables."
                )
        else:
            key_type = "TEST" if raw_key.startswith("rzp_test_") else ("LIVE" if raw_key.startswith("rzp_live_") else ("NONE" if not raw_key else "CUSTOM"))
            key_prefix = raw_key[:9] if len(raw_key) >= 9 else (raw_key if raw_key else "NONE")
            logger.info(f"Razorpay mode: {rzp_mode}")
            logger.info(f"Razorpay key type: {key_type}")
            logger.info(f"Razorpay key prefix: {key_prefix}")
    except Exception as log_err:
        logger.warning(f"Could not log safe Razorpay startup diagnostics: {log_err}")

    yield
    # Shutdown
    logger.info("NAVRANG 2026 Backend shutting down.")

app = FastAPI(
    title="NAVRANG 2026 - Official Ticketing Platform (In Collaboration with THE HAPPY CIRCLE)",
    description="Production-grade full-stack API for NAVRANG 2026 in collaboration with THE HAPPY CIRCLE - event ticket booking, payments, QR generation, validation, and check-in system.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Production Security Headers Middleware
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    if settings.ENVIRONMENT == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# CORS Configuration — includes Custom Domain & Vercel preview/production URLs
origins = [
    settings.FRONTEND_URL,
    "https://www.heritageproduction.online",
    "https://heritageproduction.online",
    "https://garba-event-inky.vercel.app",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Vercel injects VERCEL_URL (without https://) for every deployment
_vercel_url = os.environ.get("VERCEL_URL", "")
if _vercel_url:
    origins.append(f"https://{_vercel_url}")

# Allow custom extra origins (comma-separated) via env var
_extra = os.environ.get("EXTRA_CORS_ORIGINS", "")
if _extra:
    origins.extend([u.strip() for u in _extra.split(",") if u.strip()])

# De-duplicate and remove empty strings
origins = list(dict.fromkeys(o for o in origins if o))

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"]
)

# Custom Rate Limiter Middleware
app.add_middleware(RateLimitMiddleware)

# Include Routers
app.include_router(auth_router)
app.include_router(booking_router)
app.include_router(payment_router)
app.include_router(ticket_router)
app.include_router(admin_router)
app.include_router(staff_router)
app.include_router(webhook_router)

@app.get("/", tags=["System"])
@app.get("/health", tags=["System"])
@app.get("/api/health", tags=["System"])
def health_check():
    return {
        "status": "healthy",
        "service": "NAVRANG 2026 API",
        "version": "1.0.0"
    }

# Safe Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled server error on {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. Please contact event support if this persists."}
    )
