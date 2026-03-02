"""
Deep project analyzer using Claude Vision + text extraction.
Pulls: sqm, rooms + sizes, lamp counts, property type/level, style, special notes.
"""
import os
import json
import asyncio
import base64
from pathlib import Path

from services.progress import push_sync
from services.file_parser import parse_file  # fallback


ANALYSIS_PROMPT = """You are an expert architect and lighting designer.
Analyze the provided floor plan / project document and extract the following information.
Return ONLY a valid JSON object — no explanation, no markdown fences.

Required JSON structure:
{
  "total_sqm": number or null,
  "num_floors": integer or null,
  "property_type": "residential|commercial|office|hotel|restaurant|retail" or null,
  "property_level": "basic|mid|premium|luxury" or null,
  "style": "modern|classic|minimalist|industrial|rustic|nordic" or null,
  "rooms": [
    {
      "name": "room name in English",
      "sqm": number or null,
      "fixtures_recommended": integer,
      "notes": "any special requirements"
    }
  ],
  "special_requirements": "free text — outdoor areas, high ceilings, wet zones, etc.",
  "extracted_notes": "any other useful project info from the document"
}

Lighting fixture estimation rules:
- Residential general: 1 fixture per 4–6 m² (downlights) or 1 pendant per room
- Living/dining: 1 pendant + 2–4 downlights or spots per 20m²
- Bedroom: 1 ceiling + 2 wall/bedside per room
- Kitchen: 1 per 4m² (panels/downlights) + under-cabinet strip
- Bathroom: 1–2 per bathroom
- Office: 1 panel per 6m²
- Lobby/hotel: statement pendants + accent downlights
- Retail: 1 track head per 3–4m²
"""


def run_analysis(file_path: str, session_id: str, loop: asyncio.AbstractEventLoop) -> dict:
    """Synchronous worker — run in a background thread."""

    def emit(step: str, msg: str, progress: int = 0, done: bool = False, **kwargs):
        push_sync(session_id, loop, {"step": step, "msg": msg, "progress": progress, "done": done, **kwargs})

    emit("start", "Starting project analysis…", 5)

    try:
        ext = Path(file_path).suffix.lower()
        from services.ai_client import get_client
        ai = get_client()

        if ai.is_configured():
            if ext == ".pdf":
                return _analyze_pdf_with_ai(file_path, ai, emit)
            elif ext in (".dwg", ".dxf"):
                return _analyze_cad_with_ai(file_path, ai, emit)
        else:
            emit("fallback", "No API key — using text extraction…", 20)

        # Fallback: use existing regex parser
        result = parse_file(file_path)
        extracted = result.get("extracted", {})
        rooms_raw = extracted.get("rooms", [])
        rooms = [{"name": r, "sqm": None, "fixtures_recommended": 2, "notes": ""} for r in rooms_raw]
        emit("done", "Analysis complete (basic extraction)", 100, done=True)
        return {
            "total_sqm": extracted.get("total_sqm"),
            "num_floors": extracted.get("num_floors"),
            "property_type": extracted.get("property_type"),
            "property_level": extracted.get("property_level"),
            "style": extracted.get("style"),
            "rooms": rooms,
            "special_requirements": "",
            "extracted_notes": result.get("raw_text", "")[:500],
        }

    except Exception as e:
        emit("error", f"Analysis failed: {str(e)}", done=True)
        return {}


def _analyze_pdf_with_ai(file_path: str, ai, emit) -> dict:
    import pdfplumber

    emit("extract", "Extracting text from PDF…", 15)
    raw_text = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages[:8]:
                t = page.extract_text()
                if t:
                    raw_text += t + "\n"
    except Exception:
        pass

    # Try to extract images via PyMuPDF
    images_b64 = []
    emit("images", "Converting PDF pages to images for visual analysis…", 30)
    try:
        import fitz  # pymupdf
        doc = fitz.open(file_path)
        for page_num in range(min(4, len(doc))):
            page = doc[page_num]
            mat = fitz.Matrix(1.2, 1.2)
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")
            images_b64.append(base64.standard_b64encode(img_bytes).decode())
        doc.close()
        emit("images", f"Extracted {len(images_b64)} page image(s)", 45)
    except Exception as e:
        emit("images", f"Image extraction skipped ({e})", 45)

    return _call_ai_vision(raw_text, images_b64, ai, emit)


def _analyze_cad_with_ai(file_path: str, ai, emit) -> dict:
    emit("extract", "Parsing DWG/DXF file…", 15)
    try:
        import ezdxf
        doc = ezdxf.readfile(file_path)
        msp = doc.modelspace()

        texts = []
        layer_names = set()
        areas = []

        for entity in msp:
            layer_names.add(entity.dxf.layer)
            if entity.dxftype() in ("TEXT", "MTEXT"):
                try:
                    t = entity.plain_mtext() if entity.dxftype() == "MTEXT" else entity.dxf.text
                    if t and t.strip():
                        texts.append(t.strip())
                except Exception:
                    pass
            if entity.dxftype() == "LWPOLYLINE" and entity.is_closed:
                try:
                    from ezdxf.math import area as calc_area
                    pts = list(entity.get_points())
                    if len(pts) >= 3:
                        xy = [(p[0], p[1]) for p in pts]
                        a = abs(calc_area(xy))
                        if a > 1:
                            areas.append(round(a / 1_000_000, 2))
                except Exception:
                    pass

        raw_text = f"Layer names: {', '.join(list(layer_names)[:50])}\n\nText entities:\n" + "\n".join(texts[:200])
        if areas:
            raw_text += f"\n\nCalculated areas (m²): {areas[:20]}"

        emit("extract", f"Extracted {len(texts)} text entities from {len(layer_names)} layers", 40)
    except Exception as e:
        emit("error", f"CAD parsing failed: {e}", done=True)
        return {}

    return _call_ai_vision(raw_text, [], ai, emit)


def _call_ai_vision(raw_text: str, images_b64: list[str], ai, emit) -> dict:
    emit("ai", f"Sending to {ai.provider} ({ai.model})…", 55)
    try:
        text_prompt = ANALYSIS_PROMPT
        if raw_text.strip():
            text_prompt += f"\n\nEXTRACTED TEXT FROM DOCUMENT:\n{raw_text[:6000]}"
        else:
            text_prompt += "\n\nPlease analyze the floor plan images above."

        emit("ai", "Waiting for AI analysis…", 65)
        response = ai.complete_with_vision(
            text_prompt=text_prompt,
            images_b64=images_b64,
            max_tokens=2000,
        ).strip()
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0].strip()
        elif "```" in response:
            response = response.split("```")[1].split("```")[0].strip()

        emit("ai", "Parsing analysis results…", 80)
        data = json.loads(response)
        emit("done", "✓ Project analysis complete", 100, done=True)
        return data

    except Exception as e:
        emit("error", f"AI analysis failed: {e}", done=True)
        return {}
