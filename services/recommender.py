"""
Lamp recommendation engine.
Uses per-room AI specs (fixture_types, CCT, CRI, IP, dimmable) when available,
falls back to heuristics for plain room name strings.
"""
from sqlalchemy.orm import Session
from database import Lamp


LEVEL_ORDER = {"basic": 0, "mid": 1, "premium": 2, "luxury": 3}

LEVEL_SCOPE = {
    "basic":   ["basic"],
    "mid":     ["basic", "mid"],
    "premium": ["mid", "premium"],
    "luxury":  ["premium", "luxury"],
}

# Fallback heuristics when rooms are plain strings
SPACE_COLOR_TEMP = {
    "living":     ["2700K", "3000K"],
    "sala":       ["2700K", "3000K"],
    "dining":     ["2700K", "3000K"],
    "comedor":    ["2700K", "3000K"],
    "bedroom":    ["2700K", "3000K"],
    "dormitorio": ["2700K", "3000K"],
    "kitchen":    ["3000K", "4000K"],
    "cocina":     ["3000K", "4000K"],
    "bathroom":   ["3000K", "4000K"],
    "baño":       ["3000K", "4000K"],
    "office":     ["4000K"],
    "oficina":    ["4000K"],
    "lobby":      ["2700K", "3000K"],
    "retail":     ["3000K", "4000K"],
    "restaurant": ["2700K", "3000K"],
    "hotel":      ["2700K", "3000K"],
    "hall":       ["3000K"],
    "corridor":   ["3000K"],
    "terrace":    ["2700K", "3000K"],
    "outdoor":    ["2700K", "3000K"],
    "default":    ["3000K"],
}

SPACE_CATEGORIES = {
    "living":     ["pendant", "floor", "wall", "spot", "downlight"],
    "dining":     ["pendant", "spot", "downlight"],
    "bedroom":    ["pendant", "wall", "downlight", "strip"],
    "kitchen":    ["panel", "downlight", "strip", "track"],
    "bathroom":   ["downlight", "wall", "mirror"],
    "office":     ["panel", "track", "downlight"],
    "lobby":      ["pendant", "wall", "downlight", "floor"],
    "retail":     ["track", "spot", "strip"],
    "restaurant": ["pendant", "wall", "strip", "floor"],
    "hotel":      ["pendant", "wall", "downlight", "floor"],
    "hall":       ["downlight", "wall"],
    "corridor":   ["downlight", "wall"],
    "terrace":    ["wall", "floor", "outdoor"],
    "outdoor":    ["outdoor", "wall", "floor"],
    "default":    ["downlight", "spot", "panel"],
}

SPACE_IP = {
    "bathroom": "IP44", "baño": "IP44", "kitchen": "IP44", "cocina": "IP44",
    "terrace": "IP65", "outdoor": "IP65", "garage": "IP44", "default": "IP20",
}

# Lux targets by space (for quantity estimation)
SPACE_LUX = {
    "living": 150, "dining": 200, "bedroom": 100, "kitchen": 300,
    "bathroom": 200, "office": 400, "retail": 500, "default": 200,
}


def get_recommendations(db: Session, project: dict, num_proposals: int = 3) -> list[dict]:
    property_level = project.get("property_level", "mid")
    property_type  = project.get("property_type", "residential")
    total_sqm      = float(project.get("total_sqm") or 80)
    budget_usd     = project.get("budget_usd")

    # Normalise rooms to list of dicts
    rooms = _normalise_rooms(project.get("rooms") or ["living", "bedroom", "kitchen", "bathroom"])

    allowed_levels = LEVEL_SCOPE.get(property_level, ["mid"])
    query = db.query(Lamp).filter(Lamp.property_level.in_(allowed_levels))
    all_lamps = query.all()
    if not all_lamps:
        return []

    tiers = _build_tiers(property_level, num_proposals)
    proposals = []

    for tier_idx, tier in enumerate(tiers):
        tier_lamps = [l for l in all_lamps if l.property_level in tier["levels"]] or all_lamps
        room_assignments = []
        total_price = 0.0

        for room_data in rooms:
            room_name = room_data.get("name", "room")
            room_norm = _normalize_name(room_name)

            # Prefer AI-supplied specs; fall back to heuristics
            preferred_types = room_data.get("fixture_types") or SPACE_CATEGORIES.get(room_norm, SPACE_CATEGORIES["default"])
            preferred_temp  = room_data.get("color_temp")   # single string e.g. "2700K" or None
            cri_min         = room_data.get("cri_min", 0)
            ip_required     = room_data.get("ip_required") or SPACE_IP.get(room_norm, SPACE_IP["default"])
            must_dim        = room_data.get("dimmable", False)
            ai_count        = room_data.get("fixtures_recommended")
            room_sqm        = room_data.get("sqm") or _estimate_room_sqm(room_norm, total_sqm, len(rooms))

            # Fallback temp list from heuristics if not AI-supplied
            if not preferred_temp:
                fallback_temps = SPACE_COLOR_TEMP.get(room_norm, SPACE_COLOR_TEMP["default"])
            else:
                fallback_temps = [preferred_temp]

            # Filter candidates by IP requirement
            ip_level = _ip_level(ip_required)
            candidates = [l for l in tier_lamps if _ip_level(l.ip_rating or "IP20") >= ip_level]
            if not candidates:
                candidates = tier_lamps

            # Score and pick best lamp
            scored = [(
                _score_lamp(l, preferred_types, fallback_temps, cri_min, must_dim),
                l
            ) for l in candidates]
            scored.sort(key=lambda x: -x[0])

            if not scored:
                continue

            _, best = scored[0]
            qty = ai_count if ai_count else _estimate_quantity(best, room_sqm, room_norm)
            subtotal = (best.price_usd or 0) * qty
            total_price += subtotal

            room_assignments.append({
                "room":            room_name,
                "lamp_id":         best.id,
                "lamp_brand":      best.brand,
                "lamp_model":      best.model,
                "lamp_category":   best.category,
                "lamp_wattage":    best.wattage,
                "lamp_lumens":     best.lumens,
                "lamp_color_temp": best.color_temp,
                "lamp_cri":        best.cri,
                "lamp_dimmable":   best.dimmable,
                "lamp_ip":         best.ip_rating,
                "lamp_price":      best.price_usd,
                "quantity":        qty,
                "subtotal":        round(subtotal, 2),
                # pass along AI notes if any
                "room_notes":      room_data.get("notes", ""),
                "room_sqm":        room_sqm,
            })

        proposals.append({
            "proposal_number":  tier_idx + 1,
            "title":            tier["title"],
            "tier_label":       tier["label"],
            "room_assignments": room_assignments,
            "total_price":      round(total_price, 2),
        })

    return proposals


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalise_rooms(rooms_raw) -> list[dict]:
    """Accept list of strings or list of dicts."""
    result = []
    for r in rooms_raw:
        if isinstance(r, str):
            result.append({"name": r.strip()})
        elif isinstance(r, dict):
            result.append(r)
    return result


def _build_tiers(property_level: str, num_proposals: int) -> list[dict]:
    level_idx = LEVEL_ORDER.get(property_level, 1)
    all_tiers = [
        {"title": "Essential Proposal", "label": "Essential", "levels": ["basic"]},
        {"title": "Comfort Proposal",   "label": "Comfort",   "levels": ["mid"]},
        {"title": "Premium Proposal",   "label": "Premium",   "levels": ["premium"]},
        {"title": "Luxury Proposal",    "label": "Luxury",    "levels": ["luxury"]},
    ]
    base = max(0, min(level_idx, len(all_tiers) - 1))
    selected = all_tiers[base: base + num_proposals]
    if len(selected) < num_proposals:
        selected = all_tiers[max(0, len(all_tiers) - num_proposals):]
    return selected[:num_proposals]


def _score_lamp(lamp: Lamp, preferred_types: list, preferred_temps: list,
                cri_min: int, must_dim: bool) -> float:
    score = 0.0
    cat = (lamp.category or "").lower()
    if any(t.lower() == cat for t in preferred_types):
        score += 5.0  # exact category match
    elif any(t.lower() in cat or cat in t.lower() for t in preferred_types):
        score += 2.0  # partial match

    lamp_temp = lamp.color_temp or ""
    if any(t in lamp_temp for t in preferred_temps):
        score += 3.0
    elif "tunable" in lamp_temp:
        score += 1.5  # tunable covers any target

    if cri_min and lamp.cri and lamp.cri >= cri_min:
        score += 2.0
    elif lamp.cri and lamp.cri >= 90:
        score += 1.0

    if must_dim and lamp.dimmable:
        score += 1.5
    elif lamp.dimmable:
        score += 0.5

    if lamp.lumens and 100 <= lamp.lumens <= 3000:
        score += 0.5

    return score


def _ip_level(ip_str: str) -> int:
    """Return numeric IP level for comparison."""
    ip = (ip_str or "IP20").upper()
    if "IP67" in ip or "IP68" in ip:
        return 67
    if "IP65" in ip or "IP66" in ip:
        return 65
    if "IP44" in ip or "IP54" in ip:
        return 44
    return 20


def _normalize_name(name: str) -> str:
    mapping = {
        "sala": "living", "comedor": "dining", "cocina": "kitchen",
        "dormitorio": "bedroom", "habitación": "bedroom", "habitacion": "bedroom",
        "cuarto": "bedroom", "baño": "bathroom", "oficina": "office",
        "pasillo": "hall", "corredor": "corridor", "terraza": "terrace",
        "garaje": "garage", "master bedroom": "bedroom", "master bath": "bathroom",
        "dining room": "dining", "living room": "living",
    }
    n = name.lower().strip()
    return mapping.get(n, n.split()[0] if " " in n else n)


def _estimate_room_sqm(room: str, total_sqm: float, num_rooms: int) -> float:
    weights = {
        "living": 0.22, "dining": 0.10, "kitchen": 0.10, "bedroom": 0.14,
        "bathroom": 0.05, "office": 0.12, "lobby": 0.10, "hall": 0.06,
        "corridor": 0.05, "terrace": 0.08, "outdoor": 0.08,
    }
    w = weights.get(room, 1.0 / max(num_rooms, 1))
    return max(5.0, total_sqm * w)


def _estimate_quantity(lamp: Lamp, room_sqm: float, room_norm: str) -> int:
    target_lux = SPACE_LUX.get(room_norm, SPACE_LUX["default"])
    utilization = 0.65
    if not lamp.lumens or lamp.lumens == 0:
        return max(1, int(room_sqm / 5))
    required_lumens = target_lux * room_sqm / utilization
    qty = max(1, round(required_lumens / lamp.lumens))
    return min(qty, 16)
