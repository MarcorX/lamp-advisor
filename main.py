"""
LampAdvisor — Main FastAPI application (v2)
"""
import asyncio
import json
import os
import shutil
import threading
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, Request, Depends, File, UploadFile, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

from database import init_db, get_db, Lamp, Project, Proposal, User
from services.auth import hash_password, verify_password
from services.file_parser import parse_file
from services.recommender import get_recommendations
from services.ai_engine import generate_proposal_narrative
import services.progress as progress
from services.ai_catalog_importer import run_import
from services.ai_project_analyzer import run_analysis
from services.chat_handler import handle_message
from services.ai_settings import load as load_settings, save as save_settings, provider_models
import services.agent as agent_svc
from services.i18n import T, set_lang, get_lang

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
app = FastAPI(title="LampAdvisor")

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./static/uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Inject T() and lang() into every Jinja2 template automatically
templates.env.globals["T"] = T
templates.env.globals["lang"] = get_lang

SECRET_KEY = os.getenv("SECRET_KEY", "changeme-set-SECRET_KEY-in-production")

# Paths that don't require authentication
_PUBLIC_PATHS = {"/login", "/register", "/logout", "/pending", "/set-lang"}


class LangMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        lang = request.cookies.get("lang", "es")
        if lang not in ("es", "en"):
            lang = "es"
        set_lang(lang)
        request.state.lang = lang
        return await call_next(request)


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        is_public = path in _PUBLIC_PATHS or path.startswith("/static")

        uid = request.session.get("user_id")
        request.state.current_user = None

        if uid:
            from database import SessionLocal
            _db = SessionLocal()
            try:
                request.state.current_user = _db.query(User).filter(User.id == uid).first()
            finally:
                _db.close()
            # Clear stale session if user no longer exists (prevents redirect loop)
            if not request.state.current_user:
                request.session.pop("user_id", None)

        if not is_public:
            if not request.state.current_user:
                return RedirectResponse("/login", status_code=302)
            if not request.state.current_user.is_approved:
                return RedirectResponse("/pending", status_code=302)

        return await call_next(request)


# Middleware order: outermost first (last added = outermost in Starlette)
app.add_middleware(LangMiddleware)
app.add_middleware(AuthMiddleware)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)


@app.on_event("startup")
def on_startup():
    init_db()
    from seed_catalog import seed
    from database import SessionLocal
    _db = SessionLocal()
    try:
        seed(_db)
    finally:
        _db.close()


# ---------------------------------------------------------------------------
# Language switcher
# ---------------------------------------------------------------------------
@app.post("/set-lang")
async def set_language(lang: str = Form(...), next: str = Form("/")):
    if lang not in ("es", "en"):
        lang = "es"
    response = RedirectResponse(next, status_code=303)
    response.set_cookie("lang", lang, max_age=365 * 24 * 3600, httponly=True, samesite="lax")
    return response


# ---------------------------------------------------------------------------
# API Key / Anthropic Status Check
# ---------------------------------------------------------------------------
@app.get("/api/status")
async def api_status():
    """Tests the configured AI provider and returns connection status."""
    s = load_settings()
    provider = s.get("provider", "anthropic")
    model    = s.get("model", "")
    api_key  = s.get("api_key", "")
    base_url = s.get("base_url", "")

    if provider != "local" and (not api_key or api_key.startswith("your_")):
        return JSONResponse({
            "status": "missing",
            "provider": provider,
            "message": f"No API key set for {provider}",
            "model": model,
        })

    try:
        from services.ai_client import AIClient
        test_model = model

        # Use cheapest/fastest model for the ping
        if provider == "anthropic":
            test_model = "claude-haiku-4-5-20251001"
        elif provider == "openai":
            test_model = "gpt-4o-mini"

        client = AIClient(provider=provider, model=test_model,
                          api_key=api_key, base_url=base_url)
        reply = await asyncio.to_thread(
            client.complete,
            [{"role": "user", "content": "Reply with the single word: pong"}],
            "", 20,
        )
        key_preview = f"{api_key[:8]}…{api_key[-4:]}" if api_key else "none"
        return JSONResponse({
            "status": "ok",
            "provider": provider,
            "message": f"Connected — {provider} responded",
            "model": model,
            "test_model": test_model,
            "key_preview": key_preview,
            "reply": reply.strip()[:40],
        })
    except Exception as e:
        err = str(e)
        if "401" in err or "authentication" in err.lower() or "invalid" in err.lower():
            code, msg = "invalid_key", "API key is invalid or revoked"
        elif "403" in err:
            code, msg = "no_permission", "API key lacks permission"
        elif "connection" in err.lower() or "network" in err.lower() or "refused" in err.lower():
            code, msg = "network_error", f"Cannot reach {provider} — check URL/internet"
        else:
            code, msg = "error", err[:120]
        return JSONResponse({"status": code, "provider": provider,
                             "message": msg, "model": model})


# ---------------------------------------------------------------------------
# SSE Stream endpoint
# ---------------------------------------------------------------------------
@app.get("/stream/{session_id}")
async def sse_stream(session_id: str):
    async def event_generator():
        async for msg in progress.stream(session_id):
            yield f"data: {json.dumps(msg)}\n\n"
            if msg.get("done"):
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    lamp_count = db.query(Lamp).count()
    project_count = db.query(Project).count()
    proposal_count = db.query(Proposal).count()
    recent_projects = db.query(Project).order_by(Project.created_at.desc()).limit(5).all()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "lamp_count": lamp_count,
        "project_count": project_count,
        "proposal_count": proposal_count,
        "recent_projects": recent_projects,
    })


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------
@app.get("/chat", response_class=HTMLResponse)
def chat_page(request: Request, db: Session = Depends(get_db)):
    lamp_count = db.query(Lamp).count()
    return templates.TemplateResponse("chat.html", {
        "request": request,
        "lamp_count": lamp_count,
    })


@app.post("/api/chat")
async def api_chat(request: Request, db: Session = Depends(get_db)):
    body = await request.json()
    message = body.get("message", "")
    history = body.get("history", [])
    if not message.strip():
        return JSONResponse({"response": "", "tool_results": []})
    result = await asyncio.to_thread(handle_message, message, history, db)
    return JSONResponse(result)


# ---------------------------------------------------------------------------
# Lamp Database
# ---------------------------------------------------------------------------
@app.get("/lamps", response_class=HTMLResponse)
def lamps_list(
    request: Request,
    db: Session = Depends(get_db),
    search: str = "",
    category: str = "",
    level: str = "",
    page: int = 1,
):
    q = db.query(Lamp)
    if search:
        q = q.filter((Lamp.brand.ilike(f"%{search}%")) | (Lamp.model.ilike(f"%{search}%")))
    if category:
        q = q.filter(Lamp.category == category)
    if level:
        q = q.filter(Lamp.property_level == level)
    total = q.count()
    per_page = 20
    lamps = q.offset((page - 1) * per_page).limit(per_page).all()
    categories = [r[0] for r in db.query(Lamp.category).distinct() if r[0]]
    return templates.TemplateResponse("lamps.html", {
        "request": request, "lamps": lamps, "total": total, "page": page,
        "per_page": per_page, "search": search, "category": category,
        "level": level, "categories": sorted(categories),
    })


@app.get("/lamps/add", response_class=HTMLResponse)
def lamp_add_form(request: Request):
    return templates.TemplateResponse("lamp_form.html", {"request": request, "lamp": None})


@app.post("/lamps/add")
def lamp_add(db: Session = Depends(get_db), brand: str = Form(...), model: str = Form(...),
             category: str = Form(""), wattage: Optional[float] = Form(None),
             lumens: Optional[int] = Form(None), color_temp: str = Form(""),
             cri: Optional[int] = Form(None), ip_rating: str = Form(""),
             voltage: str = Form(""), dimmable: bool = Form(False),
             beam_angle: Optional[float] = Form(None), dimensions: str = Form(""),
             color_finish: str = Form(""), indoor_outdoor: str = Form("indoor"),
             property_level: str = Form("mid"), space_type: str = Form(""),
             price_usd: Optional[float] = Form(None), sku: str = Form(""),
             description: str = Form("")):
    lamp = Lamp(brand=brand, model=model, category=category, wattage=wattage, lumens=lumens,
                color_temp=color_temp, cri=cri, ip_rating=ip_rating, voltage=voltage,
                dimmable=dimmable, beam_angle=beam_angle, dimensions=dimensions,
                color_finish=color_finish, indoor_outdoor=indoor_outdoor,
                property_level=property_level, space_type=space_type,
                price_usd=price_usd, sku=sku, description=description)
    db.add(lamp)
    db.commit()
    return RedirectResponse("/lamps", status_code=303)


@app.get("/lamps/{lamp_id}/edit", response_class=HTMLResponse)
def lamp_edit_form(lamp_id: int, request: Request, db: Session = Depends(get_db)):
    lamp = db.query(Lamp).filter(Lamp.id == lamp_id).first()
    if not lamp:
        raise HTTPException(404)
    return templates.TemplateResponse("lamp_form.html", {"request": request, "lamp": lamp})


@app.post("/lamps/{lamp_id}/edit")
def lamp_edit(lamp_id: int, db: Session = Depends(get_db),
              brand: str = Form(...), model: str = Form(...), category: str = Form(""),
              wattage: Optional[float] = Form(None), lumens: Optional[int] = Form(None),
              color_temp: str = Form(""), cri: Optional[int] = Form(None),
              ip_rating: str = Form(""), voltage: str = Form(""), dimmable: bool = Form(False),
              beam_angle: Optional[float] = Form(None), dimensions: str = Form(""),
              color_finish: str = Form(""), indoor_outdoor: str = Form("indoor"),
              property_level: str = Form("mid"), space_type: str = Form(""),
              price_usd: Optional[float] = Form(None), sku: str = Form(""),
              description: str = Form("")):
    lamp = db.query(Lamp).filter(Lamp.id == lamp_id).first()
    if not lamp:
        raise HTTPException(404)
    for k, v in dict(brand=brand, model=model, category=category, wattage=wattage,
                     lumens=lumens, color_temp=color_temp, cri=cri, ip_rating=ip_rating,
                     voltage=voltage, dimmable=dimmable, beam_angle=beam_angle,
                     dimensions=dimensions, color_finish=color_finish,
                     indoor_outdoor=indoor_outdoor, property_level=property_level,
                     space_type=space_type, price_usd=price_usd, sku=sku,
                     description=description).items():
        setattr(lamp, k, v)
    db.commit()
    return RedirectResponse("/lamps", status_code=303)


@app.post("/lamps/{lamp_id}/delete")
def lamp_delete(lamp_id: int, db: Session = Depends(get_db)):
    lamp = db.query(Lamp).filter(Lamp.id == lamp_id).first()
    if lamp:
        db.delete(lamp)
        db.commit()
    return RedirectResponse("/lamps", status_code=303)


@app.post("/lamps/clear-all")
def lamps_clear_all(request: Request, db: Session = Depends(get_db)):
    """Delete all lamps from the catalog (admin only)."""
    user = request.state.current_user
    if not user or not user.is_admin:
        raise HTTPException(403, "Admin access required")
    deleted = db.query(Lamp).delete()
    db.commit()
    return RedirectResponse(f"/lamps?cleared={deleted}", status_code=303)


@app.post("/lamps/reload-seed")
def lamps_reload_seed(request: Request, db: Session = Depends(get_db)):
    """Wipe catalog and reload the built-in 500-lamp seed (admin only)."""
    user = request.state.current_user
    if not user or not user.is_admin:
        raise HTTPException(403, "Admin access required")
    from seed_catalog import seed
    count = seed(db=db, force=True)
    return RedirectResponse(f"/lamps?seeded={count}", status_code=303)


# ---------------------------------------------------------------------------
# Lamp Import — AI-powered
# ---------------------------------------------------------------------------
@app.get("/lamps/import", response_class=HTMLResponse)
def lamp_import_form(request: Request):
    return templates.TemplateResponse("lamp_import.html", {"request": request})


@app.post("/api/lamps/import")
async def api_lamp_import(
    request: Request,
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
):
    """JSON API — saves file, starts background import, returns session_id."""
    if not file.filename:
        raise HTTPException(400, "No file provided")
    ext = Path(file.filename).suffix.lower()
    if ext not in (".csv", ".xlsx", ".xls", ".pdf"):
        raise HTTPException(400, "Only CSV, Excel (.xlsx/.xls), or PDF accepted")

    save_path = UPLOAD_DIR / f"import_{file.filename}"
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    sid = progress.create_session()
    loop = asyncio.get_event_loop()

    # Run import in background thread (blocking I/O + AI calls)
    thread = threading.Thread(
        target=run_import,
        args=(str(save_path), db, sid, loop),
        daemon=True,
    )
    thread.start()

    return JSONResponse({"session_id": sid})


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------
@app.get("/projects", response_class=HTMLResponse)
def projects_list(request: Request, db: Session = Depends(get_db)):
    projects = db.query(Project).order_by(Project.created_at.desc()).all()
    return templates.TemplateResponse("projects.html", {"request": request, "projects": projects})


@app.get("/projects/new", response_class=HTMLResponse)
def new_project_form(request: Request):
    # The agent IS the new-project flow
    return templates.TemplateResponse("project_agent.html", {"request": request})


@app.post("/api/projects/analyze-preview")
async def api_analyze_preview(files: List[UploadFile] = File(...)):
    """Stateless file pre-analysis — accepts 1+ files, streams extracted data via SSE, no DB write."""
    if not files:
        raise HTTPException(400, "No files provided")
    saved_paths: list[str] = []
    for file in files:
        if not file or not file.filename:
            continue
        ext = Path(file.filename).suffix.lower()
        if ext not in (".pdf", ".dwg", ".dxf"):
            raise HTTPException(400, f"Unsupported file type: {file.filename}")
        save_path = UPLOAD_DIR / f"preview_{file.filename}"
        with open(save_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        saved_paths.append(str(save_path))
    if not saved_paths:
        raise HTTPException(400, "No valid files provided")
    sid = progress.create_session()
    loop = asyncio.get_event_loop()
    threading.Thread(
        target=_run_preview_analysis,
        args=(saved_paths, sid, loop),
        daemon=True,
    ).start()
    return JSONResponse({"session_id": sid})


def _run_preview_analysis(file_paths: list, session_id: str, loop: asyncio.AbstractEventLoop):
    from services.ai_project_analyzer import run_analysis, run_analysis_multi
    if len(file_paths) == 1:
        run_analysis(file_paths[0], session_id, loop)
    else:
        run_analysis_multi(file_paths, session_id, loop)
    for p in file_paths:
        Path(p).unlink(missing_ok=True)


@app.post("/api/projects/refine-analysis")
async def api_refine_analysis(request: Request):
    """Chat-style correction of an AI project analysis. Body: {current_data, message}."""
    body = await request.json()
    current_data = body.get("current_data") or {}
    message = (body.get("message") or "").strip()
    if not message:
        raise HTTPException(400, "message is required")

    from services.ai_client import get_client
    ai = get_client()
    if not ai.is_configured():
        raise HTTPException(503, "AI not configured — add an API key in Settings")

    prompt = (
        "You are a lighting design assistant reviewing an AI analysis of a floor plan.\n"
        "The current extracted data is:\n"
        f"{json.dumps(current_data, ensure_ascii=False, indent=2)}\n\n"
        f'The user says: "{message}"\n\n'
        "Update the JSON to reflect the user's correction and return ONLY the corrected JSON object "
        "— no explanation, no markdown fences.\n"
        "Rules:\n"
        "- Update rooms array if the user corrects room count/names\n"
        "- Update total_sqm if the user corrects the area\n"
        "- Preserve per-room specs (fixture_types, cri_min, etc.) when rooms are kept\n"
        "- For new rooms added, supply sensible lighting defaults\n"
        "- Preserve all other fields the user has not mentioned"
    )
    try:
        response = ai.complete(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000,
        ).strip()
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0].strip()
        elif "```" in response:
            response = response.split("```")[1].split("```")[0].strip()
        if not response.startswith("{"):
            start, end = response.find("{"), response.rfind("}")
            if start != -1:
                response = response[start:end + 1]
        data = json.loads(response)
        return JSONResponse({"data": data})
    except Exception as e:
        raise HTTPException(500, f"Refinement failed: {str(e)}")


# ---------------------------------------------------------------------------
# AI Lighting Agent routes
# ---------------------------------------------------------------------------

@app.get("/agent")
def agent_page(request: Request):
    return templates.TemplateResponse("project_agent.html", {"request": request})


@app.post("/api/agent/start")
async def api_agent_start(files: List[UploadFile] = File(...)):
    """Upload files → start AI analysis → SSE stream with progress + first agent message."""
    if not files:
        raise HTTPException(400, "No files provided")
    saved: list[str] = []
    for f in files:
        if not f or not f.filename:
            continue
        ext = Path(f.filename).suffix.lower()
        if ext not in (".pdf", ".dwg", ".dxf"):
            raise HTTPException(400, f"Unsupported file type: {f.filename}")
        dest = UPLOAD_DIR / f"agent_{f.filename}"
        with open(dest, "wb") as out:
            shutil.copyfileobj(f.file, out)
        saved.append(str(dest))
    if not saved:
        raise HTTPException(400, "No valid files provided")
    sid = progress.create_session()
    loop = asyncio.get_event_loop()
    threading.Thread(
        target=_run_agent_analysis,
        args=(saved, sid, loop),
        daemon=True,
    ).start()
    return JSONResponse({"session_id": sid})


def _run_agent_analysis(file_paths: list, session_id: str, loop: asyncio.AbstractEventLoop):
    agent_svc.analyze_project(file_paths, session_id, loop)
    for p in file_paths:
        Path(p).unlink(missing_ok=True)


@app.post("/api/agent/chat")
async def api_agent_chat(request: Request):
    """Continue the agent conversation. Body: {messages: [{role, content}, ...]}."""
    body = await request.json()
    messages = body.get("messages") or []
    if not messages:
        raise HTTPException(400, "messages required")
    from services.ai_client import get_client
    ai = get_client()
    if not ai.is_configured():
        raise HTTPException(503, "AI not configured")
    try:
        reply = agent_svc.chat_turn(messages, ai)
        return JSONResponse({"reply": reply})
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/agent/brief")
async def api_agent_brief(request: Request):
    """Generate structured requirements brief from conversation. Body: {messages: [...]}."""
    body = await request.json()
    messages = body.get("messages") or []
    from services.ai_client import get_client
    ai = get_client()
    if not ai.is_configured():
        raise HTTPException(503, "AI not configured")
    try:
        brief = agent_svc.generate_brief(messages, ai)
        return JSONResponse({"brief": brief})
    except Exception as e:
        raise HTTPException(500, f"Brief generation failed: {str(e)}")


@app.post("/api/agent/propose")
async def api_agent_propose(request: Request, db: Session = Depends(get_db)):
    """Match brief requirements against catalog. Body: {brief: [...]}."""
    body = await request.json()
    brief = body.get("brief") or []
    if not brief:
        raise HTTPException(400, "brief required")
    try:
        items = agent_svc.match_catalog(brief, db)
        total = round(sum(i["subtotal"] for i in items), 2)
        return JSONResponse({"items": items, "total": total})
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/agent/save")
async def api_agent_save(request: Request, db: Session = Depends(get_db)):
    """Save agent proposal to DB. Returns {project_id} for redirect."""
    body = await request.json()
    name        = (body.get("name") or "Untitled Project").strip()
    client_name = (body.get("client_name") or "").strip() or None
    proposal_items = body.get("proposal") or []
    total       = float(body.get("total") or 0)
    agent_intro = (body.get("agent_intro") or "")[:2000]   # first AI message as justification

    project = Project(
        name=name,
        client_name=client_name,
        status="proposed",
    )
    db.add(project)
    db.flush()

    # Map agent proposal items → room_assignments format used by proposals.html
    room_assignments = [
        {
            "room":           item.get("space") or item.get("label") or "—",
            "lamp_id":        item.get("lamp_id"),
            "lamp_brand":     item.get("lamp_brand", ""),
            "lamp_model":     item.get("lamp_model", ""),
            "lamp_category":  item.get("lamp_category", ""),
            "lamp_wattage":   item.get("lamp_wattage"),
            "lamp_lumens":    item.get("lamp_lumens"),
            "lamp_color_temp":item.get("lamp_cct", ""),
            "lamp_cri":       item.get("lamp_cri"),
            "lamp_dimmable":  item.get("lamp_dimmable", False),
            "lamp_ip":        item.get("lamp_ip", ""),
            "lamp_price":     item.get("lamp_price"),
            "quantity":       item.get("qty", 1),
            "subtotal":       item.get("subtotal", 0),
            "room_notes":     item.get("notes", ""),
        }
        for item in proposal_items
    ]

    proposal = Proposal(
        project_id=project.id,
        proposal_number=1,
        title="AI Agent Lighting Proposal",
        ai_justification=agent_intro,
        total_price_usd=total,
        lamps_json=json.dumps(room_assignments),
    )
    db.add(proposal)
    db.commit()
    return JSONResponse({"project_id": project.id})


@app.post("/api/projects/new")
async def api_new_project(
    request: Request,
    db: Session = Depends(get_db),
    name: str = Form(...),
    client_name: str = Form(""),
    property_type: str = Form("residential"),
    property_level: str = Form("mid"),
    total_sqm: Optional[float] = Form(None),
    num_rooms: Optional[int] = Form(None),
    rooms_detail: str = Form(""),
    style: str = Form(""),
    budget_usd: Optional[float] = Form(None),
    special_requirements: str = Form(""),
    file: Optional[UploadFile] = File(None),
):
    """JSON API — creates project, starts background analysis, returns project_id + session_id."""
    file_path = ""
    file_type = "manual"

    if file and file.filename:
        ext = Path(file.filename).suffix.lower()
        if ext not in (".pdf", ".dwg", ".dxf"):
            return JSONResponse({"error": "Only PDF, DWG, or DXF files accepted"}, status_code=400)
        save_path = UPLOAD_DIR / f"project_{file.filename}"
        with open(save_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        file_path = str(save_path)
        file_type = ext.lstrip(".")

    project = Project(
        name=name, client_name=client_name, property_type=property_type,
        property_level=property_level, total_sqm=total_sqm, num_rooms=num_rooms,
        rooms_detail=rooms_detail, style=style, budget_usd=budget_usd,
        special_requirements=special_requirements, file_path=file_path,
        file_type=file_type, extracted_text="", status="pending",
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    sid = progress.create_session()
    loop = asyncio.get_event_loop()

    thread = threading.Thread(
        target=_run_project_analysis,
        args=(project.id, file_path, file_type, db, sid, loop),
        daemon=True,
    )
    thread.start()

    return JSONResponse({"project_id": project.id, "session_id": sid})


def _run_project_analysis(
    project_id: int,
    file_path: str,
    file_type: str,
    db: Session,
    session_id: str,
    loop: asyncio.AbstractEventLoop,
):
    """Background worker: analyze project file → update DB → generate proposals."""
    from services.progress import push_sync

    def emit(step, msg, progress_pct=0, done=False, **kwargs):
        push_sync(session_id, loop, {"step": step, "msg": msg, "progress": progress_pct, "done": done, **kwargs})

    try:
        # Step 1 — file analysis
        analysis_data = {}
        if file_path:
            analysis_data = run_analysis(file_path, session_id, loop) or {}
        else:
            emit("skip", "No file — using form data", 30)

        # Update project with extracted data
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            emit("error", "Project not found", done=True)
            return

        if analysis_data.get("total_sqm") and not project.total_sqm:
            project.total_sqm = analysis_data["total_sqm"]
        if analysis_data.get("property_type") and project.property_type == "residential":
            project.property_type = analysis_data["property_type"]
        if analysis_data.get("property_level") and project.property_level == "mid":
            project.property_level = analysis_data["property_level"]
        if analysis_data.get("style") and not project.style:
            project.style = analysis_data["style"]

        # Build rooms from analysis — store full JSON for recommender
        if analysis_data.get("rooms"):
            rooms_full = analysis_data["rooms"]
            # Always update rooms_detail with the richer JSON from AI
            project.rooms_detail = json.dumps(rooms_full, ensure_ascii=False)
        elif not project.rooms_detail:
            project.rooms_detail = ""

        if analysis_data.get("special_requirements") and not project.special_requirements:
            project.special_requirements = analysis_data.get("special_requirements", "")

        project.extracted_text = json.dumps(analysis_data)
        project.status = "analyzed"
        db.commit()

        # Step 2 — recommendations
        emit("matching", "Matching catalog to project requirements…", 85)

        # Try to use full room dicts from AI; fall back to plain name strings
        rooms_raw = project.rooms_detail or ""
        rooms: list = []
        if rooms_raw.strip().startswith("["):
            try:
                rooms = json.loads(rooms_raw)
            except Exception:
                pass
        if not rooms:
            # Legacy: comma-separated room names
            rooms = [r.strip() for r in rooms_raw.replace(";", ",").split(",") if r.strip()]
        if not rooms:
            rooms = ["living", "bedroom", "kitchen", "bathroom"]

        project_dict = {
            "property_type":        project.property_type,
            "property_level":       project.property_level,
            "total_sqm":            project.total_sqm or 80,
            "rooms":                rooms,
            "style":                project.style,
            "budget_usd":           project.budget_usd,
            "special_requirements": project.special_requirements,
        }

        lamp_count = db.query(Lamp).count()
        if lamp_count == 0:
            emit("done", "Analysis complete — but no lamps in catalog yet!", 100, done=True,
                 redirect=f"/projects/{project_id}", warning="no_lamps")
            return

        raw_proposals = get_recommendations(db, project_dict, num_proposals=3)

        # Step 3 — AI narratives
        emit("ai", "Claude is writing proposal narratives…", 90)
        enriched = generate_proposal_narrative(
            project_dict, raw_proposals, project.extracted_text or ""
        )

        # Persist proposals
        db.query(Proposal).filter(Proposal.project_id == project_id).delete()
        for p in enriched:
            saved = Proposal(
                project_id=project_id,
                proposal_number=p["proposal_number"],
                title=p["title"],
                description=p.get("ai_justification", ""),
                total_price_usd=p["total_price"],
                lamps_json=json.dumps(p["room_assignments"]),
                ai_justification=p.get("ai_justification", ""),
            )
            db.add(saved)
        project.status = "proposed"
        db.commit()

        emit("done", "✓ Proposals ready!", 100, done=True,
             redirect=f"/projects/{project_id}/proposals")

    except Exception as e:
        emit("error", f"Analysis failed: {str(e)}", done=True,
             redirect=f"/projects/{project_id}")


@app.get("/projects/{project_id}/analyze", response_class=HTMLResponse)
def project_analyze_page(project_id: int, request: Request, sid: str = "",
                          db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(404)
    return templates.TemplateResponse("project_analyze.html", {
        "request": request,
        "project": project,
        "session_id": sid,
    })


@app.get("/projects/{project_id}/proposals", response_class=HTMLResponse)
def project_proposals(project_id: int, request: Request, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(404)

    saved_proposals = db.query(Proposal).filter(
        Proposal.project_id == project_id
    ).order_by(Proposal.proposal_number).all()

    proposals = []
    for sp in saved_proposals:
        proposals.append({
            "proposal_number": sp.proposal_number,
            "title": sp.title,
            "ai_justification": sp.ai_justification,
            "total_price": sp.total_price_usd,
            "room_assignments": json.loads(sp.lamps_json or "[]"),
            "db_id": sp.id,
        })

    return templates.TemplateResponse("proposals.html", {
        "request": request,
        "project": project,
        "proposals": proposals,
        "error": None if proposals else "No proposals found. Please regenerate.",
    })


@app.get("/projects/{project_id}/regenerate")
def regenerate_proposals(project_id: int, db: Session = Depends(get_db)):
    """Deletes saved proposals and triggers a full re-analysis redirect."""
    db.query(Proposal).filter(Proposal.project_id == project_id).delete()
    project = db.query(Project).filter(Project.id == project_id).first()
    if project:
        project.status = "pending"
        db.commit()

    # Re-run analysis using existing file
    project = db.query(Project).filter(Project.id == project_id).first()
    sid = progress.create_session()
    loop = asyncio.get_event_loop()
    thread = threading.Thread(
        target=_run_project_analysis,
        args=(project_id, project.file_path or "", project.file_type or "manual", db, sid, loop),
        daemon=True,
    )
    thread.start()
    return RedirectResponse(f"/projects/{project_id}/analyze?sid={sid}", status_code=303)


@app.get("/projects/{project_id}", response_class=HTMLResponse)
def project_detail(project_id: int, request: Request, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(404)
    proposals = db.query(Proposal).filter(Proposal.project_id == project_id).all()
    return templates.TemplateResponse("project_detail.html", {
        "request": request, "project": project, "proposals": proposals
    })


@app.delete("/api/projects/{project_id}")
def api_delete_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(404, "Project not found")
    db.query(Proposal).filter(Proposal.project_id == project_id).delete()
    db.delete(project)
    db.commit()
    return JSONResponse({"ok": True})


@app.patch("/api/projects/{project_id}")
async def api_update_project(project_id: int, request: Request, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(404, "Project not found")
    body = await request.json()
    if "name" in body and body["name"].strip():
        project.name = body["name"].strip()
    if "client_name" in body:
        project.client_name = body["client_name"].strip() or None
    if "status" in body and body["status"] in ("pending", "analyzed", "proposed"):
        project.status = body["status"]
    db.commit()
    return JSONResponse({"ok": True})


@app.get("/projects", response_class=HTMLResponse)
def projects_list_2(request: Request, db: Session = Depends(get_db)):
    projects = db.query(Project).order_by(Project.created_at.desc()).all()
    return templates.TemplateResponse("projects.html", {"request": request, "projects": projects})


# Legacy project creation form fallback (no file)
@app.post("/projects/new")
async def new_project_form_post(
    request: Request,
    db: Session = Depends(get_db),
    name: str = Form(...),
    client_name: str = Form(""),
    property_type: str = Form("residential"),
    property_level: str = Form("mid"),
    total_sqm: Optional[float] = Form(None),
    num_rooms: Optional[int] = Form(None),
    rooms_detail: str = Form(""),
    style: str = Form(""),
    budget_usd: Optional[float] = Form(None),
    special_requirements: str = Form(""),
):
    """Plain form fallback — no file upload, no SSE."""
    project = Project(
        name=name, client_name=client_name, property_type=property_type,
        property_level=property_level, total_sqm=total_sqm, num_rooms=num_rooms,
        rooms_detail=rooms_detail, style=style, budget_usd=budget_usd,
        special_requirements=special_requirements, file_type="manual", status="analyzed",
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return RedirectResponse(f"/projects/{project.id}/regenerate", status_code=303)


# ---------------------------------------------------------------------------
# Proposal print
# ---------------------------------------------------------------------------
@app.get("/proposals/{proposal_id}/print", response_class=HTMLResponse)
def print_proposal(proposal_id: int, request: Request, db: Session = Depends(get_db)):
    proposal = db.query(Proposal).filter(Proposal.id == proposal_id).first()
    if not proposal:
        raise HTTPException(404)
    project = db.query(Project).filter(Project.id == proposal.project_id).first()
    lamps = json.loads(proposal.lamps_json or "[]")
    return templates.TemplateResponse("proposal_print.html", {
        "request": request, "proposal": proposal, "project": project, "lamps": lamps
    })


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
@app.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request):
    user = request.state.current_user
    if not user or not user.is_admin:
        raise HTTPException(403)
    s = load_settings()
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "settings": s,
        "provider_models": provider_models(),
    })


@app.post("/settings")
async def settings_save(
    request: Request,
    provider:  str = Form("anthropic"),
    model:     str = Form(""),
    api_key:   str = Form(""),
    base_url:  str = Form(""),
):
    if not request.state.current_user or not request.state.current_user.is_admin:
        raise HTTPException(403)
    save_settings(provider=provider, model=model, api_key=api_key, base_url=base_url)
    return RedirectResponse("/settings?saved=1", status_code=303)


# ---------------------------------------------------------------------------
# CSV Template download
# ---------------------------------------------------------------------------
@app.get("/lamps/template")
def download_template():
    import io
    from fastapi.responses import StreamingResponse as SR
    headers = ["brand", "model", "category", "wattage", "lumens", "color_temp", "cri",
               "ip_rating", "voltage", "dimmable", "beam_angle", "dimensions",
               "color_finish", "indoor_outdoor", "property_level", "space_type",
               "price_usd", "sku", "description"]
    sample = ["Philips", "CorePro LED", "downlight", "9", "806", "3000K", "80",
              "IP20", "220V", "True", "36", "Ø120mm", "White", "indoor", "mid",
              "living,bedroom", "45", "PH-CORE-9", "Efficient LED downlight"]
    csv_content = ",".join(headers) + "\n" + ",".join(sample) + "\n"
    return SR(io.StringIO(csv_content), media_type="text/csv",
              headers={"Content-Disposition": "attachment; filename=lamp_template.csv"})


# ---------------------------------------------------------------------------
# Auth — Login / Register / Logout
# ---------------------------------------------------------------------------
@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@app.post("/login", response_class=HTMLResponse)
def login_post(
    request: Request,
    db: Session = Depends(get_db),
    email: str = Form(...),
    password: str = Form(...),
):
    user = db.query(User).filter(User.email == email.lower().strip()).first()
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse("login.html", {
            "request": request, "error": "Invalid email or password."
        })
    if not user.is_approved:
        return templates.TemplateResponse("login.html", {
            "request": request, "error": "Your account is pending admin approval."
        })
    request.session["user_id"] = user.id
    return RedirectResponse("/projects/new", status_code=302)


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=302)


@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse("register.html", {"request": request, "error": None})


@app.post("/register", response_class=HTMLResponse)
def register_post(
    request: Request,
    db: Session = Depends(get_db),
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    password2: str = Form(...),
):
    email = email.lower().strip()

    if password != password2:
        return templates.TemplateResponse("register.html", {
            "request": request, "error": "Passwords do not match."
        })
    if len(password) < 8:
        return templates.TemplateResponse("register.html", {
            "request": request, "error": "Password must be at least 8 characters."
        })
    if db.query(User).filter(User.email == email).first():
        return templates.TemplateResponse("register.html", {
            "request": request, "error": "An account with that email already exists."
        })

    user = User(
        email=email,
        name=name.strip(),
        password_hash=hash_password(password),
        is_admin=False,
        is_approved=False,
    )
    db.add(user)
    db.commit()
    return RedirectResponse("/pending", status_code=302)


@app.get("/pending", response_class=HTMLResponse)
def pending_page(request: Request):
    return templates.TemplateResponse("pending.html", {"request": request})


# ---------------------------------------------------------------------------
# Admin — User Management
# ---------------------------------------------------------------------------
@app.get("/admin/users", response_class=HTMLResponse)
def admin_users(request: Request, db: Session = Depends(get_db)):
    user = request.state.current_user
    if not user or not user.is_admin:
        raise HTTPException(403, "Admin access required")
    users = db.query(User).order_by(User.created_at.desc()).all()
    return templates.TemplateResponse("admin_users.html", {
        "request": request, "users": users
    })


@app.post("/admin/users/{user_id}/approve")
def admin_approve(user_id: int, request: Request, db: Session = Depends(get_db)):
    if not request.state.current_user or not request.state.current_user.is_admin:
        raise HTTPException(403)
    u = db.query(User).filter(User.id == user_id).first()
    if u:
        u.is_approved = True
        db.commit()
    return RedirectResponse("/admin/users", status_code=303)


@app.post("/admin/users/{user_id}/reject")
def admin_reject(user_id: int, request: Request, db: Session = Depends(get_db)):
    if not request.state.current_user or not request.state.current_user.is_admin:
        raise HTTPException(403)
    u = db.query(User).filter(User.id == user_id).first()
    if u and u.id != request.state.current_user.id:  # can't delete yourself
        db.delete(u)
        db.commit()
    return RedirectResponse("/admin/users", status_code=303)


@app.post("/admin/users/{user_id}/toggle-admin")
def admin_toggle(user_id: int, request: Request, db: Session = Depends(get_db)):
    if not request.state.current_user or not request.state.current_user.is_admin:
        raise HTTPException(403)
    u = db.query(User).filter(User.id == user_id).first()
    if u and u.id != request.state.current_user.id:  # can't demote yourself
        u.is_admin = not u.is_admin
        db.commit()
    return RedirectResponse("/admin/users", status_code=303)


@app.post("/admin/users/create")
async def admin_create_user(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    is_admin: str = Form(""),
    db: Session = Depends(get_db),
):
    if not request.state.current_user or not request.state.current_user.is_admin:
        raise HTTPException(403)
    if len(password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    existing = db.query(User).filter(User.email == email.lower().strip()).first()
    if existing:
        return RedirectResponse("/admin/users?exists=1", status_code=303)
    user = User(
        name=name.strip(),
        email=email.lower().strip(),
        password_hash=hash_password(password),
        is_approved=True,
        is_admin=bool(is_admin),
    )
    db.add(user)
    db.commit()
    return RedirectResponse("/admin/users?created=1", status_code=303)


@app.post("/admin/users/{user_id}/set-password")
async def admin_set_password(
    user_id: int,
    request: Request,
    new_password: str = Form(...),
    db: Session = Depends(get_db),
):
    if not request.state.current_user or not request.state.current_user.is_admin:
        raise HTTPException(403)
    if len(new_password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(404)
    u.password_hash = hash_password(new_password)
    db.commit()
    return RedirectResponse("/admin/users?pw_reset=1", status_code=303)
