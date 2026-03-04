"""
Deep project analyzer using Claude Vision + text extraction.
Pulls: sqm, rooms + sizes + per-room lighting specs, property type/level, style.
"""
import os
import re
import json
import asyncio
import base64
from pathlib import Path
from collections import defaultdict

from services.progress import push_sync
from services.file_parser import parse_file  # fallback


ANALYSIS_PROMPT = """You are an expert lighting designer and architect.
Analyze the provided floor plan / project document and return a detailed room-by-room lighting specification.
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
      "ceiling_height_m": number or null,
      "fixtures_recommended": integer,
      "fixture_types": ["downlight","pendant","spot","panel","strip","wall","floor","track","mirror"],
      "color_temp": "2700K|3000K|4000K|tunable",
      "cri_min": 80 or 90 or 95,
      "ip_required": "IP20|IP44|IP65",
      "dimmable": true or false,
      "notes": "special lighting notes for this room"
    }
  ],
  "special_requirements": "free text — outdoor, high ceilings, wet zones, etc.",
  "extracted_notes": "any other useful project information",
  "summary": "2-3 sentence plain-language overview of the lighting plan — e.g. 'This 220m² premium residence needs 68 fixtures across 9 spaces. Key areas include a dimmable pendant over the dining table, IP44 downlights in kitchen and bathrooms, and warm 2700K throughout living spaces. All main areas should be dimmable with CRI 90+ lamps.'"
}

Per-space lighting rules:
- Living room: 2700-3000K, CRI 90+, dimmable, pendants + downlights + floor lamps, ~1 per 4m²
- Dining: 2700-3000K, CRI 90+, dimmable pendant over table + 2-4 accent downlights
- Bedroom: 2700K, CRI 90+, dimmable, ceiling + 2 wall/bedside lights
- Master bedroom: 2700K, CRI 95+, dimmable, ceiling + wall + strip in wardrobes
- Kitchen: 3000-4000K, CRI 90+, IP44 over sink, downlights + under-cabinet strip, 1 per 4m²
- Bathroom: 3000-4000K, CRI 90+, IP44 min, mirror light + ceiling downlight
- Corridor/Hall: 3000K, IP20, downlights, 1 per 4m²
- Office/Study: 3000-4000K, CRI 80+, no-glare panels or downlights, 1 per 6m²
- Lobby/Entrance: 2700-3000K, CRI 90+, statement pendant + accent downlights
- Terrace/Outdoor: IP65, 2700-3000K, wall lights + spike/step lights
- Garage/Utility: 4000K, IP44, panels, 1 per 8m²
- Hotel room: 2700K, CRI 90+, full dimming, layered ambient + accent + task
- Restaurant: 2700K, CRI 90+, dimmable pendants over tables + ambient downlights
- Retail: 3000-4000K, CRI 90+, track heads, 1 per 3-4m²

Property level modifiers:
- basic: functional, IP20 where acceptable, dimming not required, CRI 80+
- mid: quality fixtures, selective dimming, CRI 80+
- premium: CRI 90+, full dimming, layered lighting in key spaces
- luxury: CRI 95+, tunable white, feature pendants/chandeliers, bespoke
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

        # Fallback: regex parser
        result = parse_file(file_path)
        extracted = result.get("extracted", {})
        rooms_raw = extracted.get("rooms", [])
        rooms = [{"name": r, "sqm": None, "fixtures_recommended": 2,
                  "fixture_types": ["downlight"], "color_temp": "3000K",
                  "cri_min": 80, "ip_required": "IP20", "dimmable": False, "notes": ""}
                 for r in rooms_raw]
        extracted_dict = {
            "total_sqm": extracted.get("total_sqm"),
            "num_floors": extracted.get("num_floors"),
            "property_type": extracted.get("property_type"),
            "property_level": extracted.get("property_level"),
            "style": extracted.get("style"),
            "rooms": rooms,
            "special_requirements": "",
            "extracted_notes": result.get("raw_text", "")[:500],
        }
        emit("done", "Analysis complete (basic extraction)", 100, done=True, data=extracted_dict)
        return extracted_dict

    except Exception as e:
        emit("error", f"Analysis failed: {str(e)}", done=True)
        return {}


def run_analysis_multi(file_paths: list, session_id: str, loop: asyncio.AbstractEventLoop) -> dict:
    """Analyze multiple files (PDFs) as one project — combines text and images before sending to Claude."""

    def emit(step: str, msg: str, progress: int = 0, done: bool = False, **kwargs):
        push_sync(session_id, loop, {"step": step, "msg": msg, "progress": progress, "done": done, **kwargs})

    emit("start", f"Starting analysis of {len(file_paths)} file(s)…", 5)

    try:
        from services.ai_client import get_client
        ai = get_client()

        all_raw_text = ""
        all_images_b64 = []

        for i, file_path in enumerate(file_paths):
            ext = Path(file_path).suffix.lower()
            name = Path(file_path).name
            base_pct = 10 + i * (35 // len(file_paths))
            emit("extract", f"Extracting file {i + 1}/{len(file_paths)}: {name}…", base_pct)

            if ext == ".pdf":
                try:
                    import pdfplumber
                    with pdfplumber.open(file_path) as pdf:
                        text = ""
                        for page in pdf.pages[:8]:
                            t = page.extract_text()
                            if t:
                                text += t + "\n"
                    if text.strip():
                        all_raw_text += f"\n=== DOCUMENT {i + 1}: {name} ===\n{text}"
                except Exception:
                    pass

                # Up to 2 images per file, 4 total cap
                slots = min(2, 4 - len(all_images_b64))
                if slots > 0:
                    try:
                        import fitz
                        doc = fitz.open(file_path)
                        for page_num in range(min(slots, len(doc))):
                            pix = doc[page_num].get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
                            all_images_b64.append(base64.standard_b64encode(pix.tobytes("png")).decode())
                        doc.close()
                    except Exception:
                        pass

            elif ext in (".dwg", ".dxf"):
                # For CAD files just run the single-file analyzer (CAD combine is complex)
                return _analyze_cad_with_ai(file_path, ai, emit)

        emit("images", f"Combined {len(all_images_b64)} page image(s) from {len(file_paths)} file(s)", 50)
        return _call_ai_vision(all_raw_text, all_images_b64, ai, emit)

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

    images_b64 = []
    emit("images", "Converting PDF pages to images for visual analysis…", 30)
    try:
        import fitz  # pymupdf
        doc = fitz.open(file_path)
        for page_num in range(min(4, len(doc))):
            page = doc[page_num]
            mat = fitz.Matrix(1.5, 1.5)
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
        try:
            doc = ezdxf.readfile(file_path)
        except Exception:
            # Binary DWG — try to extract readable text from binary
            emit("extract", "Binary DWG detected — extracting text (export as DXF or PDF for best results)…", 20)
            raw_bytes = Path(file_path).read_bytes()
            texts_raw = re.findall(rb'[ -~]{4,}', raw_bytes)
            raw_text = "\n".join(t.decode("ascii", errors="ignore") for t in texts_raw[:500])
            if not raw_text.strip():
                emit("error", "Cannot read DWG. Please export as DXF or PDF from AutoCAD and re-upload.", done=True)
                return {}
            emit("extract", f"Extracted {len(raw_text)} characters of text from binary DWG", 40)
            return _call_ai_vision(raw_text, [], ai, emit)

        msp = doc.modelspace()

        # Collect entities organized by layer
        layers: dict = defaultdict(lambda: {"texts": [], "areas": [], "counts": defaultdict(int)})
        all_texts = []
        all_areas = []

        for entity in msp:
            layer = entity.dxf.layer
            etype = entity.dxftype()
            layers[layer]["counts"][etype] += 1

            if etype in ("TEXT", "MTEXT"):
                try:
                    text = entity.plain_mtext() if etype == "MTEXT" else entity.dxf.text
                    if text and text.strip():
                        pos = None
                        try:
                            ins = entity.dxf.insert
                            pos = (round(ins.x, 0), round(ins.y, 0))
                        except Exception:
                            pass
                        all_texts.append({"text": text.strip(), "layer": layer, "pos": pos})
                        layers[layer]["texts"].append(text.strip())
                except Exception:
                    pass

            elif etype == "LWPOLYLINE" and entity.is_closed:
                try:
                    from ezdxf.math import area as calc_area
                    pts = list(entity.get_points())
                    if len(pts) >= 3:
                        xy = [(p[0], p[1]) for p in pts]
                        raw_area = abs(calc_area(xy))
                        sqm = _to_sqm(raw_area)
                        if sqm and 0.5 < sqm < 5000:
                            all_areas.append({"area_m2": sqm, "layer": layer})
                            layers[layer]["areas"].append(sqm)
                except Exception:
                    pass

        emit("extract", f"Parsed {len(all_texts)} text entities, {len(all_areas)} closed areas from {len(layers)} layers", 35)

        # Build rich text description for Claude
        raw_text = _build_cad_summary(layers, all_texts, all_areas)

        # Try rendering DXF to image using ezdxf drawing module
        images_b64 = []
        emit("images", "Rendering DXF floor plan to image…", 45)
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            from ezdxf.addons.drawing import RenderContext, Frontend
            from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
            import io

            fig = plt.figure(figsize=(18, 14), dpi=100)
            ax = fig.add_axes([0, 0, 1, 1])
            ctx = RenderContext(doc)
            out = MatplotlibBackend(ax)
            Frontend(ctx, out).draw_layout(msp, finalize=True)
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=100, bbox_inches="tight", facecolor="white")
            plt.close(fig)
            buf.seek(0)
            images_b64.append(base64.standard_b64encode(buf.read()).decode())
            emit("images", "Floor plan rendered successfully", 52)
        except ImportError:
            emit("images", "Visual rendering unavailable (matplotlib not installed) — using text extraction only", 52)
        except Exception as e:
            emit("images", f"Visual rendering skipped ({str(e)[:60]}) — using text extraction only", 52)

        return _call_ai_vision(raw_text, images_b64, ai, emit)

    except Exception as e:
        emit("error", f"CAD parsing failed: {e}", done=True)
        return {}


def _to_sqm(raw_area: float) -> float | None:
    """Convert raw DXF polyline area to m² with smart unit detection."""
    if raw_area <= 0:
        return None
    if raw_area < 10_000:
        return round(raw_area, 2)          # likely m² already
    if raw_area < 500_000_000:
        return round(raw_area / 10_000, 2) # likely cm²
    return round(raw_area / 1_000_000, 2)  # likely mm²


def _build_cad_summary(layers: dict, all_texts: list, all_areas: list) -> str:
    """Build a structured text description of the DXF for Claude."""
    lines = ["=== DXF FLOOR PLAN DATA ===\n"]

    # Layer overview (only layers with content)
    active_layers = {k: v for k, v in layers.items() if v["texts"] or v["areas"]}
    if active_layers:
        lines.append(f"LAYERS ({len(active_layers)} with content):")
        for name, data in sorted(active_layers.items()):
            parts = []
            if data["texts"]:
                sample = ", ".join(f'"{t}"' for t in data["texts"][:4])
                parts.append(f"texts: {sample}")
            if data["areas"]:
                areas_s = ", ".join(f"{a}m²" for a in sorted(data["areas"])[:5])
                parts.append(f"areas: {areas_s}")
            if parts:
                lines.append(f"  {name}: {' | '.join(parts)}")
        lines.append("")

    # All text entities (spatial context helps Claude identify rooms)
    if all_texts:
        lines.append(f"ALL TEXT ENTITIES ({len(all_texts)} total):")
        for t in all_texts[:150]:
            pos_str = f" @ ({t['pos'][0]:.0f},{t['pos'][1]:.0f})" if t['pos'] else ""
            lines.append(f"  [{t['layer']}] \"{t['text']}\"{pos_str}")
        lines.append("")

    # All detected areas
    if all_areas:
        sorted_areas = sorted(all_areas, key=lambda x: x["area_m2"], reverse=True)
        lines.append(f"CLOSED AREAS — likely rooms/spaces ({len(all_areas)} total):")
        for a in sorted_areas[:40]:
            lines.append(f"  {a['area_m2']} m²  (layer: {a['layer']})")
        lines.append(f"\n  Total area from polylines: {sum(a['area_m2'] for a in sorted_areas[:40]):.1f} m²")

    return "\n".join(lines)


def _call_ai_vision(raw_text: str, images_b64: list, ai, emit) -> dict:
    emit("ai", f"Sending to {ai.provider} ({ai.model})…", 58)
    try:
        text_prompt = ANALYSIS_PROMPT
        if raw_text.strip():
            text_prompt += f"\n\nEXTRACTED DATA FROM DOCUMENT:\n{raw_text[:8000]}"
        else:
            text_prompt += "\n\nPlease analyze the floor plan images above."

        emit("ai", "Claude is reading the floor plan…", 68)
        response = ai.complete_with_vision(
            text_prompt=text_prompt,
            images_b64=images_b64,
            max_tokens=4000,
        ).strip()

        if "```json" in response:
            response = response.split("```json")[1].split("```")[0].strip()
        elif "```" in response:
            response = response.split("```")[1].split("```")[0].strip()

        emit("ai", "Parsing analysis results…", 85)
        data = json.loads(response)
        emit("done", "✓ Project analysis complete", 100, done=True, data=data)
        return data

    except Exception as e:
        emit("error", f"AI analysis failed: {e}", done=True)
        return {}
