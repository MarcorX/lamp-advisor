"""
LampAdvisor — Main FastAPI application (v2)
"""
import asyncio
import json
import os
import shutil
import threading
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, Depends, File, UploadFile, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

from database import init_db, get_db, Lamp, Project, Proposal
from services.file_parser import parse_file
from services.recommender import get_recommendations
from services.ai_engine import generate_proposal_narrative
import services.progress as progress
from services.ai_catalog_importer import run_import
from services.ai_project_analyzer import run_analysis
from services.chat_handler import handle_message
from services.ai_settings import load as load_settings, save as save_settings, provider_models

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
app = FastAPI(title="LampAdvisor")

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./static/uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.on_event("startup")
def on_startup():
    init_db()


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
    return templates.TemplateResponse("project_form.html", {"request": request})


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

        # Build rooms from analysis
        if analysis_data.get("rooms") and not project.rooms_detail:
            room_names = [r["name"] for r in analysis_data["rooms"] if r.get("name")]
            project.rooms_detail = ",".join(room_names)

        if analysis_data.get("special_requirements") and not project.special_requirements:
            project.special_requirements = analysis_data.get("special_requirements", "")

        project.extracted_text = json.dumps(analysis_data)
        project.status = "analyzed"
        db.commit()

        # Step 2 — recommendations
        emit("matching", "Matching catalog to project requirements…", 85)
        rooms = [r.strip() for r in (project.rooms_detail or "").replace(";", ",").split(",") if r.strip()]
        if not rooms:
            rooms = ["living", "bedroom", "kitchen", "bathroom"]

        project_dict = {
            "property_type":  project.property_type,
            "property_level": project.property_level,
            "total_sqm":      project.total_sqm or 80,
            "rooms":          rooms,
            "style":          project.style,
            "budget_usd":     project.budget_usd,
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
