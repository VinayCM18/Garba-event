from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from contextlib import asynccontextmanager

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
                ticket_price=300.0,
                convenience_fee=0.0,
                total_capacity=1500,
                max_per_booking=10,
                booking_open=True,
                contact_email="support@garbanight.in",
                contact_phone="+91 98765 43210"
            )
            db.add(setting)

        from sqlalchemy import func
        # Seed super admins (.in, .local and primary admin)
        for admin_email, admin_pass, admin_name in [
            ("vinay18744@gmail.com", "Vinay@1438", "Vinay (Admin)"),
            ("admin@garbanight.in", "GarbaNight@2026", "Head Organizer (Super Admin)"),
            ("admin@garbanight.local", "GarbaNight@2026", "Head Organizer (Super Admin)")
        ]:
            admin_user = db.query(User).filter(func.lower(User.email) == admin_email.lower()).first()
            if not admin_user:
                admin_user = User(
                    email=admin_email.lower(),
                    name=admin_name,
                    password_hash=get_password_hash(admin_pass),
                    role="SUPER_ADMIN",
                    is_active=True
                )
                db.add(admin_user)
            else:
                admin_user.password_hash = get_password_hash(admin_pass)
                admin_user.role = "SUPER_ADMIN"
                admin_user.is_active = True

        # Seed staff users (.in, .local and primary staff)
        for staff_email, staff_pass, staff_name in [
            ("samaymadhyastha2005@gmail.com", "Samay@866033", "Samay Madhyastha (Staff)"),
            ("staff@garbanight.in", "StaffEntry@2026", "Gate Security Staff"),
            ("staff@garbanight.local", "StaffEntry@2026", "Gate Security Staff")
        ]:
            staff_user = db.query(User).filter(func.lower(User.email) == staff_email.lower()).first()
            if not staff_user:
                staff_user = User(
                    email=staff_email,
                    name=staff_name,
                    password_hash=get_password_hash(staff_pass),
                    role="CHECKIN_STAFF",
                    is_active=True
                )
                db.add(staff_user)
            else:
                staff_user.password_hash = get_password_hash(staff_pass)
                staff_user.role = "CHECKIN_STAFF"
                staff_user.is_active = True

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

# CORS Configuration
origins = [
    settings.FRONTEND_URL,
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
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
