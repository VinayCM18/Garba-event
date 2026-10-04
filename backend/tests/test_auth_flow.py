import pytest
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal, get_db
from app.models.user import User
from app.utils.security import create_access_token, get_password_hash
from app.config import settings

client = TestClient(app)

@pytest.fixture(scope="module")
def setup_auth_users():
    db = SessionLocal()
    # Ensure super admin exists
    admin_user = db.query(User).filter(User.email == "test_admin@garbanight.in").first()
    if not admin_user:
        admin_user = User(
            email="test_admin@garbanight.in",
            name="Test Admin",
            password_hash=get_password_hash("AdminPass12345!"),
            role="ADMIN",
            is_active=True
        )
        db.add(admin_user)

    # Ensure staff user exists
    staff_user = db.query(User).filter(User.email == "test_staff@garbanight.in").first()
    if not staff_user:
        staff_user = User(
            email="test_staff@garbanight.in",
            name="Test Staff",
            password_hash=get_password_hash("StaffPass12345!"),
            role="CHECKIN_STAFF",
            is_active=True
        )
        db.add(staff_user)

    # Ensure disabled user exists
    disabled_user = db.query(User).filter(User.email == "test_disabled@garbanight.in").first()
    if not disabled_user:
        disabled_user = User(
            email="test_disabled@garbanight.in",
            name="Disabled User",
            password_hash=get_password_hash("DisabledPass12345!"),
            role="ADMIN",
            is_active=False
        )
        db.add(disabled_user)

    db.commit()
    db.refresh(admin_user)
    db.refresh(staff_user)
    db.refresh(disabled_user)
    
    admin_id = admin_user.id
    staff_id = staff_user.id
    disabled_id = disabled_user.id
    db.close()
    
    return {
        "admin_id": admin_id,
        "admin_email": "test_admin@garbanight.in",
        "staff_id": staff_id,
        "staff_email": "test_staff@garbanight.in",
        "disabled_id": disabled_id,
        "disabled_email": "test_disabled@garbanight.in",
    }


def test_admin_login_success(setup_auth_users):
    """1 & 2: Admin login succeeds and returns valid access token."""
    res = client.post("/api/auth/login", json={
        "email": setup_auth_users["admin_email"],
        "password": "AdminPass12345!"
    })
    assert res.status_code == 200, res.text
    data = res.json()
    assert "access_token" in data
    assert data["role"] in ("ADMIN", "SUPER_ADMIN")
    assert data["email"] == setup_auth_users["admin_email"]
    # Verify cookie is set
    assert "admin_access_token" in res.cookies


def test_disabled_user_login_fails(setup_auth_users):
    """Disabled user account cannot log in."""
    res = client.post("/api/auth/login", json={
        "email": setup_auth_users["disabled_email"],
        "password": "DisabledPass12345!"
    })
    assert res.status_code == 403
    assert "disabled" in res.json().get("detail", "").lower()


def test_missing_token_returns_401():
    """5: Missing token returns 401 Unauthorized across admin endpoints."""
    unauth_client = TestClient(app)
    unauth_client.cookies.clear()
    endpoints = [
        "/api/admin/analytics",
        "/api/admin/checkins?limit=6",
        "/api/admin/notifications/recent?limit=6",
        "/api/admin/ticket-phases",
        "/api/admin/payments/verification?status=VERIFICATION_PENDING",
    ]
    for ep in endpoints:
        res = unauth_client.get(ep)
        assert res.status_code == 401, f"Expected 401 on {ep}, got {res.status_code}"
        assert "Authentication required" in res.json().get("detail", "")


def test_invalid_token_returns_401():
    """6: Invalid or malformed token returns 401."""
    headers = {"Authorization": "Bearer invalid_garbage_token_string"}
    res = client.get("/api/admin/analytics", headers=headers)
    assert res.status_code == 401
    assert "Invalid or expired" in res.json().get("detail", "")


def test_expired_token_returns_401(setup_auth_users):
    """7: Expired token returns 401."""
    expired_token = create_access_token(
        data={"sub": str(setup_auth_users["admin_id"]), "email": setup_auth_users["admin_email"], "role": "ADMIN"},
        expires_delta=timedelta(seconds=-10)
    )
    headers = {"Authorization": f"Bearer {expired_token}"}
    res = client.get("/api/admin/analytics", headers=headers)
    assert res.status_code == 401
    assert "Invalid or expired" in res.json().get("detail", "")


def test_admin_token_returns_200_on_all_admin_endpoints(setup_auth_users):
    """4 & 8: Correct ADMIN token returns 200 on all observed admin endpoints."""
    token = create_access_token(
        data={"sub": str(setup_auth_users["admin_id"]), "email": setup_auth_users["admin_email"], "role": "ADMIN"},
        expires_delta=timedelta(minutes=60)
    )
    headers = {"Authorization": f"Bearer {token}"}

    endpoints = [
        "/api/admin/analytics",
        "/api/admin/checkins?limit=6",
        "/api/admin/notifications/recent?limit=6",
        "/api/admin/ticket-phases",
        "/api/admin/payments/verification?status=VERIFICATION_PENDING",
    ]
    for ep in endpoints:
        res = client.get(ep, headers=headers)
        assert res.status_code == 200, f"Expected 200 on {ep}, got {res.status_code} with body: {res.text}"


def test_staff_cannot_access_admin_endpoints(setup_auth_users):
    """9: STAFF role cannot access ADMIN-only endpoints (returns 403 Forbidden)."""
    staff_token = create_access_token(
        data={"sub": str(setup_auth_users["staff_id"]), "email": setup_auth_users["staff_email"], "role": "CHECKIN_STAFF"},
        expires_delta=timedelta(minutes=60)
    )
    headers = {"Authorization": f"Bearer {staff_token}"}

    endpoints = [
        "/api/admin/analytics",
        "/api/admin/ticket-phases",
        "/api/admin/payments/verification",
    ]
    for ep in endpoints:
        res = client.get(ep, headers=headers)
        assert res.status_code == 403, f"Expected 403 on {ep} for STAFF, got {res.status_code}"


def test_logout_with_valid_token_succeeds(setup_auth_users):
    """10: Logout with valid token succeeds (both POST and GET)."""
    token = create_access_token(
        data={"sub": str(setup_auth_users["admin_id"]), "email": setup_auth_users["admin_email"], "role": "ADMIN"},
        expires_delta=timedelta(minutes=60)
    )
    headers = {"Authorization": f"Bearer {token}"}
    
    # POST /api/auth/logout
    res_post = client.post("/api/auth/logout", headers=headers)
    assert res_post.status_code == 200
    assert "logged out" in res_post.json().get("message", "").lower()

    # GET /api/auth/logout
    res_get = client.get("/api/auth/logout", headers=headers)
    assert res_get.status_code == 200
    assert "logged out" in res_get.json().get("message", "").lower()


def test_logout_with_expired_token_does_not_fail(setup_auth_users):
    """11: Expired-token logout does NOT return 401; gracefully returns 200 and clears session."""
    expired_token = create_access_token(
        data={"sub": str(setup_auth_users["admin_id"]), "email": setup_auth_users["admin_email"], "role": "ADMIN"},
        expires_delta=timedelta(seconds=-10)
    )
    headers = {"Authorization": f"Bearer {expired_token}"}
    
    res = client.post("/api/auth/logout", headers=headers)
    assert res.status_code == 200
    assert "logged out" in res.json().get("message", "").lower()

    res_get = client.get("/api/auth/logout", headers=headers)
    assert res_get.status_code == 200


def test_logout_without_token_returns_200():
    """Logout without any token returns 200."""
    res = client.post("/api/auth/logout")
    assert res.status_code == 200
    res_get = client.get("/api/auth/logout")
    assert res_get.status_code == 200


def test_relogin_after_expiration_works(setup_auth_users):
    """12: Re-login after expiration works and generates a working token."""
    res_login = client.post("/api/auth/login", json={
        "email": setup_auth_users["admin_email"],
        "password": "AdminPass12345!"
    })
    assert res_login.status_code == 200
    new_token = res_login.json()["access_token"]
    
    # Immediately make an admin API call
    res_analytics = client.get("/api/admin/analytics", headers={"Authorization": f"Bearer {new_token}"})
    assert res_analytics.status_code == 200
