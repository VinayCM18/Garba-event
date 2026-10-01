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
        "type": "STAG",
        "default_phase_status": "ACTIVE",
        "title": "Stag Entry",
        "full_title": "Early Bird — Stag Entry",
        "badge": "EARLY BIRD",
        "description": "Single person entry.",
        "passes_per_unit": 1,
        "price_per_unit": 599.0,
        "unit_name": "Pass",
        "is_kids": False,
        "requires_id_proof": False,
        "display_order": 1,
    },
    "EARLY_BIRD_GROUP_10": {
        "id": "EARLY_BIRD_GROUP_10",
        "phase_code": "EARLY_BIRD",
        "phase_name": "EARLY BIRD",
        "type": "GROUP",
        "default_phase_status": "ACTIVE",
        "title": "Group of 10",
        "full_title": "Early Bird — Group of 10",
        "badge": "BEST VALUE • SAVE ₹991",
        "description": "Entry for 10 people. Save ₹991 versus 10 individual passes.",
        "passes_per_unit": 10,
        "price_per_unit": 4999.0,
        "unit_name": "Group Pass (10 People)",
        "is_kids": False,
        "requires_id_proof": False,
        "display_order": 2,
    },
    "EARLY_BIRD_COUPLE": {
        "id": "EARLY_BIRD_COUPLE",
        "phase_code": "EARLY_BIRD",
        "phase_name": "EARLY BIRD",
        "type": "COUPLE",
        "default_phase_status": "ACTIVE",
        "title": "Couple Entry",
        "full_title": "Early Bird — Couple Entry",
        "badge": "POPULAR",
        "description": "Entry for 2 people.",
        "passes_per_unit": 2,
        "price_per_unit": 999.0,
        "unit_name": "Couple Pass",
        "is_kids": False,
        "requires_id_proof": False,
        "display_order": 3,
    },
    "PHASE_1_STAG": {
        "id": "PHASE_1_STAG",
        "phase_code": "PHASE_1",
        "phase_name": "PHASE 1",
        "type": "STAG",
        "default_phase_status": "LOCKED",
        "title": "Stag Entry",
        "full_title": "Phase 1 — Stag Entry",
        "badge": "COMING SOON",
        "description": "Single person entry.",
        "passes_per_unit": 1,
        "price_per_unit": 799.0,
        "unit_name": "Pass",
        "is_kids": False,
        "requires_id_proof": False,
        "display_order": 4,
    },
    "PHASE_1_GROUP_10": {
        "id": "PHASE_1_GROUP_10",
        "phase_code": "PHASE_1",
        "phase_name": "PHASE 1",
        "type": "GROUP",
        "default_phase_status": "LOCKED",
        "title": "Group of 10",
        "full_title": "Phase 1 — Group of 10",
        "badge": "COMING SOON",
        "description": "Entry for 10 people.",
        "passes_per_unit": 10,
        "price_per_unit": 6799.0,
        "unit_name": "Group Pass (10 People)",
        "is_kids": False,
        "requires_id_proof": False,
        "display_order": 5,
    },
    "PHASE_1_COUPLE": {
        "id": "PHASE_1_COUPLE",
        "phase_code": "PHASE_1",
        "phase_name": "PHASE 1",
        "type": "COUPLE",
        "default_phase_status": "LOCKED",
        "title": "Couple Entry",
        "full_title": "Phase 1 — Couple Entry",
        "badge": "COMING SOON",
        "description": "Entry for 2 people.",
        "passes_per_unit": 2,
        "price_per_unit": 1399.0,
        "unit_name": "Couple Pass",
        "is_kids": False,
        "requires_id_proof": False,
        "display_order": 6,
    },
    "KIDS_5_12": {
        "id": "KIDS_5_12",
        "phase_code": "ALL",
        "phase_name": "KIDS (5–12)",
        "type": "KIDS",
        "default_phase_status": "ACTIVE",
        "title": "Kids (5–12 years)",
        "full_title": "Kids (5–12 years) — Entry",
        "badge": "KIDS PASS",
        "description": "Entry for child aged 5–12. Aadhaar card / valid ID proof required at entry.",
        "passes_per_unit": 1,
        "price_per_unit": 300.0,
        "unit_name": "Child Pass",
        "is_kids": True,
        "requires_id_proof": True,
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
    """Returns all configured offers with authoritative schema including type, phase_status, and per_unit_passes."""
    phases = db.query(TicketPhase).all() if db else []
    phase_status_map = {p.phase_code: p.status for p in phases}

    event_setting = db.query(EventSetting).first() if db else None
    booking_open = event_setting.booking_open if event_setting else True

    offers_list = []
    for offer in sorted(OFFER_DEFINITIONS.values(), key=lambda o: o["display_order"]):
        phase_code = offer["phase_code"]
        if phase_code == "ALL":
            phase_status = "ACTIVE" if booking_open else "LOCKED"
        else:
            db_status = phase_status_map.get(phase_code)
            if db_status in ("ACTIVE", "LOCKED", "COMING_SOON"):
                phase_status = db_status
            else:
                phase_status = offer.get("default_phase_status", "LOCKED")
            
            if not booking_open and phase_status == "ACTIVE":
                phase_status = "LOCKED"

        is_purchasable = (phase_status == "ACTIVE") and booking_open
        status_text = "AVAILABLE NOW" if is_purchasable else ("COMING SOON" if phase_status == "COMING_SOON" else "LOCKED")

        offers_list.append({
            "id": offer["id"],
            "phase_code": offer["phase_code"],
            "phase_name": offer["phase_name"],
            "phase_status": phase_status,
            "type": offer["type"],
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
            "is_active": is_purchasable,
            "is_purchasable": is_purchasable,
            "requires_id_proof": bool(offer.get("requires_id_proof", False)),
            "status_text": status_text,
        })

    return offers_list

def calculate_cart_pricing(items: List[Dict[str, Any]], db: Session = None) -> Dict[str, Any]:
    """
    Authoritative server-side price calculation for a cart of multiple offer items.
    The frontend cannot modify or manipulate prices.
    Never accepts frontend prices or totals.
    """
    if not items or len(items) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cart cannot be empty. Please select at least one ticket offer."
        )

    # Cache phase statuses
    phases = db.query(TicketPhase).all() if db else []
    phase_status_map = {p.phase_code: p.status for p in phases}

    event_setting = db.query(EventSetting).first() if db else None
    booking_open = event_setting.booking_open if event_setting else True
    if not booking_open:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ticket booking is currently closed."
        )

    calculated_items: List[Dict[str, Any]] = []
    total_passes = 0
    total_amount = 0.0
    kids_count = 0
    has_group = False

    for entry in items:
        # Support dict or pydantic model
        if hasattr(entry, "offer_id"):
            raw_id = entry.offer_id
            raw_qty = getattr(entry, "quantity", 1)
        elif isinstance(entry, dict):
            raw_id = entry.get("offer_id") or entry.get("id")
            raw_qty = entry.get("quantity", 1)
        else:
            continue

        if not raw_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing offer_id in cart item."
            )

        offer = get_offer_by_id(raw_id)
        if not offer:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown or invalid offer ID '{raw_id}'."
            )

        try:
            qty = int(raw_qty)
            if qty < 1:
                raise ValueError()
            if qty > 50:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Maximum 50 units allowed per offer in a single cart. Requested {qty} for {offer['title']}."
                )
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid quantity '{raw_qty}' for offer '{offer['title']}'. Must be a positive integer."
            )

        # Check phase status
        phase_code = offer["phase_code"]
        phase_name = offer["phase_name"]
        if phase_code != "ALL":
            phase_status = phase_status_map.get(phase_code, offer.get("default_phase_status", "LOCKED"))
            if phase_status != "ACTIVE":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Ticket phase '{phase_name}' ({offer['full_title']}) is currently {phase_status.lower()} and cannot be purchased."
                )

        price_per_unit = float(offer["price_per_unit"])
        passes_per_unit = int(offer["passes_per_unit"])
        line_total = round(price_per_unit * qty, 2)
        item_passes = passes_per_unit * qty

        if offer.get("is_kids"):
            kids_count += qty
        if offer["id"] in ("EARLY_BIRD_GROUP_10", "PHASE_1_GROUP_10"):
            has_group = True

        calculated_items.append({
            "offer_id": offer["id"],
            "offer_title": offer["full_title"],
            "phase_code": phase_code,
            "phase_name": phase_name,
            "quantity": qty,
            "passes_per_unit": passes_per_unit,
            "total_passes": item_passes,
            "unit_price": price_per_unit,
            "line_total": line_total,
            "unit_name": offer.get("unit_name", "Pass"),
            "is_kids": bool(offer.get("is_kids", False)),
            "requires_id_proof": bool(offer.get("requires_id_proof", False)),
            "id_proof_note": offer.get("id_proof_note")
        })

        total_passes += item_passes
        total_amount += line_total

    total_amount = round(total_amount, 2)
    per_pass_price = round(total_amount / total_passes, 2) if total_passes > 0 else 599.0

    primary_item = calculated_items[0] if calculated_items else {}
    is_mixed = len(calculated_items) > 1

    return {
        "items": calculated_items,
        "total_amount": total_amount,
        "amount": total_amount,
        "ticket_subtotal": total_amount,
        "regular_amount": total_amount,
        "group_discount": 0.0,
        "payment_fee": 0.0,
        "gst_amount": 0.0,
        "tax_amount": 0.0,
        "base_amount": total_amount,
        "tax_rate": 0.0,
        "tax_included": True,
        "tax_label": "Taxes included",
        "currency": "INR",
        "total_passes": total_passes,
        "ticket_count": total_passes,
        "ticket_price": per_pass_price,
        "passes_count": total_passes,
        "kids_count": kids_count,
        "is_group_offer": has_group,
        "is_mixed_cart": is_mixed,
        # Legacy/single-offer fields for backward compatibility
        "offer_id": primary_item.get("offer_id") if not is_mixed else "MIXED_CART",
        "offer_title": primary_item.get("offer_title") if not is_mixed else f"Mixed Cart ({total_passes} Passes)",
        "offer_name": primary_item.get("offer_title") if not is_mixed else f"Mixed Cart ({total_passes} Passes)",
        "ticket_phase": primary_item.get("phase_code") if not is_mixed else "EARLY_BIRD",
        "phase_name": primary_item.get("phase_name") if not is_mixed else "Early Bird",
        "unit_count": primary_item.get("quantity") if not is_mixed else len(calculated_items),
        "unit_price": primary_item.get("unit_price") if not is_mixed else per_pass_price,
        "is_kids": (kids_count > 0),
        "id_proof_note": "Aadhaar card / valid ID proof required at entry." if (kids_count > 0) else None
    }

def calculate_offer_pricing(offer_id: str, quantity: int = 1, db: Session = None) -> Dict[str, Any]:
    """
    Authoritative server-side price calculation for a single selected offer.
    Delegates to calculate_cart_pricing to maintain single source of truth.
    """
    return calculate_cart_pricing(
        items=[{"offer_id": offer_id, "quantity": quantity or 1}],
        db=db
    )
