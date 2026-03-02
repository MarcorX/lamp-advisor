"""
Parse PDF, DWG, and DXF project files to extract lighting-relevant information.
"""
import os
import re
import json
from pathlib import Path


def parse_file(file_path: str) -> dict:
    """Main entry point - detect file type and parse accordingly."""
    ext = Path(file_path).suffix.lower()
    if ext == ".pdf":
        return parse_pdf(file_path)
    elif ext in (".dwg", ".dxf"):
        return parse_cad(file_path)
    return {"raw_text": "", "extracted": {}}


def parse_pdf(file_path: str) -> dict:
    """Extract text and infer project details from a PDF."""
    try:
        import pdfplumber
        raw_text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    raw_text += text + "\n"
        extracted = extract_project_details(raw_text)
        return {"raw_text": raw_text[:8000], "extracted": extracted}
    except Exception as e:
        return {"raw_text": "", "extracted": {}, "error": str(e)}


def parse_cad(file_path: str) -> dict:
    """Extract area, layer names, and text from DWG/DXF files."""
    try:
        import ezdxf
        doc = ezdxf.readfile(file_path)
        msp = doc.modelspace()

        texts = []
        areas = []
        layer_names = set()

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
                            areas.append(round(a / 1_000_000, 2))  # mm² → m²
                except Exception:
                    pass

        raw_text = "\n".join(texts)
        extracted = extract_project_details(raw_text)

        # Supplement with CAD-specific info
        if areas:
            total = sum(areas)
            extracted.setdefault("total_sqm", round(total, 1))
        if layer_names:
            rooms = infer_rooms_from_layers(layer_names)
            if rooms and not extracted.get("rooms"):
                extracted["rooms"] = rooms

        return {"raw_text": raw_text[:8000], "extracted": extracted, "layers": list(layer_names)[:50]}
    except Exception as e:
        return {"raw_text": "", "extracted": {}, "error": str(e)}


def extract_project_details(text: str) -> dict:
    """Use regex heuristics to pull key details from extracted text."""
    result = {}
    t = text.lower()

    # Total area
    area_patterns = [
        r"(\d+(?:[.,]\d+)?)\s*(?:m²|m2|sqm|sq\.?m|metros?\s*cuadrados?)",
        r"area[:\s]+(\d+(?:[.,]\d+)?)",
        r"superficie[:\s]+(\d+(?:[.,]\d+)?)",
    ]
    for pat in area_patterns:
        m = re.search(pat, t)
        if m:
            val = float(m.group(1).replace(",", "."))
            if 10 < val < 100_000:
                result["total_sqm"] = val
                break

    # Number of floors
    floors = re.search(r"(\d+)\s*(?:pisos?|floors?|plant[ae]s?|niveles?|levels?)", t)
    if floors:
        result["num_floors"] = int(floors.group(1))

    # Property type hints
    type_keywords = {
        "hotel": "hotel",
        "residencial": "residential",
        "residential": "residential",
        "vivienda": "residential",
        "casa": "residential",
        "apartment": "residential",
        "departamento": "residential",
        "oficina": "office",
        "office": "office",
        "comercial": "commercial",
        "commercial": "commercial",
        "retail": "retail",
        "tienda": "retail",
        "restaurant": "restaurant",
        "restaurante": "restaurant",
    }
    for kw, ptype in type_keywords.items():
        if kw in t:
            result["property_type"] = ptype
            break

    # Level hints
    level_keywords = {
        "lujo": "luxury", "luxury": "luxury", "premium": "premium",
        "high-end": "premium", "exclusivo": "luxury",
        "económico": "basic", "economico": "basic", "basic": "basic",
        "mid": "mid", "estándar": "mid", "estandar": "mid", "standard": "mid",
    }
    for kw, level in level_keywords.items():
        if kw in t:
            result["property_level"] = level
            break

    # Rooms mentioned
    room_keywords = [
        "living", "sala", "comedor", "dining", "kitchen", "cocina",
        "bedroom", "dormitorio", "habitación", "bathroom", "baño",
        "office", "oficina", "lobby", "hall", "corridor", "pasillo",
        "terrace", "terraza", "garage", "garaje", "gym", "gimnasio",
        "pool", "piscina", "spa", "library", "biblioteca",
    ]
    found_rooms = [r for r in room_keywords if r in t]
    if found_rooms:
        result["rooms"] = list(set(found_rooms))

    # Style hints
    style_keywords = ["modern", "moderno", "classic", "clásico", "minimalist",
                      "industrial", "rustic", "rústico", "nordic", "nórdico"]
    for kw in style_keywords:
        if kw in t:
            result["style"] = kw
            break

    return result


def infer_rooms_from_layers(layers: set) -> list:
    """Guess room types from CAD layer names."""
    room_map = {
        "living": "living", "sala": "living", "dining": "dining", "comedor": "dining",
        "kitchen": "kitchen", "cocina": "kitchen", "bed": "bedroom", "dorm": "bedroom",
        "bath": "bathroom", "baño": "bathroom", "office": "office", "lobby": "lobby",
        "hall": "hall", "terrace": "terrace", "garage": "garage",
    }
    found = set()
    for layer in layers:
        l = layer.lower()
        for kw, room in room_map.items():
            if kw in l:
                found.add(room)
    return list(found)
