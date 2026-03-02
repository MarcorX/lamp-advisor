# 💡 LampAdvisor

> AI-powered lighting proposal system for architects, interior designers, and lighting specifiers.

Upload a client project (PDF floor plan or DWG/DXF drawing), fill in key details, and get **1–3 tailored lamp proposals** from your product catalog — powered by rule-based matching and Claude AI.

---

## Features

- **Lamp Catalog Management** — import from Excel/CSV, add/edit/delete lamps
- **Project Analysis** — upload PDF or DWG/DXF; auto-extracts area, rooms, property level
- **Smart Recommendations** — rule-based engine filters lamps by property level, space type, color temperature, CRI
- **AI Justifications** — Claude AI writes a professional narrative for each proposal
- **Printable Proposals** — print-ready PDF output per proposal
- **Bilingual** — accepts English and Spanish column names / project files

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python FastAPI |
| Frontend | Jinja2 templates + HTMX + Tailwind CSS |
| Database | SQLite (via SQLAlchemy) |
| AI Engine | Anthropic Claude (`claude-sonnet-4-6`) |
| File Parsing | `pdfplumber` (PDF), `ezdxf` (DWG/DXF) |
| Deployment | Render.com (one-click) |

---

## Local Setup

```bash
# 1. Clone the repo
git clone https://github.com/MarcorX/lamp-advisor.git
cd lamp-advisor

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# 5. Run the app
uvicorn main:app --reload

# Open http://localhost:8000
```

---

## Deploy to Render.com (Free)

1. Fork or push this repo to your GitHub
2. Go to [render.com](https://render.com) → New → Web Service
3. Connect your GitHub repo
4. Set **Build Command**: `pip install -r requirements.txt`
5. Set **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Add environment variable: `ANTHROPIC_API_KEY` = your key
7. Deploy!

---

## CSV Import Format

Download the template from the app (`/lamps/template`) or use these columns:

| Column | Spanish alias | Example |
|--------|--------------|---------|
| brand | marca | Philips |
| model | modelo | CorePro 9W |
| category | categoria | downlight |
| wattage | vatios | 9 |
| lumens | — | 806 |
| color_temp | temperatura | 3000K |
| cri | irc | 80 |
| ip_rating | ip | IP44 |
| dimmable | regulable | True |
| property_level | nivel | basic / mid / premium / luxury |
| indoor_outdoor | interior_exterior | indoor / outdoor / both |
| price_usd | precio | 45.00 |
| space_type | espacio | living,bedroom |

---

## Property Levels

| Level | Description |
|-------|-------------|
| `basic` | Budget / económico — cost-efficient standard lamps |
| `mid` | Mid-range / estándar — balanced quality and price |
| `premium` | Premium — high CRI, dimmable, design-oriented |
| `luxury` | Luxury / lujo — top brands, tunable CCT, statement pieces |

---

## Getting Your Anthropic API Key

1. Sign up at [console.anthropic.com](https://console.anthropic.com)
2. Go to **API Keys** → Create key
3. Add it as `ANTHROPIC_API_KEY` in your `.env` or Render environment

> The app works without an API key — proposals still generate with built-in narratives.

---

## License

MIT
