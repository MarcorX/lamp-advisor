"""
Rule-based lamp filtering engine.
Given project details, returns candidate lamps grouped into 1–3 proposal tiers.
"""
from sqlalchemy.orm import Session
from database import Lamp


LEVEL_ORDER = {"basic": 0, "mid": 1, "premium": 2, "luxury": 3}

# Which lamp levels to include per project level
LEVEL_SCOPE = {
    "basic":   ["basic"],
    "mid":     ["basic", "mid"],
    "premium": ["mid", "premium"],
    "luxury":  ["premium", "luxury"],
}

# Recommended color temps by space type
SPACE_COLOR_TEMP = {
    "living":    ["2700K", "3000K"],
    "sala":      ["2700K", "3000K"],
    "bedroom":   ["2700K", "3000K"],
    "dormitorio":["2700K", "3000K"],
    "kitchen":   ["3000K", "4000K"],
    "cocina":    ["3000K", "4000K"],
    "bathroom":  ["3000K", "4000K"],
    "office":    ["4000K", "5000K"],
    "oficina":   ["4000K", "5000K"],
    "lobby":     ["3000K", "4000K"],
    "retail":    ["3000K", "4000K"],
    "restaurant":["2700K", "3000K"],
    "hotel":     ["2700K", "3000K"],
    "default":   ["3000K", "4000K"],
}

# Recommended categories by space type
SPACE_CATEGORIES = {
    "living":     ["pendant", "floor", "wall", "spot", "downlight"],
    "bedroom":    ["pendant", "wall", "spot", "downlight", "strip"],
    "kitchen":    ["panel", "downlight", "strip", "track"],
    "bathroom":   ["downlight", "wall", "mirror"],
    "office":     ["panel", "track", "downlight"],
    "lobby":      ["pendant", "wall", "downlight", "floor"],
    "retail":     ["track", "spot", "strip"],
    "restaurant": ["pendant", "wall", "strip", "floor"],
    "hotel":      ["pendant", "wall", "downlight", "floor"],
    "default":    ["downlight", "spot", "panel"],
}


def get_recommendations(db: Session, project: dict, num_proposals: int = 3) -> list[dict]:
    """
    Returns a list of proposal dicts, each containing a list of recommended lamps
    with quantities and room assignments.
    """
    property_level = project.get("property_level", "mid")
    property_type  = project.get("property_type", "residential")
    total_sqm      = float(project.get("total_sqm") or 80)
    rooms          = project.get("rooms") or ["living", "bedroom", "kitchen", "bathroom"]
    budget_usd     = project.get("budget_usd")
    indoor_outdoor = project.get("indoor_outdoor", "indoor")

    allowed_levels = LEVEL_SCOPE.get(property_level, ["mid"])

    # --- Fetch matching lamps from DB ---
    query = db.query(Lamp).filter(Lamp.property_level.in_(allowed_levels))
    if indoor_outdoor == "indoor":
        query = query.filter(Lamp.indoor_outdoor.in_(["indoor", "both"]))
    elif indoor_outdoor == "outdoor":
        query = query.filter(Lamp.indoor_outdoor.in_(["outdoor", "both"]))

    all_lamps = query.all()

    if not all_lamps:
        return []

    proposals = []

    # Build tier definitions
    tiers = _build_tiers(property_level, num_proposals)

    for tier_idx, tier in enumerate(tiers):
        tier_levels = tier["levels"]
        tier_lamps = [l for l in all_lamps if l.property_level in tier_levels]
        if not tier_lamps:
            tier_lamps = all_lamps  # fallback

        room_assignments = []
        total_price = 0.0

        for room in rooms:
            room_norm = _normalize_room(room)
            preferred_temps = SPACE_COLOR_TEMP.get(room_norm, SPACE_COLOR_TEMP["default"])
            preferred_cats  = SPACE_CATEGORIES.get(room_norm, SPACE_CATEGORIES["default"])

            # Score each lamp for this room
            scored = []
            for lamp in tier_lamps:
                score = _score_lamp(lamp, preferred_temps, preferred_cats)
                scored.append((score, lamp))
            scored.sort(key=lambda x: -x[0])

            # Pick top lamp for this room
            if scored:
                _, best = scored[0]
                sqm_room = _estimate_room_sqm(room_norm, total_sqm, len(rooms))
                qty = _estimate_quantity(best, sqm_room)
                subtotal = (best.price_usd or 0) * qty
                total_price += subtotal

                room_assignments.append({
                    "room": room,
                    "lamp_id": best.id,
                    "lamp_brand": best.brand,
                    "lamp_model": best.model,
                    "lamp_category": best.category,
                    "lamp_wattage": best.wattage,
                    "lamp_lumens": best.lumens,
                    "lamp_color_temp": best.color_temp,
                    "lamp_cri": best.cri,
                    "lamp_dimmable": best.dimmable,
                    "lamp_ip": best.ip_rating,
                    "lamp_price": best.price_usd,
                    "quantity": qty,
                    "subtotal": round(subtotal, 2),
                })

        proposals.append({
            "proposal_number": tier_idx + 1,
            "title": tier["title"],
            "tier_label": tier["label"],
            "room_assignments": room_assignments,
            "total_price": round(total_price, 2),
        })

    return proposals


def _build_tiers(property_level: str, num_proposals: int) -> list[dict]:
    level_idx = LEVEL_ORDER.get(property_level, 1)
    tiers = [
        {"title": "Essential Proposal",  "label": "Essential",  "levels": ["basic"]},
        {"title": "Comfort Proposal",    "label": "Comfort",    "levels": ["mid"]},
        {"title": "Premium Proposal",    "label": "Premium",    "levels": ["premium"]},
        {"title": "Luxury Proposal",     "label": "Luxury",     "levels": ["luxury"]},
    ]
    # Centre the tiers around the project's level
    base = max(0, min(level_idx, len(tiers) - 1))
    start = max(0, base - 0)
    selected = tiers[start: start + num_proposals]
    if len(selected) < num_proposals:
        selected = tiers[max(0, len(tiers) - num_proposals):]
    return selected[:num_proposals]


def _score_lamp(lamp: Lamp, preferred_temps: list, preferred_cats: list) -> float:
    score = 0.0
    if lamp.color_temp and any(t in (lamp.color_temp or "") for t in preferred_temps):
        score += 3.0
    if lamp.category and lamp.category.lower() in [c.lower() for c in preferred_cats]:
        score += 2.0
    if lamp.cri and lamp.cri >= 90:
        score += 1.0
    if lamp.dimmable:
        score += 0.5
    if lamp.lumens and 200 <= lamp.lumens <= 2000:
        score += 0.5
    return score


def _normalize_room(room: str) -> str:
    mapping = {
        "sala": "living", "comedor": "dining", "cocina": "kitchen",
        "dormitorio": "bedroom", "habitación": "bedroom", "habitacion": "bedroom",
        "baño": "bathroom", "oficina": "office", "pasillo": "hall", "terraza": "terrace",
        "garaje": "garage", "garage": "garage",
    }
    r = room.lower().strip()
    return mapping.get(r, r)


def _estimate_room_sqm(room: str, total_sqm: float, num_rooms: int) -> float:
    weights = {
        "living": 0.25, "dining": 0.12, "kitchen": 0.10, "bedroom": 0.15,
        "bathroom": 0.06, "office": 0.12, "lobby": 0.10, "hall": 0.08,
    }
    w = weights.get(room, 1.0 / max(num_rooms, 1))
    return max(6.0, total_sqm * w)


def _estimate_quantity(lamp: Lamp, room_sqm: float) -> int:
    """Estimate how many fixtures needed for a room based on lux targets."""
    if not lamp.lumens or lamp.lumens == 0:
        return max(1, int(room_sqm / 5))
    target_lux = 300  # average residential target
    utilization = 0.65
    required_lumens = target_lux * room_sqm / utilization
    qty = max(1, round(required_lumens / lamp.lumens))
    return min(qty, 12)  # cap at 12 per room
