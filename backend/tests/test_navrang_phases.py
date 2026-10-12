import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from fastapi.testclient import TestClient
from app.main import app, init_db_defaults

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    init_db_defaults()

client = TestClient(app)

def test_public_config_navrang_branding_and_phases():
    """Verify that public config returns NAVRANG branding and configured phases."""
    response = client.get("/api/bookings/public-config")
    assert response.status_code == 200
    data = response.json()
    assert "NAVRANG" in data["event_name"]
    assert data["collaboration_name"] == "THE HAPPY CIRCLE"
    assert "/images/happy-circle-logo.png" in data["collaboration_logo_url"]
    assert "ticket_phases" in data
    phases = {p["phase_code"]: p for p in data["ticket_phases"]}
    assert "EARLY_BIRD" in phases
    assert phases["EARLY_BIRD"]["status"] == "SOLD_OUT"
    assert phases["EARLY_BIRD"]["price"] == 599.0
    assert "PHASE_1" in phases
    assert phases["PHASE_1"]["status"] == "ACTIVE"
    assert phases["PHASE_1"]["price"] == 799.0

def test_early_bird_sold_out_calculation_rejected():
    """Attempting to calculate pricing for sold out EARLY_BIRD must return 400 Bad Request."""
    response = client.get("/api/payments/calculate", params={
        "ticket_count": 1,
        "ticket_phase": "EARLY_BIRD"
    })
    assert response.status_code == 400
    assert "Early Bird tickets are sold out. Please select Phase 1." in response.json()["detail"]

def test_phase_1_calculation_active():
    """Pricing calculation for active PHASE_1 must return 200 OK and ₹799.0."""
    response = client.get("/api/payments/calculate", params={
        "ticket_count": 1,
        "ticket_phase": "PHASE_1"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["ticket_price"] == 799.0
    assert data["total_amount"] in (799.0, 817.86)
    assert data["ticket_phase"] == "PHASE_1"

def test_early_bird_order_creation_rejected():
    """Attempting to initiate an order for sold out EARLY_BIRD must return 400 Bad Request."""
    response = client.post("/api/payments/create-order", json={
        "customer_name": "Test Attendee",
        "email": "testattendee@example.com",
        "phone": "+91 99999 88888",
        "ticket_count": 1,
        "ticket_phase": "EARLY_BIRD"
    })
    assert response.status_code == 400
    assert "Early Bird tickets are sold out. Please select Phase 1." in response.json()["detail"]
