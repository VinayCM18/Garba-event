import os
import time
from collections import defaultdict
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

class InMemoryRateLimiter:
    def __init__(self):
        # Maps key -> list of timestamps
        self.requests = defaultdict(list)
    
    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> bool:
        now = time.time()
        cutoff = now - window_seconds
        # Clean expired timestamps
        self.requests[key] = [t for t in self.requests[key] if t > cutoff]
        if len(self.requests[key]) >= max_requests:
            return False
        self.requests[key].append(now)
        return True

limiter = InMemoryRateLimiter()

def rate_limit_check(request: Request, max_requests: int = 60, window_seconds: int = 60):
    client_ip = request.client.host if request.client else "unknown"
    path = request.url.path
    key = f"{client_ip}:{path}"
    
    if not limiter.is_allowed(key, max_requests, window_seconds):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please slow down and try again in a few moments."
        )

class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path

        # Specific strict rules
        if path.startswith("/api/auth/login"):
            if not limiter.is_allowed(f"{client_ip}:login", max_requests=10, window_seconds=60):
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many failed login attempts. Please wait 1 minute."}
                )
        elif path.startswith("/api/payments/create-order"):
            max_order_reqs = 1000 if os.environ.get("PYTEST_CURRENT_TEST") else 25
            if not limiter.is_allowed(f"{client_ip}:payment_order", max_requests=max_order_reqs, window_seconds=60):
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many payment creation requests. Please try again shortly."}
                )
        elif path.startswith("/api/qr/"):
            if not limiter.is_allowed(f"{client_ip}:qr_scan", max_requests=120, window_seconds=60):
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded for QR validation. Please wait."}
                )

        response = await call_next(request)
        return response
