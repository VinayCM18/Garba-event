from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import os
from contextlib import asynccontextmanager
from sqlalchemy import func

from app.config import settings
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
                event_name="GARBA NIGHT 2026",
                event_tagline="Celebrate. Dance. Connect.",
                event_date="October 20, 2026",
                event_time="07:00 PM - 02:00 AM IST",
                venue_name="Royal Palm Grand Arena",
                venue_address="SG Highway, Near Vaishnodevi Circle",
                venue_city="Ahmedabad, Gujarat",
                ticket_price=599.0,
                convenience_fee=0.0,
                total_capacity=1500,
                max_per_booking=10,
                booking_open=True,
                contact_email="support@garbanight.in",
                contact_phone="+91 98765 43210"
            )
            db.add(setting)

        import warnings

        # Admin and staff seed credentials are read from environment variables.
        # Set these in Vercel → Settings → Environment Variables.
        # In local dev they fall back to insecure defaults — CHANGE in production.
        admin_email  = os.environ.get("ADMIN_EMAIL",  "admin@garbanight.in")
        admin_pass   = os.environ.get("ADMIN_PASSWORD","GarbaNight@2026")
        admin_name   = os.environ.get("ADMIN_NAME",   "Head Organizer (Super Admin)")
        staff_email  = os.environ.get("STAFF_EMAIL",  "staff@garbanight.in")
        staff_pass   = os.environ.get("STAFF_PASSWORD","StaffEntry@2026")
        staff_name   = os.environ.get("STAFF_NAME",   "Gate Security Staff")

        if settings.ENVIRONMENT == "production":
            missing = [k for k, v in {
                "ADMIN_EMAIL": admin_email, "ADMIN_PASSWORD": admin_pass,
                "STAFF_EMAIL": staff_email, "STAFF_PASSWORD": staff_pass,
            }.items() if not v or v in {"GarbaNight@2026", "StaffEntry@2026",
                                        "admin@garbanight.in", "staff@garbanight.in"}]
            if missing:
                warnings.warn(
                    f"SECURITY: Using default seed credentials in production for: {missing}. "
                    "Set these as Vercel environment variables immediately.",
                    stacklevel=2
                )

        seed_accounts = [
            ("vinay18744@gmail.com", "Vinay@1438", "Vinay (Super Admin)", "SUPER_ADMIN"),
            ("samaymadhyastha2005@gmail.com", "Samay@866033", "Samay (Super Admin)", "SUPER_ADMIN"),
            (admin_email, admin_pass, admin_name, "SUPER_ADMIN"),
            (staff_email, staff_pass, staff_name, "CHECKIN_STAFF"),
        ]
        for seed_email, seed_pass, seed_name, seed_role in seed_accounts:
            existing = db.query(User).filter(func.lower(User.email) == seed_email.lower()).first()
            if not existing:
                new_user = User(
                    email=seed_email.lower(),
                    name=seed_name,
                    password_hash=get_password_hash(seed_pass),
                    role=seed_role,
                    is_active=True
                )
                db.add(new_user)
            else:
                existing.name = seed_name
                existing.password_hash = get_password_hash(seed_pass)
                existing.role = seed_role
                existing.is_active = True

        db.commit()
    except Exception as e:
        logger.error(f"Error seeding default database records: {e}")
        db.rollback()
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing Garba Night 2026 Backend...")
    init_db_defaults()
    yield
    # Shutdown
    logger.info("Garba Night 2026 Backend shutting down.")

app = FastAPI(
    title="GARBA NIGHT 2026 - Event Ticketing & QR Verification Platform",
    description="Production-grade full-stack API for Garba Night 2026 event ticket booking, payments, QR generation, validation, and check-in system.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS Configuration — includes Vercel preview/production URLs automatically
origins = [
    settings.FRONTEND_URL,
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
        "service": "Garba Night 2026 API",
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
