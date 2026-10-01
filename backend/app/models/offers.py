from typing import Dict, Any, List, Optional
import os
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.config import settings
from app.models.ticket_phase import TicketPhase
from app.models.event_setting import EventSetting

OFFER_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "EARLY_BIRD_STAG": {
        "id": "EARLY_BIRD_STAG",
        "phase_code": "EARLY_BIRD",
        "phase_name": "EARLY BIRD",
        "title": "Stag Entry",
        "full_title": "Early Bird — Stag Entry",
        "badge": "EARLY BIRD",
        "description": "Single person entry.",
        "passes_per_unit": 1,
        "price_per_unit": 599.0,
        "unit_name": "Pass",
        "is_kids": False,
        "display_order": 1,
    },
    "EARLY_BIRD_GROUP_10": {
        "id": "EARLY_BIRD_GROUP_10",
        "phase_code": "EARLY_BIRD",
        "phase_name": "EARLY BIRD",
        "title": "Group of 10",
        "full_title": "Early Bird — Group of 10",
        "badge": "BEST VALUE",
        "description": "Entry for 10 people.",
        "passes_per_unit": 10,
        "price_per_unit": 4999.0,
        "unit_name": "Group Pass (10 People)",
        "is_kids": False,
        "display_order": 2,
    },
    "EARLY_BIRD_COUPLE": {
        "id": "EARLY_BIRD_COUPLE",
        "phase_code": "EARLY_BIRD",
        "phase_name": "EARLY BIRD",
        "title": "Couple Entry",
        "full_title": "Early Bird — Couple Entry",
        "badge": "POPULAR",
        "description": "Entry for 2 people.",
        "passes_per_unit": 2,
        "price_per_unit": 999.0,
        "unit_name": "Couple Pass",
        "is_kids": False,
        "display_order": 3,
    },
    "PHASE_1_STAG": {
        "id": "PHASE_1_STAG",
        "phase_code": "PHASE_1",
        "phase_name": "PHASE 1",
        "title": "Stag Entry",
        "full_title": "Phase 1 — Stag Entry",
        "badge": "PHASE 1",
        "description": "Single person entry.",
        "passes_per_unit": 1,
        "price_per_unit": 799.0,
        "unit_name": "Pass",
        "is_kids": False,
        "display_order": 4,
    },
    "PHASE_1_GROUP_10": {
        "id": "PHASE_1_GROUP_10",
        "phase_code": "PHASE_1",
        "phase_name": "PHASE 1",
        "title": "Group of 10",
        "full_title": "Phase 1 — Group of 10",
        "badge": "GROUP OFFER",
        "description": "Entry for 10 people.",
        "passes_per_unit": 10,
        "price_per_unit": 6799.0,
        "unit_name": "Group Pass (10 People)",
        "is_kids": False,
        "display_order": 5,
    },
    "PHASE_1_COUPLE": {
        "id": "PHASE_1_COUPLE",
        "phase_code": "PHASE_1",
        "phase_name": "PHASE 1",
        "title": "Couple Entry",
        "full_title": "Phase 1 — Couple Entry",
        "badge": "PHASE 1",
        "description": "Entry for 2 people.",
        "passes_per_unit": 2,
        "price_per_unit": 1399.0,
        "unit_name": "Couple Pass",
        "is_kids": False,
        "display_order": 6,
    },
    "KIDS_5_12": {
        "id": "KIDS_5_12",
        "phase_code": "ALL",
        "phase_name": "KIDS (5–12)",
        "title": "Kids (5–12 years)",
        "full_title": "Kids (5–12 years) — Entry",
        "badge": "KIDS PASS",
        "description": "Entry for child aged 5–12. Aadhaar card / valid ID proof required at entry.",
        "passes_per_unit": 1,
        "price_per_unit": 300.0,
        "unit_name": "Child Pass",
        "is_kids": True,
        "id_proof_note": "Aadhaar card / valid ID proof required at entry.",
        "display_order": 7,
    },
}

def get_offer_by_id(offer_id: str) -> Optional[Dict[str, Any]]:
    if not offer_id:
        return None
    normalized_id = offer_id.strip().upper()
    return OFFER_DEFINITIONS.get(normalized_id)

def get_all_offers(db: Session) -> List[Dict[str, Any]]:
    """Returns all configured offers with their live active/locked status based on ticket_phases."""
    # Look up phase statuses
    phases = db.query(TicketPhase).all() if db else []
    phase_status_map = {p.phase_code: p.status for p in phases}

    event_setting = db.query(EventSetting).first() if db else None
    booking_open = event_setting.booking_open if event_setting else True

    offers_list = []
    for offer in sorted(OFFER_DEFINITIONS.values(), key=lambda o: o["display_order"]):
        phase_code = offer["phase_code"]
        if phase_code == "ALL":
            is_active = booking_open
            status_text = "AVAILABLE NOW" if is_active else "CLOSED"
        else:
            p_status = phase_status_map.get(phase_code, "LOCKED" if phase_code != "EARLY_BIRD" else "ACTIVE")
            is_active = (p_status == "ACTIVE") and booking_open
            status_text = "AVAILABLE NOW" if is_active else "COMING SOON"

        offers_list.append({
            "id": offer["id"],
            "phase_code": offer["phase_code"],
            "phase_name": offer["phase_name"],
            "title": offer["title"],
            "full_title": offer["full_title"],
            "badge": offer["badge"],
            "description": offer["description"],
            "passes_per_unit": offer["passes_per_unit"],
            "per_unit_passes": offer["passes_per_unit"],
            "price": offer["price_per_unit"],
            "price_per_unit": offer["price_per_unit"],
            "unit_name": offer["unit_name"],
            "is_kids": offer["is_kids"],
            "id_proof_note": offer.get("id_proof_note"),
            "is_active": is_active,
            "is_purchasable": is_active,
            "requires_id_proof": offer["is_kids"],
            "status_text": status_text,
        })

    return offers_list

def calculate_offer_pricing(offer_id: str, quantity: int = 1, db: Session = None) -> Dict[str, Any]:
    """
    Authoritative server-side price calculation for a selected offer.
    The frontend cannot modify or manipulate the price.
    """
    offer = get_offer_by_id(offer_id)
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown or invalid offer ID '{offer_id}'."
        )

    qty = max(1, quantity)

    # Check phase status if tied to a specific phase
    phase_code = offer["phase_code"]
    phase_name = offer["phase_name"]
    if phase_code != "ALL" and db:
        phase = db.query(TicketPhase).filter(TicketPhase.phase_code == phase_code).first()
        if phase and phase.status != "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ticket phase '{phase.name}' is currently {phase.status.lower()} and cannot be purchased."
            )

    passes_count = offer["passes_per_unit"] * qty
    price_per_unit = float(offer["price_per_unit"])
    ticket_subtotal = round(price_per_unit * qty, 2)

    # NAVRANG 2026 ticket prices are strictly all-inclusive.
    # No extra tax or gateway fee is added to the customer (599 is strictly 599).
    payment_fee = 0.0
    gst_amount = 0.0
    tax_amount = 0.0
    total_amount = ticket_subtotal

    # Effective per-pass ticket price stored in db
    per_pass_price = round(ticket_subtotal / passes_count, 2) if passes_count > 0 else price_per_unit

    return {
        "offer_id": offer["id"],
        "offer_title": offer["full_title"],
        "ticket_phase": phase_code if phase_code != "ALL" else "EARLY_BIRD",
        "phase_name": phase_name,
        "unit_count": qty,
        "passes_count": passes_count,
        "ticket_count": passes_count,
        "unit_price": price_per_unit,
        "ticket_price": per_pass_price,
        "regular_amount": ticket_subtotal,
        "group_discount": 0.0,
        "ticket_subtotal": ticket_subtotal,
        "payment_fee": payment_fee,
        "gst_amount": gst_amount,
        "tax_amount": gst_amount,
        "base_amount": ticket_subtotal,
        "tax_rate": 0.0,
        "tax_included": True,
        "tax_label": "Taxes included",
        "total_amount": total_amount,
        "currency": "INR",
        "is_group_offer": offer["id"] in ("EARLY_BIRD_GROUP_10", "PHASE_1_GROUP_10"),
        "offer_name": offer["full_title"],
        "is_kids": offer["is_kids"],
        "id_proof_note": offer.get("id_proof_note")
    }
