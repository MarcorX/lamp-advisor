"""
AI Lighting Agent — expert lighting designer persona.

Flow:
  1. analyze_project()  — reads files, emits SSE progress, final event carries agent_message
  2. chat_turn()        — continues the conversation
  3. generate_brief()   — produces structured requirements JSON from conversation
  4. match_catalog()    — finds best catalog lamps for each brief item
"""
from __future__ import annotations
import re
import json
import base64
import asyncio
from pathlib import Path
from sqlalchemy.orm import Session

from database import Lamp
from services.progress import push_sync


# ---------------------------------------------------------------------------
# Agent persona / system prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are Alex, an expert lighting designer and interior lighting specialist with 20 years of \
experience across residential, commercial, hotel, retail, and hospitality projects.

Your role: analyze architectural floor plans and project documents, then develop precise \
lighting specifications that clients can use to purchase and install the right luminaires.

When analyzing a project, always specify for each space:
- Fixture type (downlight, pendant, strip, wall, floor, track, panel, spot, outdoor, mirror)
- Quantity
- Color temperature / CCT (2700K, 3000K, 4000K, 5000K, 6500K, or tunable white)
- Luminous flux in lumens (lm)
- Power in watts (W) where known
- CRI (80, 90, or 95+)
- IP rating (IP20 dry, IP44 bathrooms/kitchens, IP65+ outdoor, IP67/68 pools)
- Beam angle in degrees where relevant (15°, 24°, 36°, 60°)
- Dimmability (yes/no)

Color temperature guide:
- 2700K: warm white — living rooms, bedrooms, restaurants, hotel rooms, lobbies
- 3000K: warm neutral — kitchens, bathrooms, corridors, upscale retail
- 4000K: neutral white — offices, commercial spaces, workshops
- 5000–6500K: cool daylight — task lighting, medical, garages

IP rating guide:
- IP20: dry indoor areas
- IP44: bathrooms (zone 2), over kitchen sinks, covered outdoor
- IP65: exposed outdoor, direct spray
- IP67/IP68: submerged — pools, water features

Property level modifiers:
- Basic: functional, standard lamps, dimming optional
- Mid: quality fixtures, selective dimming in main rooms
- Premium: CRI 90+, full dimming, layered lighting (ambient + accent + task)
- Luxury: CRI 95+, tunable white, statement fixtures, bespoke

Be specific and professional. Say "6× recessed downlights, 9W, 2700K, 780 lm, CRI 90, \
dimmable, Ø95 mm" — not "some warm lights". Always invite corrections after your analysis.\
"""


BRIEF_INSTRUCTION = """\
Based on our conversation above, generate a complete lighting requirements brief as a JSON array.
Each element represents one group of identical fixtures.
Return ONLY valid JSON — no explanation, no markdown fences.

Schema (use null for unknown values):
[
  {
    "label":         "descriptive label e.g. 'Living room downlights'",
    "space":         "room or area name",
    "category":      "downlight|pendant|strip|wall|floor|outdoor|track|panel|spot|mirror",
    "qty":           <integer — number of fixtures; for strip lights set qty=null and use linear_meters>,
    "linear_meters": <number or null — total strip length in metres>,
    "cct":           "2700K|3000K|4000K|5000K|6500K|tunable",
    "lumens_min":    <integer or null>,
    "watts_max":     <number or null>,
    "cri_min":       <80|90|95>,
    "beam_angle":    <number or null>,
    "dimmable":      <true|false>,
    "ip_required":   "IP20|IP44|IP65|IP67|IP68",
    "notes":         "any special requirements"
  }
]\
"""


# ---------------------------------------------------------------------------
# File extraction helpers
# ---------------------------------------------------------------------------

def _extract_files(file_paths: list[str]) -> tuple[str, list[str]]:
    """Return (combined_raw_text, images_b64_list)."""
    all_text = ""
    all_images: list[str] = []

    for i, fp in enumerate(file_paths):
        ext = Path(fp).suffix.lower()
        name = Path(fp).name

        if ext == ".pdf":
            try:
                import pdfplumber
                with pdfplumber.open(fp) as pdf:
                    text = "".join(
                        (p.extract_text() or "") + "\n" for p in pdf.pages[:8]
                    ).strip()
                if text:
                    all_text += f"\n=== DOCUMENT {i + 1}: {name} ===\n{text}\n"
            except Exception:
                pass

            slots = min(2, 4 - len(all_images))
            if slots > 0:
                try:
                    import fitz
                    doc = fitz.open(fp)
                    for pn in range(min(slots, len(doc))):
                        pix = doc[pn].get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
                        all_images.append(
                            base64.standard_b64encode(pix.tobytes("png")).decode()
                        )
                    doc.close()
                except Exception:
                    pass

        elif ext in (".dwg", ".dxf"):
            try:
                import ezdxf
                doc = ezdxf.readfile(fp)
                msp = doc.modelspace()
                texts = []
                for ent in msp:
                    if ent.dxftype() in ("TEXT", "MTEXT"):
                        try:
                            t = ent.plain_mtext() if ent.dxftype() == "MTEXT" else ent.dxf.text
                            if t and t.strip():
                                texts.append(t.strip())
                        except Exception:
                            pass
                if texts:
                    all_text += f"\n=== CAD FILE {i + 1}: {name} ===\n" + "\n".join(texts[:200])
                else:
                    raise ValueError("no text entities")
            except Exception:
                # Binary DWG fallback — extract printable ASCII
                try:
                    raw = Path(fp).read_bytes()
                    parts = re.findall(rb"[ -~]{4,}", raw)
                    t = "\n".join(p.decode("ascii", errors="ignore") for p in parts[:500])
                    if t.strip():
                        all_text += f"\n=== DWG FILE {i + 1}: {name} (text extract) ===\n{t}\n"
                except Exception:
                    pass

    return all_text, all_images


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze_project(
    file_paths: list[str],
    session_id: str,
    loop: asyncio.AbstractEventLoop,
) -> str:
    """
    Synchronous worker — runs in a background thread.
    Emits SSE progress events via push_sync, then emits the agent's first message.
    Returns the agent message string.
    """
    def emit(step: str, msg: str, progress: int = 0, done: bool = False, **kwargs):
        push_sync(session_id, loop, {
            "step": step, "msg": msg, "progress": progress, "done": done, **kwargs
        })

    emit("start", f"Reading {len(file_paths)} file(s)…", 5)

    try:
        from services.ai_client import get_client
        ai = get_client()

        if not ai.is_configured():
            emit("error", "No AI API key configured — add one in Settings.", done=True)
            return ""

        emit("extract", "Extracting text and images from files…", 20)
        raw_text, images = _extract_files(file_paths)

        if not raw_text.strip() and not images:
            emit("error", "Could not extract any content from the uploaded files.", done=True)
            return ""

        emit("ai", f"Claude is reading the floor plan{'s' if len(file_paths) > 1 else ''}…", 55)

        analysis_prompt = (
            "Analyze the floor plan / project documents provided and express your understanding "
            "as an expert lighting designer.\n\n"
            "Structure your response:\n"
            "1. **Project overview** — property type, approximate size, quality level, style\n"
            "2. **Space-by-space specification** — for each room/area:\n"
            "   - Fixture type and quantity\n"
            "   - CCT, estimated lumens, watts, CRI\n"
            "   - IP rating (if relevant — bathrooms, kitchen, outdoor)\n"
            "   - Dimmability\n"
            "   - Any special notes (ceiling height, feature lighting, wet zones)\n"
            "3. **Summary line** — total fixture count, any notable special requirements\n"
            "4. **Ask the client** whether anything needs to be corrected or added.\n\n"
            "Be specific and professional. Use markdown for formatting (bold space names, bullet lists).\n"
        )
        if raw_text.strip():
            analysis_prompt += f"\n\nDOCUMENT DATA:\n{raw_text[:8000]}"

        agent_message = ai.complete_with_vision(
            text_prompt=analysis_prompt,
            images_b64=images,
            system=SYSTEM_PROMPT,
            max_tokens=3000,
        )

        emit("done", "Analysis complete", 100, done=True, agent_message=agent_message)
        return agent_message

    except Exception as e:
        emit("error", f"Analysis failed: {str(e)}", done=True)
        return ""


def chat_turn(messages: list[dict], ai) -> str:
    """Continue the agent conversation. messages = [{role, content}, ...]."""
    return ai.complete(messages=messages, system=SYSTEM_PROMPT, max_tokens=2000)


def generate_brief(messages: list[dict], ai) -> list[dict]:
    """Generate a structured requirements brief from the full conversation."""
    msgs = messages + [{"role": "user", "content": BRIEF_INSTRUCTION}]
    response = ai.complete(msgs, system=SYSTEM_PROMPT, max_tokens=4000).strip()

    # Clean markdown fences
    if "```json" in response:
        response = response.split("```json")[1].split("```")[0].strip()
    elif "```" in response:
        response = response.split("```")[1].split("```")[0].strip()
    if not response.startswith("["):
        s, e = response.find("["), response.rfind("]")
        if s != -1:
            response = response[s:e + 1]

    return json.loads(response)


def match_catalog(brief: list[dict], db: Session) -> list[dict]:
    """Match each brief item to the best available lamp in the catalog."""
    from services.recommender import _ip_level, _score_lamp

    all_lamps = db.query(Lamp).all()
    if not all_lamps:
        return []

    results = []
    for item in brief:
        category   = (item.get("category") or "").lower()
        cct        = item.get("cct") or ""
        cri_min    = int(item.get("cri_min") or 0)
        must_dim   = bool(item.get("dimmable", False))
        ip_req     = item.get("ip_required") or "IP20"
        ip_level   = _ip_level(ip_req)

        # Filter by IP first
        candidates = [l for l in all_lamps if _ip_level(l.ip_rating or "IP20") >= ip_level]
        if not candidates:
            candidates = all_lamps

        # Score
        scored = [
            (_score_lamp(l, [category] if category else [], [cct] if cct else [], cri_min, must_dim), l)
            for l in candidates
        ]
        scored.sort(key=lambda x: -x[0])
        if not scored:
            continue

        _, best = scored[0]
        qty = item.get("qty") or 1
        linear_m = item.get("linear_meters")
        if linear_m:
            qty = max(1, round(float(linear_m) / 5))   # treat ~5 m per strip unit

        subtotal = round((best.price_usd or 0) * qty, 2)

        results.append({
            # Brief requirement
            "label":         item.get("label", ""),
            "space":         item.get("space", ""),
            "req_category":  item.get("category", ""),
            "qty":           qty,
            "linear_meters": linear_m,
            "req_cct":       cct,
            "req_cri":       cri_min,
            "req_ip":        ip_req,
            "req_dimmable":  must_dim,
            "req_watts_max": item.get("watts_max"),
            "req_lumens_min":item.get("lumens_min"),
            "notes":         item.get("notes", ""),
            # Matched product
            "lamp_id":       best.id,
            "lamp_brand":    best.brand,
            "lamp_model":    best.model,
            "lamp_category": best.category,
            "lamp_wattage":  best.wattage,
            "lamp_lumens":   best.lumens,
            "lamp_cct":      best.color_temp,
            "lamp_cri":      best.cri,
            "lamp_dimmable": best.dimmable,
            "lamp_ip":       best.ip_rating,
            "lamp_price":    best.price_usd,
            "lamp_image":    best.image_url,
            "lamp_url":      best.datasheet_url,
            "subtotal":      subtotal,
        })

    return results
