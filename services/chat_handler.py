"""
Natural language chat handler using Claude tool_use.
Stateless server side — conversation history is passed in by the client.
"""
import os
import json
from sqlalchemy.orm import Session
from database import Lamp, Project, Proposal


SYSTEM_PROMPT = """You are LampAdvisor, an expert AI lighting design consultant embedded in a lamp proposal system.

You help sales reps and lighting designers:
- Find the right lamps from the catalog for any project
- Understand lighting requirements (lux levels, CCT, CRI, etc.)
- Compare products and explain recommendations
- Answer questions about color temperature, energy efficiency, IP ratings, dimming, etc.

Lighting design knowledge:
- Residential warm: 2700K–3000K, CRI 80+
- Hospitality/retail: 2700K–3000K, CRI 90+ (better colour rendering)
- Offices: 4000K, CRI 80+, 300–500 lux target
- Luxury/premium projects: always recommend dimmable, CRI 90+
- Wet areas (bathrooms, outdoor): IP44 minimum, IP65 for full outdoor
- Lux targets: living room 150–300, kitchen 300–500, office 500, retail 500–1000

Always be concise, specific, and professional. Use numbers and specs.
When searching for lamps, use the available tools and present results clearly."""


TOOLS = [
    {
        "name": "search_lamps",
        "description": "Search the lamp catalog by any combination of criteria. Returns matching lamps.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category":       {"type": "string", "description": "e.g. downlight, pendant, panel, strip, spot"},
                "property_level": {"type": "string", "description": "basic, mid, premium, or luxury"},
                "color_temp":     {"type": "string", "description": "e.g. 3000K, 4000K"},
                "indoor_outdoor": {"type": "string", "description": "indoor, outdoor, or both"},
                "min_cri":        {"type": "integer", "description": "minimum CRI value"},
                "dimmable":       {"type": "boolean"},
                "max_price":      {"type": "number", "description": "maximum price in USD"},
                "limit":          {"type": "integer", "description": "max results (default 8)"},
            },
        },
    },
    {
        "name": "get_catalog_summary",
        "description": "Get a summary of how many lamps are in the catalog, broken down by level and category.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_recent_projects",
        "description": "List the most recent projects in the system.",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "number of projects to return (default 5)"},
            },
        },
    },
    {
        "name": "get_lighting_requirements",
        "description": "Calculate how many lamps are needed for a room given area and target lux level.",
        "input_schema": {
            "type": "object",
            "required": ["room_sqm", "lamp_lumens"],
            "properties": {
                "room_sqm":     {"type": "number"},
                "lamp_lumens":  {"type": "number"},
                "target_lux":   {"type": "number", "description": "default 300"},
                "utilization":  {"type": "number", "description": "light utilization factor 0-1, default 0.65"},
            },
        },
    },
]


def handle_message(message: str, history: list[dict], db: Session) -> dict:
    """
    Process one chat message. Returns {response, tool_results}.
    history: list of {role, content} dicts.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key or api_key.startswith("your_"):
        return {
            "response": "⚠️ Chat requires an Anthropic API key. Please set `ANTHROPIC_API_KEY` in your `.env` file.",
            "tool_results": [],
        }

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        messages = list(history) + [{"role": "user", "content": message}]

        tool_results_accumulated = []

        # Agentic loop — let Claude call tools as needed
        for _ in range(5):  # max 5 tool rounds
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1500,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages,
            )

            if response.stop_reason == "end_turn":
                text = "".join(b.text for b in response.content if hasattr(b, "text"))
                return {"response": text, "tool_results": tool_results_accumulated}

            if response.stop_reason == "tool_use":
                # Process all tool calls
                tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
                tool_results_msg = []

                for tool_call in tool_use_blocks:
                    result = _execute_tool(tool_call.name, tool_call.input, db)
                    tool_results_accumulated.append({"tool": tool_call.name, "result": result})
                    tool_results_msg.append({
                        "type": "tool_result",
                        "tool_use_id": tool_call.id,
                        "content": json.dumps(result),
                    })

                # Append assistant message + tool results to messages
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results_msg})
                continue

            break

        text = "".join(b.text for b in response.content if hasattr(b, "text"))
        return {"response": text or "I couldn't process that request.", "tool_results": tool_results_accumulated}

    except Exception as e:
        return {"response": f"Error: {str(e)}", "tool_results": []}


def _execute_tool(name: str, inputs: dict, db: Session) -> dict:
    if name == "search_lamps":
        return _search_lamps(inputs, db)
    elif name == "get_catalog_summary":
        return _catalog_summary(db)
    elif name == "get_recent_projects":
        return _recent_projects(inputs, db)
    elif name == "get_lighting_requirements":
        return _lighting_requirements(inputs)
    return {"error": f"Unknown tool: {name}"}


def _search_lamps(inputs: dict, db: Session) -> dict:
    q = db.query(Lamp)
    if inputs.get("category"):
        q = q.filter(Lamp.category.ilike(f"%{inputs['category']}%"))
    if inputs.get("property_level"):
        q = q.filter(Lamp.property_level == inputs["property_level"])
    if inputs.get("color_temp"):
        q = q.filter(Lamp.color_temp.ilike(f"%{inputs['color_temp']}%"))
    if inputs.get("indoor_outdoor"):
        q = q.filter(Lamp.indoor_outdoor.in_([inputs["indoor_outdoor"], "both"]))
    if inputs.get("min_cri"):
        q = q.filter(Lamp.cri >= inputs["min_cri"])
    if inputs.get("dimmable") is not None:
        q = q.filter(Lamp.dimmable == inputs["dimmable"])
    if inputs.get("max_price"):
        q = q.filter(Lamp.price_usd <= inputs["max_price"])

    limit = min(inputs.get("limit", 8), 20)
    lamps = q.limit(limit).all()

    return {
        "count": len(lamps),
        "lamps": [
            {
                "id": l.id, "brand": l.brand, "model": l.model, "category": l.category,
                "wattage": l.wattage, "lumens": l.lumens, "color_temp": l.color_temp,
                "cri": l.cri, "ip_rating": l.ip_rating, "dimmable": l.dimmable,
                "property_level": l.property_level, "price_usd": l.price_usd,
            }
            for l in lamps
        ],
    }


def _catalog_summary(db: Session) -> dict:
    total = db.query(Lamp).count()
    by_level = {}
    for level in ["basic", "mid", "premium", "luxury"]:
        by_level[level] = db.query(Lamp).filter(Lamp.property_level == level).count()
    categories = {}
    for lamp in db.query(Lamp.category).distinct():
        if lamp[0]:
            categories[lamp[0]] = db.query(Lamp).filter(Lamp.category == lamp[0]).count()
    return {"total_lamps": total, "by_level": by_level, "by_category": categories}


def _recent_projects(inputs: dict, db: Session) -> dict:
    limit = inputs.get("limit", 5)
    projects = db.query(Project).order_by(Project.created_at.desc()).limit(limit).all()
    return {
        "projects": [
            {
                "id": p.id, "name": p.name, "client": p.client_name,
                "type": p.property_type, "level": p.property_level,
                "sqm": p.total_sqm, "status": p.status,
            }
            for p in projects
        ]
    }


def _lighting_requirements(inputs: dict) -> dict:
    room_sqm = inputs.get("room_sqm", 20)
    lamp_lumens = inputs.get("lamp_lumens", 800)
    target_lux = inputs.get("target_lux", 300)
    utilization = inputs.get("utilization", 0.65)
    required_lumens = target_lux * room_sqm / utilization
    qty = max(1, round(required_lumens / lamp_lumens))
    total_lumens = qty * lamp_lumens
    actual_lux = round((total_lumens * utilization) / room_sqm)
    return {
        "room_sqm": room_sqm,
        "target_lux": target_lux,
        "lamp_lumens": lamp_lumens,
        "fixtures_needed": qty,
        "actual_lux_achieved": actual_lux,
        "total_watts": None,
    }
