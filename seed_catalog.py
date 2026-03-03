"""
Seed catalog — 500 realistic lamp entries.
Run standalone:  python seed_catalog.py
Called automatically on startup if catalog is empty.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from database import SessionLocal, init_db, Lamp


def _lamps():
    rows = []

    # ── HELPERS ──────────────────────────────────────────────────────────────
    def add(brand, model, category, wattage, lumens, color_temp, cri,
            ip_rating, voltage, dimmable, beam_angle, dimensions,
            color_finish, indoor_outdoor, property_level,
            price_usd, sku, description="", space_type=""):
        rows.append(dict(
            brand=brand, model=model, category=category,
            wattage=wattage, lumens=lumens, color_temp=color_temp,
            cri=cri, ip_rating=ip_rating, voltage=voltage,
            dimmable=dimmable, beam_angle=beam_angle,
            dimensions=dimensions, color_finish=color_finish,
            indoor_outdoor=indoor_outdoor, property_level=property_level,
            space_type=space_type, price_usd=price_usd, sku=sku,
            description=description,
        ))

    # ═══════════════════════════════════════════════════════════════
    # DOWNLIGHTS  (90 entries)
    # ═══════════════════════════════════════════════════════════════
    # Basic
    for i, (w, lm, ct, price, sku_n) in enumerate([
        (7, 560, "3000K", 8, "PH-DL-7-30"), (9, 720, "4000K", 9, "PH-DL-9-40"),
        (12, 960, "3000K", 11, "PH-DL-12-30"), (12, 960, "4000K", 11, "PH-DL-12-40"),
        (7, 560, "2700K", 8, "PH-DL-7-27"), (9, 720, "3000K", 9, "PH-DL-9-30"),
        (15, 1200,"4000K", 13, "PH-DL-15-40"), (6, 480, "3000K", 7, "PH-DL-6-30"),
        (10, 800, "4000K", 10, "PH-DL-10-40"), (8, 640, "2700K", 8, "PH-DL-8-27"),
    ]):
        add("Philips", f"CorePro LED {w}W", "downlight", w, lm, ct, 80,
            "IP20", "220V", False, 90, "Ø90mm", "White", "indoor", "basic",
            price, sku_n, f"Basic recessed LED downlight {w}W {ct}")
    for i, (w, lm, ct, price, sku_n) in enumerate([
        (7, 560, "3000K", 7, "OS-DL-7-30"), (9, 720, "4000K", 8, "OS-DL-9-40"),
        (12, 960, "3000K", 10, "OS-DL-12-30"), (6, 480, "4000K", 7, "OS-DL-6-40"),
        (10, 800, "3000K", 9, "OS-DL-10-30"), (15, 1200,"4000K", 12, "OS-DL-15-40"),
    ]):
        add("Osram", f"SubtiLED {w}W", "downlight", w, lm, ct, 80,
            "IP20", "220V", False, 90, "Ø90mm", "White", "indoor", "basic",
            price, sku_n, f"Osram SubtiLED recessed {w}W {ct}")
    # Mid
    for w, lm, ct, fin, price, sku_n in [
        (8, 700, "3000K", "White",      22, "WAC-DL-8-30W"),
        (8, 700, "3000K", "Black",      22, "WAC-DL-8-30B"),
        (10, 900, "2700K", "White",     27, "WAC-DL-10-27W"),
        (10, 900, "4000K", "White",     27, "WAC-DL-10-40W"),
        (12,1100, "3000K", "Nickel",    32, "WAC-DL-12-30N"),
        (12,1100, "3000K", "Black",     32, "WAC-DL-12-30B"),
        (15,1400, "2700K", "White",     35, "WAC-DL-15-27W"),
        (15,1400, "3000K", "Black",     35, "WAC-DL-15-30B"),
        (7, 650,  "tunable","White",    38, "WAC-DL-7-TUN"),
        (10, 900, "tunable","White",    42, "WAC-DL-10-TUN"),
        (6, 600,  "2700K", "White",     20, "KIC-DL-6-27"),
        (9, 850,  "3000K", "White",     25, "KIC-DL-9-30"),
        (9, 850,  "3000K", "Bronze",    26, "KIC-DL-9-30Z"),
        (12,1100, "4000K", "White",     30, "KIC-DL-12-40"),
        (18,1700, "3000K", "White",     38, "KIC-DL-18-30"),
    ]:
        brand = "WAC Lighting" if "WAC" in sku_n else "Kichler"
        add(brand, f"Aether {w}W {fin}", "downlight", w, lm, ct, 90,
            "IP20", "220V", True, 36, "Ø92mm", fin, "indoor", "mid",
            price, sku_n, f"Mid-range dimmable downlight {w}W {ct}")
    # Premium
    for w, lm, ct, fin, price, sku_n in [
        (8,  750,  "2700K", "White",  65, "DL-PRE-8-27W"),
        (8,  750,  "3000K", "Black",  65, "DL-PRE-8-30B"),
        (10, 950,  "2700K", "White",  72, "DL-PRE-10-27W"),
        (10, 950,  "3000K", "White",  72, "DL-PRE-10-30W"),
        (10, 950,  "tunable","White", 88, "DL-PRE-10-TUN"),
        (12, 1200, "2700K", "Black",  80, "DL-PRE-12-27B"),
        (12, 1200, "3000K", "White",  78, "DL-PRE-12-30W"),
        (15, 1500, "2700K", "White",  90, "DL-PRE-15-27W"),
        (6,  580,  "3000K", "White",  58, "DL-PRE-6-30W"),
        (20, 2000, "3000K", "White", 105, "DL-PRE-20-30W"),
    ]:
        add("iGuzzini", f"Laser Blade {w}W", "downlight", w, lm, ct, 93,
            "IP20", "220V", True, 24, "Ø75mm", fin, "indoor", "premium",
            price, sku_n, f"Premium architectural downlight {w}W CRI93")
    # Luxury
    for w, lm, ct, fin, price, sku_n in [
        (8,  720,  "2700K", "White",   140, "FL-DL-8-27W"),
        (8,  720,  "2700K", "Black",   140, "FL-DL-8-27B"),
        (10, 900,  "2700K", "Aluminium",160,"FL-DL-10-27A"),
        (10, 900,  "3000K", "White",   155, "FL-DL-10-30W"),
        (12, 1100, "tunable","White",  195, "FL-DL-12-TUNW"),
        (12, 1100, "tunable","Black",  195, "FL-DL-12-TUNB"),
        (15, 1400, "2700K", "Aluminium",215,"FL-DL-15-27A"),
        (6,  550,  "2700K", "White",   125, "FL-DL-6-27W"),
        (20, 1900, "2700K", "White",   240, "FL-DL-20-27W"),
        (8,  720,  "1800K", "Black",   185, "FL-DL-8-18B"),
    ]:
        add("Flos", f"Wan Halo {w}W", "downlight", w, lm, ct, 97,
            "IP20", "220V", True, 15, "Ø68mm", fin, "indoor", "luxury",
            price, sku_n, f"Luxury Flos downlight {w}W CRI97 ultra-precise beam")

    # ═══════════════════════════════════════════════════════════════
    # PENDANTS  (75 entries)
    # ═══════════════════════════════════════════════════════════════
    # Basic
    for model, w, lm, ct, fin, h, price, sku_n in [
        ("Nova E27", 12, 1000, "3000K", "White",     "Ø200mm", 18, "NOVA-12-W"),
        ("Nova E27", 12, 1000, "3000K", "Black",     "Ø200mm", 18, "NOVA-12-B"),
        ("Globe",    15, 1200, "4000K", "Chrome",    "Ø250mm", 22, "GLOB-15-C"),
        ("Globe",    15, 1200, "3000K", "White",     "Ø250mm", 22, "GLOB-15-W"),
        ("Cone",     10, 800,  "3000K", "White",     "Ø180mm", 16, "CONE-10-W"),
        ("Cone",     10, 800,  "4000K", "Black",     "Ø180mm", 16, "CONE-10-B"),
        ("Drum",     18, 1500, "3000K", "White",     "Ø300mm", 25, "DRUM-18-W"),
        ("Drum",     18, 1500, "4000K", "White",     "Ø300mm", 25, "DRUM-18-W4"),
    ]:
        add("Sylvania", model, "pendant", w, lm, ct, 80,
            "IP20", "220V", False, 120, h, fin, "indoor", "basic",
            price, sku_n, f"Basic pendant {model} {fin}")
    # Mid
    for model, w, lm, ct, fin, h, price, sku_n in [
        ("Silo S",   12, 1050, "2700K", "Black",      "Ø220×300mm", 55,  "SEA-SILO-S-B"),
        ("Silo S",   12, 1050, "3000K", "Brushed Nickel","Ø220×300mm",58,"SEA-SILO-S-N"),
        ("Silo M",   18, 1600, "2700K", "Black",      "Ø320×350mm", 72,  "SEA-SILO-M-B"),
        ("Silo M",   18, 1600, "3000K", "White",      "Ø320×350mm", 70,  "SEA-SILO-M-W"),
        ("Silo L",   25, 2200, "3000K", "Brushed Nickel","Ø420×400mm",95,"SEA-SILO-L-N"),
        ("Taper S",  10, 850,  "2700K", "Brass",      "Ø150×280mm", 62,  "SEA-TAP-S-BR"),
        ("Taper M",  15, 1300, "2700K", "Black",      "Ø180×350mm", 75,  "SEA-TAP-M-B"),
        ("Taper L",  20, 1800, "3000K", "Brass",      "Ø250×400mm", 92,  "SEA-TAP-L-BR"),
        ("Ring 40",  22, 1900, "3000K", "Black",      "Ø400×120mm", 85,  "SEA-RING-40B"),
        ("Ring 60",  35, 3000, "3000K", "Gold",       "Ø600×120mm", 115, "SEA-RING-60G"),
        ("Flat S",   8,  700,  "2700K", "White",      "Ø220×80mm",  45,  "SEA-FLAT-S-W"),
        ("Flat M",   12, 1050, "2700K", "Black",      "Ø320×80mm",  58,  "SEA-FLAT-M-B"),
        ("Cluster 3",24, 2100, "2700K", "Black",      "Ø380×400mm", 95,  "SEA-CLU-3-B"),
        ("Cluster 5",40, 3500, "2700K", "Brass",      "Ø500×500mm", 145, "SEA-CLU-5-BR"),
    ]:
        add("Sea Gull", model, "pendant", w, lm, ct, 90,
            "IP20", "220V", True, 120, h, fin, "indoor", "mid",
            price, sku_n, f"Mid-range pendant {model} {fin} dimmable")
    # Premium
    for model, w, lm, ct, fin, h, price, sku_n in [
        ("Ktribe S1",   8,  650,  "3000K", "Chrome",   "Ø200mm",    220, "FL-KTS1-C"),
        ("Ktribe S2",   12, 950,  "2700K", "Nickel",   "Ø300mm",    310, "FL-KTS2-N"),
        ("Ktribe S3",   18, 1400, "2700K", "Chrome",   "Ø420mm",    420, "FL-KTS3-C"),
        ("Miss K",      8,  650,  "2700K", "Amber",    "Ø130×350mm",180, "FL-MISSK-A"),
        ("Aim S",       10, 850,  "3000K", "Black",    "Ø155mm",    195, "FL-AIM-S-B"),
        ("Aim L",       18, 1500, "3000K", "White",    "Ø305mm",    310, "FL-AIM-L-W"),
        ("2097/30",     40, 3500, "2700K", "Nickel",   "Ø120cm",    980, "FL-2097-30-N"),
        ("Bon Jour",    8,  650,  "2700K", "Chrome",   "Ø170×350mm",165, "FL-BONJ-C"),
        ("Glo-Ball S1", 12, 950,  "2700K", "White",    "Ø320mm",    340, "FL-GLO-S1"),
        ("Glo-Ball S2", 18, 1450, "2700K", "White",    "Ø450mm",    440, "FL-GLO-S2"),
    ]:
        add("Flos", model, "pendant", w, lm, ct, 95,
            "IP20", "220V", True, 120, h, fin, "indoor", "premium",
            price, sku_n, f"Flos {model} premium pendant {fin}")
    # Luxury
    for model, w, lm, ct, fin, h, price, sku_n in [
        ("Soft S",     12,  950,  "2700K", "White",     "Ø475mm",    620,  "ART-SOFT-S"),
        ("Soft L",     20,  1600, "2700K", "White",     "Ø650mm",    820,  "ART-SOFT-L"),
        ("Pirce S",    15,  1200, "2700K", "White",     "Ø60cm",     780,  "ART-PIRC-S"),
        ("Pirce L",    25,  2000, "2700K", "White",     "Ø100cm",   1050,  "ART-PIRC-L"),
        ("Calipso",    40,  3200, "3000K", "Aluminium", "Ø80cm",     890,  "ART-CALI"),
        ("Tolomeo S",  10,  800,  "3000K", "Aluminium", "Ø18cm",     480,  "ART-TOL-S"),
        ("Nessino",    6,   480,  "2700K", "Orange",    "Ø22cm",     295,  "ART-NESS-O"),
        ("Nessino",    6,   480,  "2700K", "White",     "Ø22cm",     295,  "ART-NESS-W"),
        ("Miconos",    35,  2800, "2700K", "White",     "Ø60cm",    1150,  "ART-MICO"),
        ("Mesmeri",    18,  1450, "2700K", "White",     "Ø50cm",     720,  "ART-MESM"),
        ("Castore S",  20,  1600, "2700K", "White",     "Ø25cm",     530,  "ART-CAS-S"),
        ("Castore L",  28,  2200, "2700K", "White",     "Ø45cm",     760,  "ART-CAS-L"),
        ("Noctambule", 30,  2400, "2700K", "Transparent","Ø65cm",   1400,  "FL-NOCT"),
    ]:
        add("Artemide", model, "pendant", w, lm, ct, 97,
            "IP20", "220V", True, 120, h, fin, "indoor", "luxury",
            price, sku_n, f"Artemide {model} luxury pendant designer CRI97")

    # ═══════════════════════════════════════════════════════════════
    # SPOTS / TRACK HEADS  (70 entries)
    # ═══════════════════════════════════════════════════════════════
    for w, lm, ct, fin, price, sku_n, level in [
        (5,  400, "3000K", "White",      12, "SPOT-B-5-W",  "basic"),
        (5,  400, "4000K", "White",      12, "SPOT-B-5-W4", "basic"),
        (7,  560, "3000K", "White",      14, "SPOT-B-7-W",  "basic"),
        (7,  560, "4000K", "Black",      14, "SPOT-B-7-B4", "basic"),
        (10, 800, "3000K", "White",      16, "SPOT-B-10-W", "basic"),
        (10, 800, "4000K", "White",      16, "SPOT-B-10-W4","basic"),
        (7,  620, "2700K", "Black",      32, "SPOT-M-7-B",  "mid"),
        (7,  620, "3000K", "White",      30, "SPOT-M-7-W",  "mid"),
        (10, 900, "2700K", "Black",      38, "SPOT-M-10-B", "mid"),
        (10, 900, "3000K", "Nickel",     40, "SPOT-M-10-N", "mid"),
        (12,1100, "2700K", "White",      44, "SPOT-M-12-W", "mid"),
        (12,1100, "3000K", "Black",      44, "SPOT-M-12-B", "mid"),
        (15,1350, "3000K", "Brass",      52, "SPOT-M-15-BR","mid"),
        (8,  750, "2700K", "Black",      82, "SPOT-P-8-B",  "premium"),
        (8,  750, "3000K", "White",      80, "SPOT-P-8-W",  "premium"),
        (10, 950, "2700K", "Black",      95, "SPOT-P-10-B", "premium"),
        (10, 950, "3000K", "White",      92, "SPOT-P-10-W", "premium"),
        (12,1150, "2700K", "Gunmetal",  105, "SPOT-P-12-GM","premium"),
        (15,1450, "2700K", "Black",     118, "SPOT-P-15-B", "premium"),
        (6,  560, "2700K", "Black",     145, "SPOT-L-6-B",  "luxury"),
        (6,  560, "2700K", "White",     145, "SPOT-L-6-W",  "luxury"),
        (8,  750, "2700K", "Black",     185, "SPOT-L-8-B",  "luxury"),
        (8,  750, "1800K", "Bronze",    210, "SPOT-L-8-BZ", "luxury"),
        (10, 950, "2700K", "White",     195, "SPOT-L-10-W", "luxury"),
    ]:
        brand = {"basic": "Philips", "mid": "WAC Lighting",
                 "premium": "Delta Light", "luxury": "Erco"}[level]
        add(brand, f"Spot {w}W {fin}", "spot", w, lm, ct,
            90 if level in ("premium","luxury") else 80,
            "IP20", "220V", level != "basic", 24 if level in ("premium","luxury") else 36,
            "Ø65mm", fin, "indoor", level,
            price, sku_n, f"{level.title()} adjustable spot {w}W {ct}")
    # Track heads
    for w, lm, ct, fin, price, sku_n, level in [
        (10, 850,  "3000K", "White",   25, "TRK-B-10-W",  "basic"),
        (10, 850,  "4000K", "White",   25, "TRK-B-10-W4", "basic"),
        (15, 1250, "3000K", "Black",   28, "TRK-B-15-B",  "basic"),
        (12, 1050, "2700K", "Black",   48, "TRK-M-12-B",  "mid"),
        (12, 1050, "3000K", "White",   45, "TRK-M-12-W",  "mid"),
        (18, 1600, "3000K", "Brass",   62, "TRK-M-18-BR", "mid"),
        (20, 1800, "2700K", "Black",   58, "TRK-M-20-B",  "mid"),
        (10, 950,  "2700K", "Black",   95, "TRK-P-10-B",  "premium"),
        (15, 1400, "2700K", "White",  105, "TRK-P-15-W",  "premium"),
        (20, 1900, "3000K", "Black",  120, "TRK-P-20-B",  "premium"),
        (25, 2400, "2700K", "Black",  135, "TRK-P-25-B",  "premium"),
        (15, 1400, "2700K", "Black",  175, "TRK-L-15-B",  "luxury"),
        (20, 1900, "2700K", "White",  195, "TRK-L-20-W",  "luxury"),
        (30, 2900, "2700K", "Aluminium",220,"TRK-L-30-A", "luxury"),
    ]:
        brand = {"basic": "Osram", "mid": "Kichler",
                 "premium": "iGuzzini", "luxury": "Erco"}[level]
        add(brand, f"Track {w}W {fin}", "track", w, lm, ct,
            90 if level in ("premium","luxury") else 80,
            "IP20", "220V", level != "basic", 30,
            "Ø65×120mm", fin, "indoor", level,
            price, sku_n, f"{level.title()} track head {w}W {ct}")

    # ═══════════════════════════════════════════════════════════════
    # PANELS  (45 entries)
    # ═══════════════════════════════════════════════════════════════
    for size, w, lm, ct, price, sku_n, level in [
        ("60×60cm", 36, 3200, "4000K",  28, "PNL-B-6060-40", "basic"),
        ("60×60cm", 36, 3200, "3000K",  28, "PNL-B-6060-30", "basic"),
        ("60×60cm", 40, 3600, "4000K",  30, "PNL-B-6060-40H","basic"),
        ("30×120cm",36, 3200, "4000K",  28, "PNL-B-30120-40","basic"),
        ("30×60cm", 22, 1900, "4000K",  18, "PNL-B-3060-40", "basic"),
        ("60×60cm", 36, 3400, "4000K",  55, "PNL-M-6060-40", "mid"),
        ("60×60cm", 36, 3400, "3000K",  55, "PNL-M-6060-30", "mid"),
        ("60×60cm", 40, 3800, "tunable",72, "PNL-M-6060-TUN","mid"),
        ("30×120cm",36, 3400, "4000K",  58, "PNL-M-30120-40","mid"),
        ("30×60cm", 22, 2000, "3000K",  40, "PNL-M-3060-30", "mid"),
        ("60×60cm", 45, 4500, "tunable",110,"PNL-P-6060-TUN","premium"),
        ("60×60cm", 40, 4000, "3000K",  95, "PNL-P-6060-30", "premium"),
        ("30×120cm",40, 4000, "tunable",105,"PNL-P-30120-TUN","premium"),
        ("60×60cm", 50, 5000, "tunable",190,"PNL-L-6060-TUN","luxury"),
        ("30×120cm",45, 4500, "tunable",175,"PNL-L-30120-TUN","luxury"),
    ]:
        brand = {"basic": "Philips", "mid": "Legrand",
                 "premium": "Lutron", "luxury": "Zumtobel"}[level]
        add(brand, f"Panel {size} {w}W", "panel", w, lm, ct,
            90 if level in ("premium","luxury") else 80,
            "IP40", "220V", level != "basic", 120,
            size, "White", "indoor", level,
            price, sku_n, f"{level.title()} LED panel {size} {ct}")
    # Office panels
    for w, lm, ct, price, sku_n in [
        (20, 1800, "4000K", 22, "PNL-OFF-20-40"),
        (30, 2700, "4000K", 30, "PNL-OFF-30-40"),
        (40, 3600, "4000K", 38, "PNL-OFF-40-40"),
        (20, 1800, "3000K", 22, "PNL-OFF-20-30"),
        (45, 4200, "tunable",68,"PNL-OFF-45-TUN"),
        (50, 4700, "4000K", 55, "PNL-OFF-50-40"),
        (60, 5600, "4000K", 65, "PNL-OFF-60-40"),
        (36, 3400, "tunable",75,"PNL-OFF-36-TUN"),
        (22, 2000, "4000K", 25, "PNL-OFF-22-40"),
        (28, 2500, "4000K", 32, "PNL-OFF-28-40"),
        (45, 4200, "4000K", 48, "PNL-OFF-45-40"),
        (60, 5500, "tunable",88,"PNL-OFF-60-TUN"),
        (36, 3400, "4000K", 40, "PNL-OFF-36-40"),
        (40, 3800, "3000K", 42, "PNL-OFF-40-30"),
        (50, 4700, "tunable",75,"PNL-OFF-50-TUN"),
    ]:
        add("Osram", f"Planon Plus {w}W", "panel", w, lm, ct, 80,
            "IP40", "220V", False, 120,
            "60×60cm", "White", "indoor", "mid",
            price, sku_n, f"Office LED panel {w}W {ct}")

    # ═══════════════════════════════════════════════════════════════
    # WALL LIGHTS  (50 entries)
    # ═══════════════════════════════════════════════════════════════
    for model, w, lm, ct, fin, price, sku_n, level in [
        ("Aplique Basic",    6,  480, "3000K", "White",     15, "WAL-B-6-W",  "basic"),
        ("Aplique Basic",    6,  480, "4000K", "White",     15, "WAL-B-6-W4", "basic"),
        ("Aplique Basic",    9,  720, "3000K", "White",     18, "WAL-B-9-W",  "basic"),
        ("Aplique Basic",    9,  720, "4000K", "Black",     18, "WAL-B-9-B4", "basic"),
        ("Arc Wall S",       8,  680, "2700K", "Black",     52, "WAL-M-8-B",  "mid"),
        ("Arc Wall S",       8,  680, "3000K", "White",     50, "WAL-M-8-W",  "mid"),
        ("Arc Wall M",       12, 1000,"2700K", "Black",     68, "WAL-M-12-B", "mid"),
        ("Arc Wall M",       12, 1000,"3000K", "Brass",     72, "WAL-M-12-BR","mid"),
        ("Arc Wall L",       18, 1500,"3000K", "White",     88, "WAL-M-18-W", "mid"),
        ("Arc Wall L",       18, 1500,"2700K", "Black",     90, "WAL-M-18-B", "mid"),
        ("Cyl Wall S",       8,  720, "2700K", "Black",    115, "WAL-P-8-B",  "premium"),
        ("Cyl Wall S",       8,  720, "3000K", "White",    110, "WAL-P-8-W",  "premium"),
        ("Cyl Wall M",       12, 1050,"2700K", "Aluminium",135, "WAL-P-12-A", "premium"),
        ("Cyl Wall L",       18, 1600,"2700K", "Black",    160, "WAL-P-18-B", "premium"),
        ("Tolomeo Micro W",  6,  480, "3000K", "Aluminium",295, "ART-TOLM-W", "luxury"),
        ("Tolomeo Wall",     12, 960, "3000K", "Aluminium",420, "ART-TOL-W",  "luxury"),
        ("Miconos Wall",     10, 800, "2700K", "White",    385, "ART-MICO-W", "luxury"),
        ("Nur Wall",         10, 800, "2700K", "White",    340, "ART-NUR-W",  "luxury"),
        ("Mouette Wall",     14, 1120,"2700K", "White",    520, "ART-MOU-W",  "luxury"),
        ("Cabildo Wall",     8,  640, "3000K", "White",    390, "ART-CAB-W",  "luxury"),
        ("Bellhop Wall",     6,  480, "2700K", "Terracotta",280,"FL-BELL-W",  "luxury"),
        ("Bellhop Wall",     6,  480, "2700K", "Black",    280, "FL-BELL-WB", "luxury"),
    ]:
        brand = "Philips" if level == "basic" else \
                "Kichler" if level == "mid" else \
                "Delta Light" if level == "premium" else \
                ("Artemide" if "ART" in sku_n else "Flos")
        add(brand, model, "wall", w, lm, ct,
            90 if level in ("premium","luxury") else 80,
            "IP20", "220V", level != "basic", 120,
            "200×120mm", fin, "indoor", level,
            price, sku_n, f"{level.title()} wall light {model}")

    # ═══════════════════════════════════════════════════════════════
    # OUTDOOR  (55 entries)
    # ═══════════════════════════════════════════════════════════════
    for model, w, lm, ct, fin, ip, price, sku_n, level in [
        ("Garden Basic",  10, 800,  "4000K", "Anthracite", "IP65", 28,  "OUT-B-10-AN","basic"),
        ("Garden Basic",  10, 800,  "3000K", "Anthracite", "IP65", 28,  "OUT-B-10-AN3","basic"),
        ("Post Light",    15, 1200, "4000K", "Black",      "IP65", 35,  "OUT-B-15-B","basic"),
        ("Post Light",    15, 1200, "3000K", "Silver",     "IP65", 35,  "OUT-B-15-S","basic"),
        ("Wall Outdoor",  9,  720,  "4000K", "Anthracite", "IP54", 25,  "OUT-B-9-AN","basic"),
        ("Wall Outdoor",  9,  720,  "3000K", "Black",      "IP54", 25,  "OUT-B-9-B","basic"),
        ("Clove S",       10, 850,  "3000K", "Black",      "IP65", 65,  "OUT-M-10-B","mid"),
        ("Clove S",       10, 850,  "3000K", "White",      "IP65", 62,  "OUT-M-10-W","mid"),
        ("Clove M",       15, 1280, "3000K", "Black",      "IP65", 85,  "OUT-M-15-B","mid"),
        ("Clove M",       15, 1280, "4000K", "Anthracite", "IP65", 82,  "OUT-M-15-AN","mid"),
        ("Clove L",       20, 1700, "3000K", "Black",      "IP65", 110, "OUT-M-20-B","mid"),
        ("Flood 30",      30, 2800, "4000K", "Grey",       "IP65", 72,  "OUT-M-30-G","mid"),
        ("Flood 50",      50, 4600, "4000K", "Grey",       "IP65", 95,  "OUT-M-50-G","mid"),
        ("Flood 80",      80, 7200, "4000K", "Grey",       "IP65", 120, "OUT-M-80-G","mid"),
        ("Spike 6",       6,  500,  "3000K", "Black",      "IP67", 42,  "OUT-M-SPK-6","mid"),
        ("Spike 9",       9,  750,  "3000K", "Black",      "IP67", 55,  "OUT-M-SPK-9","mid"),
        ("Path S",        5,  400,  "3000K", "Black",      "IP67", 38,  "OUT-M-PATH-S","mid"),
        ("Path M",        8,  650,  "3000K", "Black",      "IP67", 48,  "OUT-M-PATH-M","mid"),
        ("Lam Out S",     8,  700,  "2700K", "Black",      "IP65", 130, "OUT-P-8-B","premium"),
        ("Lam Out M",     12, 1050, "2700K", "Black",      "IP65", 165, "OUT-P-12-B","premium"),
        ("Lam Out L",     18, 1580, "3000K", "Anthracite", "IP65", 210, "OUT-P-18-AN","premium"),
        ("Flood Pro 50",  50, 4800, "4000K", "Anthracite", "IP66", 185, "OUT-P-F50","premium"),
        ("Flood Pro 100",100, 9500, "4000K", "Anthracite", "IP66", 260, "OUT-P-F100","premium"),
        ("Mast S",        6,  520,  "2700K", "Dark Grey",  "IP65", 280, "OUT-L-6-DG","luxury"),
        ("Mast M",        10, 870,  "2700K", "Black",      "IP65", 360, "OUT-L-10-B","luxury"),
        ("Mast L",        15, 1300, "2700K", "Dark Grey",  "IP65", 450, "OUT-L-15-DG","luxury"),
        ("Ova Spike",     8,  700,  "2700K", "Corten",     "IP67", 320, "OUT-L-OVA-C","luxury"),
        ("Cyl Floor Out", 20, 1750, "2700K", "Corten",     "IP65", 420, "OUT-L-CYL-C","luxury"),
    ]:
        brand = "Philips" if level == "basic" else \
                "Kichler" if level == "mid" else \
                "iGuzzini" if level == "premium" else "Delta Light"
        add(brand, model, "outdoor", w, lm, ct,
            80 if level in ("basic","mid") else 90, ip, "220V",
            level not in ("basic"), 60,
            "200×200mm", fin, "outdoor", level,
            price, sku_n, f"{level.title()} outdoor IP65 {model}")

    # ═══════════════════════════════════════════════════════════════
    # STRIP LIGHTS  (30 entries)
    # ═══════════════════════════════════════════════════════════════
    for ct, ip, w_m, price, sku_n, level in [
        ("3000K","IP20", 9.6,  8,  "STR-B-30-IP20","basic"),
        ("4000K","IP20", 9.6,  8,  "STR-B-40-IP20","basic"),
        ("3000K","IP44",14.4, 12,  "STR-B-30-IP44","basic"),
        ("4000K","IP44",14.4, 12,  "STR-B-40-IP44","basic"),
        ("2700K","IP20",14.4, 22,  "STR-M-27-IP20","mid"),
        ("3000K","IP20",14.4, 22,  "STR-M-30-IP20","mid"),
        ("4000K","IP20",14.4, 22,  "STR-M-40-IP20","mid"),
        ("2700K","IP44",19.2, 28,  "STR-M-27-IP44","mid"),
        ("3000K","IP44",19.2, 28,  "STR-M-30-IP44","mid"),
        ("tunable","IP20",20, 48,  "STR-M-TUN-IP20","mid"),
        ("2700K","IP20",24,   62,  "STR-P-27-IP20","premium"),
        ("3000K","IP20",24,   62,  "STR-P-30-IP20","premium"),
        ("tunable","IP20",24, 85,  "STR-P-TUN-IP20","premium"),
        ("2700K","IP44",24,   72,  "STR-P-27-IP44","premium"),
        ("tunable","IP44",24, 95,  "STR-P-TUN-IP44","premium"),
        ("2700K","IP20",28,  125,  "STR-L-27-IP20","luxury"),
        ("tunable","IP20",28,155,  "STR-L-TUN-IP20","luxury"),
        ("2700K","IP44",28,  145,  "STR-L-27-IP44","luxury"),
        ("RGBW","IP20", 24,   80,  "STR-RGB-IP20","mid"),
        ("RGBW","IP44", 24,   95,  "STR-RGB-IP44","mid"),
    ]:
        lm = int(w_m * 80)
        brand = {"basic":"Sylvania","mid":"Philips","premium":"Osram","luxury":"Lutron"}[level]
        add(brand, f"Flex Strip {ct} {ip} {w_m}W/m", "strip",
            w_m, lm, ct, 90 if level in ("premium","luxury") else 80,
            ip, "24V", True, 120,
            "per meter", "White PCB",
            "both" if ip == "IP44" else "indoor",
            level, price * 5, sku_n,
            f"LED strip {ct} {ip} {w_m}W/m (price per 5m reel)")

    # ═══════════════════════════════════════════════════════════════
    # FLOOR LAMPS  (30 entries)
    # ═══════════════════════════════════════════════════════════════
    for model, w, lm, ct, fin, price, sku_n, level in [
        ("Arc Floor Basic",  20, 1600, "3000K", "Black",     35,  "FLR-B-20-B",  "basic"),
        ("Arc Floor Basic",  20, 1600, "3000K", "White",     35,  "FLR-B-20-W",  "basic"),
        ("Tripod Basic",     15, 1200, "3000K", "Black",     42,  "FLR-B-15-B",  "basic"),
        ("Tripod Basic",     15, 1200, "4000K", "White",     42,  "FLR-B-15-W",  "basic"),
        ("Arc Floor Mid",    25, 2000, "2700K", "Black",     92,  "FLR-M-25-B",  "mid"),
        ("Arc Floor Mid",    25, 2000, "3000K", "Brass",    102,  "FLR-M-25-BR", "mid"),
        ("Tripod Mid",       20, 1600, "2700K", "Black",     88,  "FLR-M-20-B",  "mid"),
        ("Tripod Mid",       20, 1600, "2700K", "Walnut",    98,  "FLR-M-20-W",  "mid"),
        ("Reading Floor",    12, 960,  "3000K", "Black",     75,  "FLR-M-12-B",  "mid"),
        ("Reading Floor",    12, 960,  "2700K", "Brass",     80,  "FLR-M-12-BR", "mid"),
        ("Toio",             150,13000,"3000K", "Chrome",   550,  "FL-TOIO-C",   "premium"),
        ("Stylos",           20, 1600, "2700K", "White",    380,  "FL-STYL-W",   "premium"),
        ("Parentesi",        40, 3200, "2700K", "Black",    420,  "FL-PAR-B",    "premium"),
        ("Kelvin LED Floor", 30, 2400, "3000K", "Black",    580,  "FL-KEL-B",    "premium"),
        ("Tolomeo Mega",     26, 2100, "3000K", "Aluminium",620,  "ART-TOLMG",   "premium"),
        ("Tolomeo Floor",    20, 1600, "3000K", "Aluminium",490,  "ART-TOL-F",   "luxury"),
        ("Chlorophilia 2",   30, 2400, "2700K", "White",    780,  "ART-CHLO-F",  "luxury"),
        ("Mendori Floor",    12, 960,  "2700K", "White",    650,  "ART-MEND-F",  "luxury"),
        ("Nessino Floor",    8,  640,  "2700K", "Orange",   420,  "ART-NESSF-O", "luxury"),
        ("Nessino Floor",    8,  640,  "2700K", "Ice Blue",  420, "ART-NESSF-IB","luxury"),
    ]:
        brand = "Sylvania" if level == "basic" else \
                "Kichler" if level == "mid" else \
                ("Flos" if "FL-" in sku_n else "Artemide")
        add(brand, model, "floor", w, lm, ct,
            90 if level in ("premium","luxury") else 80,
            "IP20", "220V", level != "basic", 120,
            "H:170cm", fin, "indoor", level,
            price, sku_n, f"{level.title()} floor lamp {model} {fin}")

    # ═══════════════════════════════════════════════════════════════
    # MIRROR / BATHROOM  (25 entries)
    # ═══════════════════════════════════════════════════════════════
    for w, lm, ct, dim, price, sku_n, level in [
        (12, 1050, "4000K", "W:600mm",  22, "MIR-B-12-40","basic"),
        (18, 1580, "4000K", "W:800mm",  28, "MIR-B-18-40","basic"),
        (20, 1750, "4000K", "W:1000mm", 32, "MIR-B-20-40","basic"),
        (12, 1050, "3000K", "W:600mm",  22, "MIR-B-12-30","basic"),
        (14, 1250, "4000K", "W:700mm",  58, "MIR-M-14-40","mid"),
        (20, 1800, "4000K", "W:900mm",  72, "MIR-M-20-40","mid"),
        (24, 2150, "tunable","W:1200mm",95, "MIR-M-24-TUN","mid"),
        (14, 1250, "3000K", "W:700mm",  60, "MIR-M-14-30","mid"),
        (20, 1800, "3000K", "W:900mm",  74, "MIR-M-20-30","mid"),
        (16, 1450, "4000K", "W:800mm",  115,"MIR-P-16-40","premium"),
        (24, 2200, "tunable","W:1000mm",150,"MIR-P-24-TUN","premium"),
        (30, 2700, "tunable","W:1200mm",180,"MIR-P-30-TUN","premium"),
        (16, 1450, "3000K", "W:800mm",  112,"MIR-P-16-30","premium"),
        (24, 2200, "4000K", "W:1000mm", 145,"MIR-P-24-40","premium"),
        (20, 1800, "tunable","W:900mm", 280,"MIR-L-20-TUN","luxury"),
        (30, 2700, "tunable","W:1200mm",350,"MIR-L-30-TUN","luxury"),
        (36, 3240, "tunable","W:1500mm",420,"MIR-L-36-TUN","luxury"),
    ]:
        brand = {"basic":"Philips","mid":"WAC Lighting","premium":"Astro","luxury":"Vibia"}[level]
        add(brand, f"Mirror Light {w}W", "mirror", w, lm, ct,
            92 if level in ("premium","luxury") else 85,
            "IP44", "220V", level != "basic", 120,
            dim, "Chrome", "indoor", level,
            price, sku_n, f"{level.title()} bathroom mirror light {w}W CRI high")

    # ═══════════════════════════════════════════════════════════════
    # CEILING / FLUSH MOUNT  (40 entries)
    # ═══════════════════════════════════════════════════════════════
    for model, w, lm, ct, fin, dim, price, sku_n, level in [
        ("Flush Basic S",    12, 960,  "3000K", "White",     "Ø280mm",  18, "CEI-B-12-W",  "basic"),
        ("Flush Basic S",    12, 960,  "4000K", "White",     "Ø280mm",  18, "CEI-B-12-W4", "basic"),
        ("Flush Basic M",    18, 1440, "3000K", "White",     "Ø350mm",  24, "CEI-B-18-W",  "basic"),
        ("Flush Basic M",    18, 1440, "4000K", "White",     "Ø350mm",  24, "CEI-B-18-W4", "basic"),
        ("Flush Basic L",    24, 1920, "4000K", "White",     "Ø440mm",  30, "CEI-B-24-W",  "basic"),
        ("Flush Basic L",    24, 1920, "3000K", "White",     "Ø440mm",  30, "CEI-B-24-W3", "basic"),
        ("Plato S",          12, 1050, "2700K", "Black",     "Ø300mm",  65, "CEI-M-12-B",  "mid"),
        ("Plato S",          12, 1050, "3000K", "White",     "Ø300mm",  62, "CEI-M-12-W",  "mid"),
        ("Plato M",          18, 1600, "2700K", "Brass",     "Ø400mm",  85, "CEI-M-18-BR", "mid"),
        ("Plato M",          18, 1600, "3000K", "Black",     "Ø400mm",  82, "CEI-M-18-B",  "mid"),
        ("Plato L",          24, 2100, "2700K", "White",     "Ø500mm",  105,"CEI-M-24-W",  "mid"),
        ("Plato L",          24, 2100, "3000K", "Black",     "Ø500mm",  105,"CEI-M-24-B",  "mid"),
        ("Plato XL",         36, 3200, "3000K", "Brass",     "Ø620mm",  145,"CEI-M-36-BR", "mid"),
        ("Venn Flush S",     10, 900,  "2700K", "White",     "Ø250mm",  140,"CEI-P-10-W",  "premium"),
        ("Venn Flush S",     10, 900,  "2700K", "Black",     "Ø250mm",  140,"CEI-P-10-B",  "premium"),
        ("Venn Flush M",     16, 1450, "2700K", "White",     "Ø380mm",  185,"CEI-P-16-W",  "premium"),
        ("Venn Flush M",     16, 1450, "tunable","Aluminium","Ø380mm",  220,"CEI-P-16-A",  "premium"),
        ("Venn Flush L",     22, 2000, "2700K", "Black",     "Ø500mm",  240,"CEI-P-22-B",  "premium"),
        ("Venn Flush L",     22, 2000, "tunable","White",    "Ø500mm",  265,"CEI-P-22-W",  "premium"),
        ("Cyclos Ceiling S", 14, 1250, "2700K", "White",     "Ø320mm",  380,"CEI-L-14-W",  "luxury"),
        ("Cyclos Ceiling M", 20, 1800, "2700K", "White",     "Ø450mm",  520,"CEI-L-20-W",  "luxury"),
        ("Cyclos Ceiling L", 28, 2500, "2700K", "White",     "Ø600mm",  680,"CEI-L-28-W",  "luxury"),
        ("Cyclos Ceiling L", 28, 2500, "tunable","Black",    "Ø600mm",  720,"CEI-L-28-B",  "luxury"),
        ("Castore Ceiling S",18, 1600, "2700K", "White",     "Ø25cm",   580,"ART-CASFLAT-S","luxury"),
        ("Castore Ceiling L",28, 2500, "2700K", "White",     "Ø45cm",   820,"ART-CASFLAT-L","luxury"),
    ]:
        brand = "Philips" if level == "basic" else \
                "Sea Gull" if level == "mid" else \
                "WAC Lighting" if level == "premium" else "Artemide"
        add(brand, model, "ceiling", w, lm, ct,
            90 if level in ("premium","luxury") else 80,
            "IP20", "220V", level != "basic", 120,
            dim, fin, "indoor", level,
            price, sku_n, f"{level.title()} flush-mount ceiling light {model}")

    # ═══════════════════════════════════════════════════════════════
    # TABLE LAMPS  (35 entries)
    # ═══════════════════════════════════════════════════════════════
    for model, w, lm, ct, fin, price, sku_n, level in [
        ("Desk Basic",       9,  720,  "4000K", "White",      22, "TBL-B-9-W",   "basic"),
        ("Desk Basic",       9,  720,  "3000K", "Black",      22, "TBL-B-9-B",   "basic"),
        ("Bedside Basic",    6,  480,  "3000K", "White",      18, "TBL-B-6-W",   "basic"),
        ("Bedside Basic",    6,  480,  "2700K", "White",      18, "TBL-B-6-W2",  "basic"),
        ("Clip-on",          5,  400,  "4000K", "Black",      15, "TBL-B-CLIP-B", "basic"),
        ("Studio Task S",    10, 850,  "3000K", "Black",      68, "TBL-M-10-B",   "mid"),
        ("Studio Task S",    10, 850,  "2700K", "Brass",      72, "TBL-M-10-BR",  "mid"),
        ("Studio Task M",    15, 1280, "3000K", "Black",      88, "TBL-M-15-B",   "mid"),
        ("Bedside Mid",      8,  680,  "2700K", "White",      55, "TBL-M-8-W",    "mid"),
        ("Bedside Mid",      8,  680,  "2700K", "Brass",      60, "TBL-M-8-BR",   "mid"),
        ("Cone Shade",       12, 1050, "2700K", "Black",      78, "TBL-M-12-B",   "mid"),
        ("Cone Shade",       12, 1050, "3000K", "White",      75, "TBL-M-12-W",   "mid"),
        ("Globe Table",      10, 850,  "2700K", "Terracotta", 82, "TBL-M-10-TC",  "mid"),
        ("Tolomeo Micro",    6,  480,  "3000K", "Aluminium", 245, "ART-TOLMIC-T", "premium"),
        ("Tolomeo Table",    12, 960,  "3000K", "Aluminium", 380, "ART-TOL-T",    "premium"),
        ("Miss K Table",     8,  640,  "2700K", "Amber",     165, "FL-MISSK-T",   "premium"),
        ("Bon Jour Table",   8,  640,  "2700K", "Chrome",    145, "FL-BONJ-T",    "premium"),
        ("Stylos Table",     12, 960,  "2700K", "White",     295, "FL-STYL-T",    "premium"),
        ("IC Table",         12, 960,  "3000K", "Brass",     320, "FL-IC-T",      "premium"),
        ("Nessino Table",    6,  480,  "2700K", "Orange",    265, "ART-NESS-T-O", "luxury"),
        ("Nessino Table",    6,  480,  "2700K", "Red",       265, "ART-NESS-T-R", "luxury"),
        ("Castore Table S",  16, 1300, "2700K", "White",     460, "ART-CAS-T-S",  "luxury"),
        ("Castore Table L",  22, 1800, "2700K", "White",     620, "ART-CAS-T-L",  "luxury"),
        ("Luminator",        25, 2000, "2700K", "White",     540, "FL-LUMI-T",    "luxury"),
        ("Parentesi Table",  20, 1600, "2700K", "Black",     380, "FL-PAR-T",     "luxury"),
    ]:
        brand = "Philips" if level == "basic" else \
                "Kichler" if level == "mid" else \
                ("Artemide" if "ART" in sku_n else "Flos")
        add(brand, model, "table", w, lm, ct,
            90 if level in ("premium","luxury") else 80,
            "IP20", "220V", level != "basic", 120,
            "H:40-60cm", fin, "indoor", level,
            price, sku_n, f"{level.title()} table lamp {model} {fin}")

    # ═══════════════════════════════════════════════════════════════
    # LINEAR PENDANTS  (40 entries)
    # ═══════════════════════════════════════════════════════════════
    for length, w, lm, ct, fin, price, sku_n, level in [
        ("60cm",   20, 1700, "4000K", "White",      32, "LIN-B-60-W",   "basic"),
        ("60cm",   20, 1700, "3000K", "White",      32, "LIN-B-60-W3",  "basic"),
        ("90cm",   30, 2550, "4000K", "White",      40, "LIN-B-90-W",   "basic"),
        ("120cm",  40, 3400, "4000K", "White",      50, "LIN-B-120-W",  "basic"),
        ("120cm",  40, 3400, "3000K", "White",      50, "LIN-B-120-W3", "basic"),
        ("60cm",   20, 1800, "2700K", "Black",      85, "LIN-M-60-B",   "mid"),
        ("60cm",   20, 1800, "3000K", "Brass",      90, "LIN-M-60-BR",  "mid"),
        ("90cm",   30, 2700, "2700K", "Black",     110, "LIN-M-90-B",   "mid"),
        ("90cm",   30, 2700, "3000K", "White",     105, "LIN-M-90-W",   "mid"),
        ("120cm",  40, 3600, "2700K", "Black",     138, "LIN-M-120-B",  "mid"),
        ("120cm",  40, 3600, "3000K", "Brass",     145, "LIN-M-120-BR", "mid"),
        ("150cm",  50, 4500, "3000K", "Black",     175, "LIN-M-150-B",  "mid"),
        ("180cm",  60, 5400, "3000K", "Brushed Nickel",205,"LIN-M-180-N","mid"),
        ("60cm",   22, 2000, "2700K", "Black",     195, "LIN-P-60-B",   "premium"),
        ("60cm",   22, 2000, "tunable","White",    225, "LIN-P-60-TW",  "premium"),
        ("90cm",   32, 2900, "2700K", "Black",     245, "LIN-P-90-B",   "premium"),
        ("120cm",  42, 3800, "2700K", "Black",     295, "LIN-P-120-B",  "premium"),
        ("120cm",  42, 3800, "tunable","White",    340, "LIN-P-120-TW", "premium"),
        ("150cm",  55, 5000, "2700K", "Aluminium", 360, "LIN-P-150-A",  "premium"),
        ("180cm",  65, 5900, "tunable","Black",    420, "LIN-P-180-B",  "premium"),
        ("60cm",   20, 1800, "2700K", "Black",     420, "LIN-L-60-B",   "luxury"),
        ("60cm",   20, 1800, "tunable","White",    480, "LIN-L-60-TW",  "luxury"),
        ("90cm",   30, 2700, "2700K", "Black",     580, "LIN-L-90-B",   "luxury"),
        ("90cm",   30, 2700, "tunable","White",    640, "LIN-L-90-TW",  "luxury"),
        ("120cm",  40, 3600, "2700K", "Black",     720, "LIN-L-120-B",  "luxury"),
        ("120cm",  40, 3600, "tunable","Aluminium",800, "LIN-L-120-A",  "luxury"),
        ("150cm",  50, 4500, "2700K", "Black",     920, "LIN-L-150-B",  "luxury"),
        ("180cm",  60, 5400, "tunable","White",   1050, "LIN-L-180-TW", "luxury"),
    ]:
        brand = {"basic": "Sylvania", "mid": "Sea Gull",
                 "premium": "Delta Light", "luxury": "Vibia"}[level]
        add(brand, f"Linear {length} {w}W", "linear", w, lm, ct,
            90 if level in ("premium","luxury") else 80,
            "IP20", "220V", level != "basic", 120,
            f"{length}×H80mm", fin, "indoor", level,
            price, sku_n, f"{level.title()} linear pendant {length} {ct}")

    # ═══════════════════════════════════════════════════════════════
    # CHANDELIERS  (30 entries)
    # ═══════════════════════════════════════════════════════════════
    for model, w, lm, ct, fin, dim, price, sku_n, level in [
        ("Orb Basic 5lt",    25, 2000, "3000K", "Chrome",    "Ø450mm",  55,  "CHD-B-5-C",   "basic"),
        ("Orb Basic 5lt",    25, 2000, "3000K", "Black",     "Ø450mm",  55,  "CHD-B-5-B",   "basic"),
        ("Drum Basic",       36, 2900, "3000K", "White",     "Ø500mm",  65,  "CHD-B-DRUM-W","basic"),
        ("Branch 5lt",       25, 2100, "2700K", "Brass",     "Ø560mm",  145, "CHD-M-5-BR",  "mid"),
        ("Branch 5lt",       25, 2100, "2700K", "Black",     "Ø560mm",  138, "CHD-M-5-B",   "mid"),
        ("Branch 8lt",       40, 3400, "2700K", "Brass",     "Ø700mm",  210, "CHD-M-8-BR",  "mid"),
        ("Branch 8lt",       40, 3400, "3000K", "Black",     "Ø700mm",  198, "CHD-M-8-B",   "mid"),
        ("Halo Ring S",      30, 2550, "2700K", "Gold",      "Ø500mm",  195, "CHD-M-HALO-S","mid"),
        ("Halo Ring L",      50, 4250, "2700K", "Gold",      "Ø800mm",  280, "CHD-M-HALO-L","mid"),
        ("Halo Ring XL",     80, 6800, "2700K", "Gold",      "Ø1200mm", 395, "CHD-M-HALO-XL","mid"),
        ("Cluster 10",       50, 4500, "2700K", "Chrome",    "Ø600mm",  280, "CHD-M-CLU-10","mid"),
        ("Antler Modern",    40, 3400, "3000K", "Black",     "Ø650mm",  320, "CHD-M-ANT-B", "mid"),
        ("Milo Crystal S",   24, 2100, "2700K", "Chrome",    "Ø500mm",  580, "CHD-P-MIL-S", "premium"),
        ("Milo Crystal L",   48, 4200, "2700K", "Chrome",    "Ø800mm",  920, "CHD-P-MIL-L", "premium"),
        ("Fractal 8lt",      40, 3600, "2700K", "Black+Gold","Ø700mm",  680, "CHD-P-FRA-8", "premium"),
        ("Fractal 12lt",     60, 5400, "2700K", "Black+Gold","Ø900mm",  980, "CHD-P-FRA-12","premium"),
        ("Orbital S",        30, 2700, "2700K", "Nickel",    "Ø600mm",  750, "CHD-P-ORB-S", "premium"),
        ("Orbital L",        50, 4500, "2700K", "Nickel",    "Ø900mm",  1050,"CHD-P-ORB-L", "premium"),
        ("2097/50",          100,8800, "2700K", "Nickel",    "Ø160cm",  2800,"FL-2097-50",  "luxury"),
        ("Medusa",           80, 7200, "2700K", "Chrome",    "Ø140cm",  3500,"FL-MEDU",     "luxury"),
        ("Taraxacum 88 S1",  60, 5400, "2700K", "Chrome",    "Ø79cm",   2200,"FL-TAR-S1",   "luxury"),
        ("Taraxacum 88 S2",  90, 8100, "2700K", "Chrome",    "Ø114cm",  3100,"FL-TAR-S2",   "luxury"),
        ("Galaxia S",        40, 3600, "2700K", "White",     "Ø70cm",   1800,"ART-GAL-S",   "luxury"),
        ("Galaxia L",        70, 6300, "2700K", "White",     "Ø100cm",  2500,"ART-GAL-L",   "luxury"),
        ("Swarovski Drop",  120,10800, "2700K", "Crystal+Chrome","Ø120cm",6500,"SWA-DROP",  "luxury"),
        ("Swarovski Jewel", 200,18000, "2700K", "Crystal+Gold","Ø180cm",9800,"SWA-JEWL",   "luxury"),
    ]:
        brand = "Philips" if level == "basic" else \
                "Kichler" if level == "mid" else \
                "Flos" if "FL-" in sku_n else \
                "Artemide" if "ART" in sku_n else \
                "Swarovski" if "SWA" in sku_n else "Delta Light"
        add(brand, model, "chandelier", w, lm, ct,
            90 if level in ("premium","luxury") else 80,
            "IP20", "220V", level not in ("basic",), 120,
            dim, fin, "indoor", level,
            price, sku_n, f"{level.title()} chandelier {model}")

    # ═══════════════════════════════════════════════════════════════
    # HIGH BAY / INDUSTRIAL  (20 entries)
    # ═══════════════════════════════════════════════════════════════
    for w, lm, ct, price, sku_n, level in [
        (100, 10000, "4000K",  55, "HB-B-100-40", "basic"),
        (100, 10000, "5000K",  55, "HB-B-100-50", "basic"),
        (150, 15000, "4000K",  75, "HB-B-150-40", "basic"),
        (200, 20000, "4000K",  95, "HB-B-200-40", "basic"),
        (200, 20000, "5000K",  95, "HB-B-200-50", "basic"),
        (100, 12000, "4000K", 135, "HB-M-100-40", "mid"),
        (150, 18000, "4000K", 175, "HB-M-150-40", "mid"),
        (200, 24000, "4000K", 220, "HB-M-200-40", "mid"),
        (240, 28800, "4000K", 265, "HB-M-240-40", "mid"),
        (300, 36000, "4000K", 320, "HB-M-300-40", "mid"),
        (100, 12000, "tunable",220,"HB-P-100-TUN","premium"),
        (150, 18000, "tunable",280,"HB-P-150-TUN","premium"),
        (200, 24000, "4000K", 340, "HB-P-200-40", "premium"),
        (250, 30000, "4000K", 420, "HB-P-250-40", "premium"),
        (300, 36000, "tunable",520,"HB-P-300-TUN","premium"),
        (100, 12500, "4000K", 480, "HB-L-100-40", "luxury"),
        (150, 18750, "tunable",620,"HB-L-150-TUN","luxury"),
        (200, 25000, "tunable",780,"HB-L-200-TUN","luxury"),
        (250, 31250, "4000K", 920, "HB-L-250-40", "luxury"),
        (300, 37500, "tunable",1100,"HB-L-300-TUN","luxury"),
    ]:
        brand = {"basic": "Philips", "mid": "Osram",
                 "premium": "iGuzzini", "luxury": "Zumtobel"}[level]
        add(brand, f"HighBay UFO {w}W", "highbay", w, lm, ct,
            90 if level in ("premium","luxury") else 80,
            "IP65", "220V", level not in ("basic",), 120,
            "Ø380mm", "Silver", "indoor", level,
            price, sku_n, f"{level.title()} industrial UFO high bay {w}W")

    # ═══════════════════════════════════════════════════════════════
    # STEP / STAIR / RECESSED WALL  (25 entries)
    # ═══════════════════════════════════════════════════════════════
    for model, w, lm, ct, fin, ip, price, sku_n, level in [
        ("Step Basic",        2,  160,  "3000K", "White",    "IP20", 12, "STEP-B-2-W",   "basic"),
        ("Step Basic",        2,  160,  "3000K", "Black",    "IP20", 12, "STEP-B-2-B",   "basic"),
        ("Step Basic Out",    3,  240,  "3000K", "Anthracite","IP65",18, "STEP-B-3-AN",  "basic"),
        ("Stair Mid S",       3,  270,  "2700K", "Black",    "IP20", 38, "STEP-M-3-B",   "mid"),
        ("Stair Mid S",       3,  270,  "3000K", "White",    "IP20", 35, "STEP-M-3-W",   "mid"),
        ("Stair Mid M",       5,  450,  "2700K", "Black",    "IP20", 48, "STEP-M-5-B",   "mid"),
        ("Stair Mid Out",     5,  450,  "3000K", "Anthracite","IP65",58, "STEP-M-5-AN",  "mid"),
        ("Wall Recess S",     6,  540,  "3000K", "Black",    "IP20", 55, "WRES-M-6-B",   "mid"),
        ("Wall Recess S",     6,  540,  "2700K", "White",    "IP20", 52, "WRES-M-6-W",   "mid"),
        ("Wall Recess M",     8,  720,  "2700K", "Black",    "IP20", 72, "WRES-M-8-B",   "mid"),
        ("Blade Step S",      4,  360,  "2700K", "Black",    "IP20", 95, "STEP-P-4-B",   "premium"),
        ("Blade Step M",      6,  540,  "2700K", "Black",    "IP20", 120,"STEP-P-6-B",   "premium"),
        ("Blade Step Out",    6,  540,  "2700K", "Anthracite","IP65",140,"STEP-P-6-AN",  "premium"),
        ("Wall Washer S",     8,  720,  "2700K", "Black",    "IP20", 145,"WWSH-P-8-B",   "premium"),
        ("Wall Washer M",    12, 1080,  "2700K", "Black",    "IP20", 185,"WWSH-P-12-B",  "premium"),
        ("Wall Washer M",    12, 1080,  "tunable","White",   "IP20", 210,"WWSH-P-12-TW", "premium"),
        ("Cove Recess S",     6,  540,  "2700K", "Black",    "IP20", 230,"COV-P-6-B",    "premium"),
        ("Cove Recess M",    10,  900,  "2700K", "Aluminium","IP20", 280,"COV-P-10-A",   "premium"),
        ("Slot Wall S",       4,  360,  "2700K", "Black",    "IP20", 320,"SLOT-L-4-B",   "luxury"),
        ("Slot Wall M",       8,  720,  "2700K", "Black",    "IP20", 420,"SLOT-L-8-B",   "luxury"),
        ("Slot Wall L",      12, 1080,  "tunable","Black",   "IP20", 580,"SLOT-L-12-B",  "luxury"),
        ("Step Linear S",     6,  540,  "2700K", "Dark Grey","IP65", 380,"STEPLIN-L-S",  "luxury"),
        ("Step Linear M",    10,  900,  "2700K", "Dark Grey","IP65", 480,"STEPLIN-L-M",  "luxury"),
        ("Micro Slot",        3,  270,  "2700K", "Black",    "IP20", 260,"MSLOT-L-3-B",  "luxury"),
        ("Micro Slot Out",    3,  270,  "2700K", "Anthracite","IP67",320,"MSLOT-L-3-AN", "luxury"),
    ]:
        brand = "Philips" if level == "basic" else \
                "Astro" if level == "mid" else \
                "iGuzzini" if level == "premium" else "Erco"
        add(brand, model, "recessed_wall", w, lm, ct,
            90 if level in ("premium","luxury") else 80,
            ip, "220V", level not in ("basic",), 30,
            "120×80mm", fin,
            "outdoor" if "Out" in model else "indoor",
            level, price, sku_n, f"{level.title()} step/wall recessed {model}")

    # ═══════════════════════════════════════════════════════════════
    # READING / BED-HEAD LIGHTS  (20 entries)
    # ═══════════════════════════════════════════════════════════════
    for model, w, lm, ct, fin, price, sku_n, level in [
        ("Clip Read B",     5,  400, "3000K", "Black",      14, "READ-B-5-B",   "basic"),
        ("Clip Read B",     5,  400, "4000K", "White",      14, "READ-B-5-W",   "basic"),
        ("Flex Arm Read",   6,  480, "4000K", "Silver",     18, "READ-B-6-S",   "basic"),
        ("Swing Arm S",     8,  680, "2700K", "Black",      55, "READ-M-8-B",   "mid"),
        ("Swing Arm S",     8,  680, "3000K", "Brass",      60, "READ-M-8-BR",  "mid"),
        ("Swing Arm M",     12, 1020,"3000K", "Black",      75, "READ-M-12-B",  "mid"),
        ("Bedhead S",       6,  510, "2700K", "White",      48, "READ-M-6-W",   "mid"),
        ("Bedhead S",       6,  510, "2700K", "Brass",      52, "READ-M-6-BR",  "mid"),
        ("Bedhead M",       10, 850, "2700K", "Black",      68, "READ-M-10-B",  "mid"),
        ("Bedhead M",       10, 850, "2700K", "White",      65, "READ-M-10-W",  "mid"),
        ("Tolomeo Micro R", 6,  480, "3000K", "Aluminium",  245,"READ-P-6-A",   "premium"),
        ("Nodro",           8,  680, "2700K", "White",      195,"READ-P-8-W",   "premium"),
        ("Nodro",           8,  680, "2700K", "Black",      195,"READ-P-8-B",   "premium"),
        ("Flexarm Pro",    10, 850,  "tunable","Black",      280,"READ-P-10-B",  "premium"),
        ("Flexarm Pro",    10, 850,  "tunable","Chrome",     280,"READ-P-10-C",  "premium"),
        ("Nod",             6,  480, "2700K", "White",      380,"READ-L-6-W",   "luxury"),
        ("Nod",             6,  480, "tunable","Black",      420,"READ-L-6-B",   "luxury"),
        ("Pivothead S",     8,  680, "2700K", "Aluminium",  520,"READ-L-8-A",   "luxury"),
        ("Pivothead M",    12, 1020, "tunable","Aluminium",  680,"READ-L-12-A",  "luxury"),
        ("Cabildo Read",    6,  480, "3000K", "White",      350,"READ-L-6-WH",  "luxury"),
    ]:
        brand = "Philips" if level == "basic" else \
                "Kichler" if level == "mid" else \
                ("Artemide" if "ART" in sku_n or level == "premium" else "Vibia")
        add(brand, model, "reading", w, lm, ct,
            90 if level in ("premium","luxury") else 80,
            "IP20", "220V", level not in ("basic",), 120,
            "H:30-50cm", fin, "indoor", level,
            price, sku_n, f"{level.title()} reading/bedhead light {model}")

    # ═══════════════════════════════════════════════════════════════
    # BATHROOM / IP44 DOWNLIGHTS  (20 entries)
    # ═══════════════════════════════════════════════════════════════
    for w, lm, ct, fin, price, sku_n, level in [
        (7,  560, "3000K", "White",   14, "BATH-B-7-W",   "basic"),
        (7,  560, "4000K", "White",   14, "BATH-B-7-W4",  "basic"),
        (9,  720, "4000K", "White",   17, "BATH-B-9-W",   "basic"),
        (9,  720, "3000K", "White",   17, "BATH-B-9-W3",  "basic"),
        (12, 960, "4000K", "White",   20, "BATH-B-12-W",  "basic"),
        (7,  630, "3000K", "White",   38, "BATH-M-7-W",   "mid"),
        (7,  630, "3000K", "Chrome",  40, "BATH-M-7-C",   "mid"),
        (9,  810, "4000K", "White",   45, "BATH-M-9-W",   "mid"),
        (9,  810, "tunable","Chrome", 58, "BATH-M-9-TUN", "mid"),
        (12,1080, "4000K", "White",   52, "BATH-M-12-W",  "mid"),
        (12,1080, "tunable","Chrome", 68, "BATH-M-12-TUN","mid"),
        (7,  650, "3000K", "White",   88, "BATH-P-7-W",   "premium"),
        (7,  650, "2700K", "Chrome",  92, "BATH-P-7-C",   "premium"),
        (9,  840, "3000K", "White",  105, "BATH-P-9-W",   "premium"),
        (9,  840, "tunable","Chrome",125, "BATH-P-9-TUN", "premium"),
        (12,1120, "2700K", "White",  118, "BATH-P-12-W",  "premium"),
        (7,  650, "2700K", "White",  175, "BATH-L-7-W",   "luxury"),
        (9,  840, "2700K", "Chrome", 210, "BATH-L-9-C",   "luxury"),
        (12,1120, "tunable","White", 260, "BATH-L-12-TUN","luxury"),
        (7,  650, "1800K", "Chrome", 240, "BATH-L-7-18",  "luxury"),
    ]:
        brand = {"basic":"Philips","mid":"WAC Lighting","premium":"Astro","luxury":"Vibia"}[level]
        add(brand, f"Aqua Downlight {w}W", "downlight", w, lm, ct,
            90 if level in ("premium","luxury") else 80,
            "IP44", "220V", level != "basic", 90,
            "Ø90mm", fin, "indoor", level,
            price, sku_n, f"{level.title()} IP44 bathroom downlight {w}W")

    # ═══════════════════════════════════════════════════════════════
    # RETAIL / DISPLAY SPOTS  (20 entries)
    # ═══════════════════════════════════════════════════════════════
    for w, lm, ct, fin, beam, price, sku_n, level in [
        (10, 850,  "3000K", "White",  15, 22, "RET-B-10-W",  "basic"),
        (10, 850,  "4000K", "White",  24, 22, "RET-B-10-W4", "basic"),
        (15, 1280, "3000K", "White",  24, 28, "RET-B-15-W",  "basic"),
        (15, 1280, "4000K", "Black",  36, 28, "RET-B-15-B",  "basic"),
        (10, 950,  "3000K", "Black",  15, 52, "RET-M-10-B",  "mid"),
        (10, 950,  "4000K", "White",  24, 50, "RET-M-10-W",  "mid"),
        (15, 1430, "3000K", "Black",  24, 65, "RET-M-15-B",  "mid"),
        (20, 1900, "3000K", "Black",  24, 80, "RET-M-20-B",  "mid"),
        (20, 1900, "4000K", "White",  36, 78, "RET-M-20-W",  "mid"),
        (25, 2375, "3000K", "Nickel", 36, 95, "RET-M-25-N",  "mid"),
        (10, 950,  "2700K", "Black",  10, 125,"RET-P-10-B",  "premium"),
        (15, 1430, "2700K", "Black",  15, 155,"RET-P-15-B",  "premium"),
        (20, 1900, "3000K", "Black",  24, 185,"RET-P-20-B",  "premium"),
        (25, 2375, "3000K", "White",  24, 210,"RET-P-25-W",  "premium"),
        (30, 2850, "2700K", "Black",  15, 245,"RET-P-30-B",  "premium"),
        (10, 950,  "2700K", "Black",  10, 280,"RET-L-10-B",  "luxury"),
        (15, 1430, "2700K", "Black",  15, 360,"RET-L-15-B",  "luxury"),
        (20, 1900, "tunable","Black", 15, 420,"RET-L-20-B",  "luxury"),
        (25, 2375, "2700K", "White",  10, 480,"RET-L-25-W",  "luxury"),
        (30, 2850, "tunable","Black", 24, 560,"RET-L-30-B",  "luxury"),
    ]:
        brand = {"basic":"Sylvania","mid":"WAC Lighting","premium":"Erco","luxury":"Erco"}[level]
        add(brand, f"Retail Spot {w}W {fin}", "spot", w, lm, ct,
            90 if level in ("premium","luxury") else 80,
            "IP20", "220V", level != "basic", beam,
            "Ø65mm", fin, "indoor", level,
            price, sku_n, f"{level.title()} retail/display spot {w}W narrow {beam}°")

    # ═══════════════════════════════════════════════════════════════
    # EMERGENCY / EXIT LIGHTS  (10 entries)
    # ═══════════════════════════════════════════════════════════════
    for model, w, lm, price, sku_n in [
        ("Exit Sign Standard", 2, 200, 18, "EMG-EXIT-STD"),
        ("Exit Sign Slim",     2, 200, 24, "EMG-EXIT-SLM"),
        ("Emergency Bulkhead", 8, 640, 28, "EMG-BLK-8"),
        ("Emergency Twin",    16,1280, 35, "EMG-TWN-16"),
        ("Maintained Exit",    5, 400, 38, "EMG-MAINT-5"),
        ("Dual Purpose 3hr",  10, 800, 45, "EMG-DUAL-3H"),
        ("Maintained Twin",   20,1600, 52, "EMG-MTWN-20"),
        ("Exit Surface",       3, 240, 22, "EMG-SURF-3"),
        ("Emergency Recessed",10, 800, 55, "EMG-REC-10"),
        ("Exit Safelight",     4, 320, 28, "EMG-SAFE-4"),
    ]:
        add("Legrand", model, "emergency", w, lm, "4000K", 80,
            "IP44", "220V", False, 120,
            "300×100mm", "White", "indoor", "basic",
            price, sku_n, f"Emergency/exit lighting {model} 3-hour battery backup")

    # Extra track heads to round up to 500
    for w, lm, ct, fin, price, sku_n, level in [
        (8,  720, "2700K", "White",   35, "TRK-B-8-W",   "basic"),
        (8,  720, "3000K", "Black",   35, "TRK-B-8-B",   "basic"),
        (15, 1350,"2700K", "Brass",   72, "TRK-M-15-BR", "mid"),
        (18, 1620,"tunable","Black",  88, "TRK-M-18-TUN","mid"),
        (12, 1140,"2700K", "Black",  140, "TRK-P-12-B",  "premium"),
        (20, 1900,"tunable","Black", 165, "TRK-P-20-TUN","premium"),
        (8,  760, "2700K", "Black",  220, "TRK-L-8-B",   "luxury"),
        (12, 1140,"2700K", "White",  240, "TRK-L-12-W",  "luxury"),
        (25, 2375,"tunable","Black", 290, "TRK-L-25-TUN","luxury"),
        (30, 2850,"2700K", "Aluminium",325,"TRK-L-30-A2","luxury"),
    ]:
        brand = {"basic":"Philips","mid":"WAC Lighting","premium":"Delta Light","luxury":"Erco"}[level]
        add(brand, f"Track Pro {w}W {fin}", "track", w, lm, ct,
            90 if level in ("premium","luxury") else 80,
            "IP20", "220V", level != "basic", 24,
            "Ø65×120mm", fin, "indoor", level,
            price, sku_n, f"{level.title()} track head {w}W {ct} narrow beam")

    return rows


def seed(db=None):
    close_db = db is None
    if db is None:
        init_db()
        db = SessionLocal()
    try:
        count = db.query(Lamp).count()
        if count > 0:
            print(f"Catalog already has {count} lamps — skipping seed.")
            return count
        lamps = _lamps()
        for data in lamps:
            db.add(Lamp(**data))
        db.commit()
        print(f"✓ Seeded {len(lamps)} lamps into catalog.")
        return len(lamps)
    finally:
        if close_db:
            db.close()


if __name__ == "__main__":
    seed()
