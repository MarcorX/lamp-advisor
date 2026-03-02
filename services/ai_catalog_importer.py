"""
AI-powered catalog importer.
Accepts any Excel / CSV / PDF product list and uses Claude to map it to the Lamp schema.
Falls back to column-name heuristics if no API key is present.
"""
import os
import json
import asyncio
import pandas as pd
from pathlib import Path
from sqlalchemy.orm import Session

from database import Lamp
from services.progress import push_sync


TARGET_SCHEMA = """
{
  "brand": "string — manufacturer name",
  "model": "string — product model or name",
  "category": "string — one of: downlight, pendant, spot, panel, strip, wall, floor, track, mirror, outdoor",
  "wattage": "number — power consumption in watts (W)",
  "lumens": "integer — luminous flux in lumens (lm)",
  "color_temp": "string — colour temperature e.g. '3000K', '4000K', 'tunable'",
  "cri": "integer — colour rendering index (0-100)",
  "ip_rating": "string — ingress protection e.g. 'IP20', 'IP44', 'IP65'",
  "voltage": "string — e.g. '220V', '24V'",
  "dimmable": "boolean",
  "beam_angle": "number — beam angle in degrees",
  "dimensions": "string — e.g. 'Ø120mm' or '60x60cm'",
  "color_finish": "string — e.g. 'White', 'Black Matt'",
  "indoor_outdoor": "string — 'indoor', 'outdoor', or 'both'",
  "property_level": "string — 'basic', 'mid', 'premium', or 'luxury'",
  "space_type": "string — comma-separated room types, e.g. 'living,bedroom,lobby'",
  "price_usd": "number — unit price in USD",
  "sku": "string — product code / reference",
  "description": "string — short product description"
}
"""


def run_import(file_path: str, db: Session, session_id: str, loop: asyncio.AbstractEventLoop) -> int:
    """Synchronous worker — run in a background thread."""

    def emit(step: str, msg: str, progress: int = 0, done: bool = False, **kwargs):
        push_sync(session_id, loop, {"step": step, "msg": msg, "progress": progress, "done": done, **kwargs})

    emit("reading", "Reading file…", 5)

    try:
        ext = Path(file_path).suffix.lower()
        raw_text = ""
        df_preview = ""

        if ext in (".xlsx", ".xls"):
            df = pd.read_excel(file_path)
            raw_text = f"Columns: {list(df.columns)}\n\nFirst 30 rows:\n{df.head(30).to_string()}"
            df_preview = df.to_dict(orient="records")
        elif ext == ".csv":
            df = pd.read_csv(file_path)
            raw_text = f"Columns: {list(df.columns)}\n\nFirst 30 rows:\n{df.head(30).to_string()}"
            df_preview = df.to_dict(orient="records")
        elif ext == ".pdf":
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages[:6]:
                    t = page.extract_text()
                    if t:
                        raw_text += t + "\n"
            emit("reading", f"Extracted {len(raw_text)} characters from PDF", 15)
        else:
            emit("error", f"Unsupported file type: {ext}", done=True)
            return 0

        emit("mapping", "AI is mapping columns to lamp schema…", 30)

        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        lamps_data = []

        from services.ai_client import get_client
        ai = get_client()
        if ai.is_configured():
            lamps_data = _ai_map(raw_text, ai, emit)
        else:
            emit("mapping", "No API key — using column name heuristics…", 35)
            if isinstance(df_preview, list):
                lamps_data = _heuristic_map(df_preview, emit)
            else:
                emit("error", "Cannot map PDF catalog without Claude API key.", done=True)
                return 0

        if not lamps_data:
            emit("error", "No lamps could be extracted from the file.", done=True)
            return 0

        emit("saving", f"Saving {len(lamps_data)} lamps to database…", 80)
        saved = _save_lamps(lamps_data, db)
        emit("done", f"✓ {saved} lamps imported successfully!", 100, done=True, count=saved)
        return saved

    except Exception as e:
        emit("error", f"Import failed: {str(e)}", done=True)
        return 0


def _ai_map(raw_text: str, ai, emit) -> list[dict]:
    """Ask AI to map the raw catalog data to the lamp schema."""
    try:
        prompt = f"""You are a data engineer. Below is raw product catalog data.
Map EVERY product to the JSON schema and return a JSON array.
If a field is missing or unclear, use null.
For property_level: infer from price or product description (basic <$30, mid $30-100, premium $100-300, luxury >$300).
For indoor_outdoor: infer from IP rating (IP44+ = outdoor capable).
Return ONLY a valid JSON array, no explanation.

TARGET SCHEMA:
{TARGET_SCHEMA}

CATALOG DATA:
{raw_text[:12000]}"""

        emit("mapping", f"Sending to {ai.provider} ({ai.model})…", 50)
        content = ai.complete(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=8000,
        )

        # Strip markdown fences if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        emit("mapping", "Parsing Claude response…", 70)
        return json.loads(content)

    except Exception as e:
        emit("mapping", f"AI mapping failed ({e}), falling back to heuristics…", 55)
        return []


def _heuristic_map(records: list[dict], emit) -> list[dict]:
    """Column-name based mapping (Spanish + English)."""
    col_aliases = {
        "marca": "brand", "fabricante": "brand",
        "modelo": "model", "nombre": "model",
        "categoria": "category", "tipo": "category",
        "vatios": "wattage", "watts": "wattage", "w": "wattage",
        "lumens": "lumens", "lm": "lumens",
        "temperatura": "color_temp", "temp_color": "color_temp", "cct": "color_temp",
        "irc": "cri",
        "ip": "ip_rating", "proteccion": "ip_rating",
        "voltaje": "voltage", "tension": "voltage",
        "regulable": "dimmable", "dimmer": "dimmable",
        "precio": "price_usd", "price": "price_usd", "costo": "price_usd",
        "nivel": "property_level", "gama": "property_level",
        "espacio": "space_type", "uso": "space_type",
        "interior_exterior": "indoor_outdoor",
    }
    result = []
    for row in records:
        normalized = {}
        for k, v in row.items():
            key = str(k).lower().strip().replace(" ", "_")
            mapped = col_aliases.get(key, key)
            normalized[mapped] = v
        result.append(normalized)
    emit("mapping", f"Mapped {len(result)} rows via heuristics", 70)
    return result


def _save_lamps(data: list[dict], db: Session) -> int:
    saved = 0
    for item in data:
        if not item or not item.get("brand") or not item.get("model"):
            continue
        try:
            lamp = Lamp(
                brand=str(item.get("brand") or "Unknown")[:100],
                model=str(item.get("model") or "Unknown")[:200],
                category=str(item.get("category") or "")[:50] if item.get("category") else "",
                wattage=_safe_float(item.get("wattage")),
                lumens=_safe_int(item.get("lumens")),
                color_temp=str(item.get("color_temp") or "")[:50] if item.get("color_temp") else "",
                cri=_safe_int(item.get("cri")),
                ip_rating=str(item.get("ip_rating") or "")[:20] if item.get("ip_rating") else "",
                voltage=str(item.get("voltage") or "")[:50] if item.get("voltage") else "",
                dimmable=bool(item.get("dimmable") or False),
                beam_angle=_safe_float(item.get("beam_angle")),
                dimensions=str(item.get("dimensions") or "")[:100] if item.get("dimensions") else "",
                color_finish=str(item.get("color_finish") or "")[:100] if item.get("color_finish") else "",
                indoor_outdoor=str(item.get("indoor_outdoor") or "indoor")[:20],
                property_level=str(item.get("property_level") or "mid")[:20],
                space_type=str(item.get("space_type") or "")[:200] if item.get("space_type") else "",
                price_usd=_safe_float(item.get("price_usd")),
                sku=str(item.get("sku") or "")[:100] if item.get("sku") else "",
                description=str(item.get("description") or "")[:500] if item.get("description") else "",
            )
            db.add(lamp)
            saved += 1
        except Exception:
            continue
    db.commit()
    return saved


def _safe_float(v) -> float | None:
    try:
        return float(v) if v is not None and str(v).strip() not in ("", "nan", "None", "null") else None
    except Exception:
        return None


def _safe_int(v) -> int | None:
    f = _safe_float(v)
    return int(f) if f is not None else None
