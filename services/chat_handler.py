"""
Natural language chat using unified AI client with tool_use.
"""
import json
from sqlalchemy.orm import Session
from database import Lamp, Project
from services.ai_client import get_client, register_tool_executor


SYSTEM_PROMPT = """You are LampAdvisor, an expert AI lighting design consultant.
You help find the right lamps from the catalog, answer lighting questions, and assist with proposals.

Lighting knowledge:
- Residential warm: 2700K–3000K, CRI 80+
- Hospitality / retail: 2700K–3000K, CRI 90+
- Offices: 4000K, CRI 80+, 300–500 lux target
- Luxury projects: dimmable, CRI 90+
- Wet areas: IP44+ minimum, IP65 for outdoor
- Lux targets: living room 150–300, kitchen 300–500, office 500, retail 500–1000

Be concise, specific, and use numbers."""


TOOLS = [
    {
        "name": "search_lamps",
        "description": "Search the lamp catalog by criteria.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category":       {"type": "string"},
                "property_level": {"type": "string", "description": "basic, mid, premium, luxury"},
                "color_temp":     {"type": "string"},
                "indoor_outdoor": {"type": "string"},
                "min_cri":        {"type": "integer"},
                "dimmable":       {"type": "boolean"},
                "max_price":      {"type": "number"},
                "limit":          {"type": "integer"},
            },
        },
    },
    {
        "name": "get_catalog_summary",
        "description": "Summary of lamps in the catalog by level and category.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_recent_projects",
        "description": "List recent projects.",
        "input_schema": {
            "type": "object",
            "properties": {"limit": {"type": "integer"}},
        },
    },
    {
        "name": "get_lighting_requirements",
        "description": "Calculate how many fixtures are needed for a room.",
        "input_schema": {
            "type": "object",
            "required": ["room_sqm", "lamp_lumens"],
            "properties": {
                "room_sqm":    {"type": "number"},
                "lamp_lumens": {"type": "number"},
                "target_lux":  {"type": "number"},
                "utilization": {"type": "number"},
            },
        },
    },
]

# We hold a reference to the DB session in a thread-local way via a closure
_current_db = None


def handle_message(message: str, history: list[dict], db: Session) -> dict:
    global _current_db
    _current_db = db

    # Register the tool executor so ai_client can call it
    register_tool_executor(_execute_tool_with_db)

    client = get_client()
    if not client.is_configured():
        return {
            "response": "⚠️ No AI provider configured. Go to **Settings** to add an API key.",
            "tool_results": [],
        }

    try:
        messages = list(history) + [{"role": "user", "content": message}]
        text, tool_results = client.complete_with_tools(messages, SYSTEM_PROMPT, TOOLS)
        return {"response": text or "I couldn't process that request.", "tool_results": tool_results}
    except Exception as e:
        return {"response": f"Error: {str(e)}", "tool_results": []}


def _execute_tool_with_db(name: str, inputs: dict) -> dict:
    db = _current_db
    if db is None:
        return {"error": "No database session"}
    if name == "search_lamps":       return _search_lamps(inputs, db)
    if name == "get_catalog_summary": return _catalog_summary(db)
    if name == "get_recent_projects": return _recent_projects(inputs, db)
    if name == "get_lighting_requirements": return _lighting_requirements(inputs)
    return {"error": f"Unknown tool: {name}"}


def _search_lamps(inputs, db):
    q = db.query(Lamp)
    if inputs.get("category"):       q = q.filter(Lamp.category.ilike(f"%{inputs['category']}%"))
    if inputs.get("property_level"): q = q.filter(Lamp.property_level == inputs["property_level"])
    if inputs.get("color_temp"):     q = q.filter(Lamp.color_temp.ilike(f"%{inputs['color_temp']}%"))
    if inputs.get("indoor_outdoor"): q = q.filter(Lamp.indoor_outdoor.in_([inputs["indoor_outdoor"], "both"]))
    if inputs.get("min_cri"):        q = q.filter(Lamp.cri >= inputs["min_cri"])
    if inputs.get("dimmable") is not None: q = q.filter(Lamp.dimmable == inputs["dimmable"])
    if inputs.get("max_price"):      q = q.filter(Lamp.price_usd <= inputs["max_price"])
    lamps = q.limit(min(inputs.get("limit", 8), 20)).all()
    return {
        "count": len(lamps),
        "lamps": [{"id": l.id, "brand": l.brand, "model": l.model, "category": l.category,
                   "wattage": l.wattage, "lumens": l.lumens, "color_temp": l.color_temp,
                   "cri": l.cri, "ip_rating": l.ip_rating, "dimmable": l.dimmable,
                   "property_level": l.property_level, "price_usd": l.price_usd}
                  for l in lamps],
    }


def _catalog_summary(db):
    total = db.query(Lamp).count()
    by_level = {lvl: db.query(Lamp).filter(Lamp.property_level == lvl).count()
                for lvl in ["basic", "mid", "premium", "luxury"]}
    cats = {}
    for (cat,) in db.query(Lamp.category).distinct():
        if cat:
            cats[cat] = db.query(Lamp).filter(Lamp.category == cat).count()
    return {"total_lamps": total, "by_level": by_level, "by_category": cats}


def _recent_projects(inputs, db):
    projects = db.query(Project).order_by(Project.created_at.desc()).limit(inputs.get("limit", 5)).all()
    return {"projects": [{"id": p.id, "name": p.name, "client": p.client_name,
                          "type": p.property_type, "level": p.property_level,
                          "sqm": p.total_sqm, "status": p.status} for p in projects]}


def _lighting_requirements(inputs):
    sqm  = inputs.get("room_sqm", 20)
    lm   = inputs.get("lamp_lumens", 800)
    lux  = inputs.get("target_lux", 300)
    util = inputs.get("utilization", 0.65)
    qty  = max(1, round(lux * sqm / util / lm))
    return {"room_sqm": sqm, "target_lux": lux, "lamp_lumens": lm,
            "fixtures_needed": qty, "actual_lux": round(qty * lm * util / sqm)}
