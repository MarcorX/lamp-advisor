"""
AI-powered catalog importer.
Accepts any Excel / CSV / PDF product list and uses Claude to map it to the Lamp schema.
Falls back to column-name heuristics if no API key is present.
"""
import os
import re
import json
import asyncio
import pandas as pd
from pathlib import Path
from urllib.parse import urljoin, urlparse
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
  "description": "string — short product description",
  "url": "string — product page URL (if present in the data)"
}
"""


CHUNK_SIZE = 50


def run_import(file_path: str, db: Session, session_id: str, loop: asyncio.AbstractEventLoop) -> int:
    """Synchronous worker — run in a background thread."""

    def emit(step: str, msg: str, progress: int = 0, done: bool = False, **kwargs):
        push_sync(session_id, loop, {"step": step, "msg": msg, "progress": progress, "done": done, **kwargs})

    emit("reading", "Reading file…", 5)

    try:
        ext = Path(file_path).suffix.lower()
        df = None
        raw_text = ""

        if ext in (".xlsx", ".xls"):
            df = pd.read_excel(file_path)
            emit("reading", f"Read {len(df)} rows from Excel file", 12)
        elif ext == ".csv":
            df = pd.read_csv(file_path)
            emit("reading", f"Read {len(df)} rows from CSV file", 12)
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

        from services.ai_client import get_client
        ai = get_client()
        all_lamps: list[dict] = []
        failed_rows: list[str] = []

        if df is not None:
            total_rows = len(df)
            chunks = [df.iloc[i:i + CHUNK_SIZE] for i in range(0, total_rows, CHUNK_SIZE)]
            num_chunks = len(chunks)
            emit("mapping", f"Processing {total_rows} rows in {num_chunks} chunk(s) of {CHUNK_SIZE}…", 20)

            if ai.is_configured():
                ai_chunk_failures = 0
                for idx, chunk_df in enumerate(chunks):
                    chunk_num = idx + 1
                    chunk_progress = 20 + int((idx / num_chunks) * 55)
                    emit("mapping", f"AI mapping chunk {chunk_num}/{num_chunks} ({len(chunk_df)} rows)…", chunk_progress)
                    # CSV is compact and never truncates values (unlike to_string)
                    chunk_text = chunk_df.to_csv(index=False)
                    results, chunk_failures = _ai_map_chunk(chunk_text, ai, emit, chunk_num, num_chunks)
                    all_lamps.extend(results)
                    failed_rows.extend(chunk_failures)
                    if not results:
                        ai_chunk_failures += 1
                    emit("mapping", f"Chunk {chunk_num}/{num_chunks}: {len(results)} lamps mapped", chunk_progress + 2)

                # If ALL chunks failed AI mapping, fall back to heuristics
                if ai_chunk_failures == num_chunks and num_chunks > 0:
                    emit("mapping", f"⚠ AI mapping failed for all {num_chunks} chunks — falling back to column-name heuristics…", 72)
                    all_lamps = _heuristic_map(df.to_dict(orient="records"), emit)
                    failed_rows = []  # reset — heuristic rows are reported differently
            else:
                emit("mapping", "No API key — using column name heuristics…", 35)
                all_lamps = _heuristic_map(df.to_dict(orient="records"), emit)
        else:
            # PDF path — single call, no chunking
            if ai.is_configured():
                all_lamps, failed_rows = _ai_map_chunk(raw_text, ai, emit, 1, 1)
            else:
                emit("error", "Cannot map PDF catalog without an AI API key.", done=True)
                return 0

        if not all_lamps:
            emit("error", "No lamps could be extracted from the file.", done=True)
            return 0

        emit("saving", f"Saving {len(all_lamps)} lamps to database…", 80)
        saved, save_failures, url_map = _save_lamps_tracked(all_lamps, db)
        failed_rows.extend(save_failures)

        # Fetch product page images for lamps that have a URL
        img_fetched = 0
        if url_map:
            emit("images", f"Fetching product images for {len(url_map)} lamp(s)…", 85)
            for lamp_id, product_url in url_map:
                img_url = _fetch_product_image(product_url)
                if img_url:
                    lamp = db.get(Lamp, lamp_id)
                    if lamp:
                        lamp.image_url = img_url
                        img_fetched += 1
            if img_fetched:
                db.commit()
            emit("images", f"Found images for {img_fetched}/{len(url_map)} lamp(s)", 95)

        n_failed = len(failed_rows)
        suffix = f", {n_failed} rows skipped" if n_failed else ""
        img_suffix = f", {img_fetched} images fetched" if img_fetched else ""
        emit("done", f"✓ {saved} lamps imported successfully{suffix}{img_suffix}", 100,
             done=True, count=saved, failed=n_failed, failed_samples=failed_rows[:5])
        return saved

    except Exception as e:
        emit("error", f"Import failed: {str(e)}", done=True)
        return 0


def _ai_map_chunk(chunk_text: str, ai, emit, chunk_num: int, total_chunks: int) -> tuple:
    """Map one chunk of catalog text to lamp schema. Returns (lamps, failure_descriptions)."""
    failures = []
    try:
        prompt = f"""You are a data engineer. Below is raw product catalog data (chunk {chunk_num} of {total_chunks}).
Map EVERY product row to the JSON schema and return a JSON array.
If a field is missing or unclear, use null.
For property_level: infer from price or description (basic <$30, mid $30-100, premium $100-300, luxury >$300).
For indoor_outdoor: infer from IP rating (IP44+ = outdoor capable).
Return ONLY a valid JSON array, no explanation, no markdown fences.

TARGET SCHEMA:
{TARGET_SCHEMA}

CATALOG DATA:
{chunk_text}"""

        content = ai.complete(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=8000,
        )

        # Strip markdown fences if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        # Bracket-scan fallback: find the outermost JSON array even if
        # Claude added preamble/postamble text around it
        content = content.strip()
        if not content.startswith("["):
            start = content.find("[")
            end = content.rfind("]")
            if start != -1 and end > start:
                content = content[start:end + 1]

        results = json.loads(content)
        if not isinstance(results, list):
            failures.append(f"chunk {chunk_num}: AI returned non-list response")
            return [], failures
        return results, failures

    except json.JSONDecodeError as e:
        failures.append(f"chunk {chunk_num}: JSON parse error — {str(e)[:100]}")
        return [], failures
    except Exception as e:
        failures.append(f"chunk {chunk_num}: AI call failed — {str(e)[:100]}")
        return [], failures


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
        "url": "url", "link": "url", "enlace": "url", "producto": "url",
        "product_url": "url", "product_link": "url", "web": "url",
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


def _save_lamps_tracked(data: list[dict], db: Session) -> tuple:
    """Save lamps tracking per-row failures. Returns (saved_count, failure_descriptions, url_map).
    url_map is a list of (lamp_id, product_url) for lamps that have a product page URL."""
    saved = 0
    failures = []
    url_map = []
    for idx, item in enumerate(data):
        if not item:
            failures.append(f"row {idx + 1}: empty record")
            continue
        if not item.get("brand"):
            failures.append(f"row {idx + 1}: missing brand (model: {str(item.get('model', '?'))[:40]})")
            continue
        if not item.get("model"):
            failures.append(f"row {idx + 1}: missing model (brand: {str(item.get('brand', '?'))[:40]})")
            continue
        try:
            product_url = str(item.get("url") or "").strip()[:500] or None
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
                datasheet_url=product_url or "",
                description=str(item.get("description") or "")[:500] if item.get("description") else "",
            )
            db.add(lamp)
            db.flush()  # get the auto-assigned lamp.id before committing
            if product_url:
                url_map.append((lamp.id, product_url))
            saved += 1
        except Exception as ex:
            failures.append(f"row {idx + 1}: DB error — {str(ex)[:60]}")
            continue
    db.commit()
    return saved, failures, url_map


def _fetch_product_image(url: str) -> str | None:
    """Fetch a product page and return its main image URL (og:image preferred).
    Returns None on any error or if no image is found."""
    try:
        import urllib.request
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; LampAdvisor/1.0; +https://lampadvisor.com)"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read(200_000).decode("utf-8", errors="ignore")

        base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"

        # og:image — two attribute orderings
        for pattern in (
            r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\'>\s]+)["\']',
            r'<meta[^>]+content=["\']([^"\'>\s]+)["\'][^>]+property=["\']og:image["\']',
            r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\'>\s]+)["\']',
            r'<meta[^>]+content=["\']([^"\'>\s]+)["\'][^>]+name=["\']twitter:image["\']',
        ):
            m = re.search(pattern, html, re.IGNORECASE)
            if m:
                img = m.group(1).strip()
                return urljoin(base, img) if img.startswith("/") else img

        return None
    except Exception:
        return None


def _safe_float(v) -> float | None:
    try:
        return float(v) if v is not None and str(v).strip() not in ("", "nan", "None", "null") else None
    except Exception:
        return None


def _safe_int(v) -> int | None:
    f = _safe_float(v)
    return int(f) if f is not None else None
