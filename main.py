"""
LampAdvisor — Main FastAPI application
"""
import os
import json
import shutil
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, Depends, File, UploadFile, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
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
# Dashboard
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    lamp_count   = db.query(Lamp).count()
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
        "request": request,
        "lamps": lamps,
        "total": total,
        "page": page,
        "per_page": per_page,
        "search": search,
        "category": category,
        "level": level,
        "categories": categories,
    })


@app.get("/lamps/add", response_class=HTMLResponse)
def lamp_add_form(request: Request):
    return templates.TemplateResponse("lamp_form.html", {"request": request, "lamp": None})


@app.post("/lamps/add")
def lamp_add(
    request: Request,
    db: Session = Depends(get_db),
    brand: str = Form(...),
    model: str = Form(...),
    category: str = Form(""),
    wattage: Optional[float] = Form(None),
    lumens: Optional[int] = Form(None),
    color_temp: str = Form(""),
    cri: Optional[int] = Form(None),
    ip_rating: str = Form(""),
    voltage: str = Form(""),
    dimmable: bool = Form(False),
    beam_angle: Optional[float] = Form(None),
    dimensions: str = Form(""),
    color_finish: str = Form(""),
    indoor_outdoor: str = Form("indoor"),
    property_level: str = Form("mid"),
    space_type: str = Form(""),
    price_usd: Optional[float] = Form(None),
    sku: str = Form(""),
    description: str = Form(""),
):
    lamp = Lamp(
        brand=brand, model=model, category=category, wattage=wattage, lumens=lumens,
        color_temp=color_temp, cri=cri, ip_rating=ip_rating, voltage=voltage,
        dimmable=dimmable, beam_angle=beam_angle, dimensions=dimensions,
        color_finish=color_finish, indoor_outdoor=indoor_outdoor,
        property_level=property_level, space_type=space_type,
        price_usd=price_usd, sku=sku, description=description,
    )
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
def lamp_edit(
    lamp_id: int,
    db: Session = Depends(get_db),
    brand: str = Form(...),
    model: str = Form(...),
    category: str = Form(""),
    wattage: Optional[float] = Form(None),
    lumens: Optional[int] = Form(None),
    color_temp: str = Form(""),
    cri: Optional[int] = Form(None),
    ip_rating: str = Form(""),
    voltage: str = Form(""),
    dimmable: bool = Form(False),
    beam_angle: Optional[float] = Form(None),
    dimensions: str = Form(""),
    color_finish: str = Form(""),
    indoor_outdoor: str = Form("indoor"),
    property_level: str = Form("mid"),
    space_type: str = Form(""),
    price_usd: Optional[float] = Form(None),
    sku: str = Form(""),
    description: str = Form(""),
):
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


@app.get("/lamps/import", response_class=HTMLResponse)
def lamp_import_form(request: Request):
    return templates.TemplateResponse("lamp_import.html", {"request": request})


@app.post("/lamps/import")
async def lamp_import(
    request: Request,
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
):
    if not file.filename.endswith((".csv", ".xlsx", ".xls")):
        return templates.TemplateResponse("lamp_import.html", {
            "request": request,
            "error": "Only CSV or Excel files are accepted."
        })

    tmp_path = UPLOAD_DIR / f"import_{file.filename}"
    with open(tmp_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        if file.filename.endswith(".csv"):
            df = pd.read_csv(tmp_path)
        else:
            df = pd.read_excel(tmp_path)

        # Normalize column names
        df.columns = [c.lower().strip().replace(" ", "_") for c in df.columns]

        col_map = {
            "marca": "brand", "fabricante": "brand",
            "modelo": "model", "nombre": "model",
            "categoria": "category", "tipo": "category",
            "vatios": "wattage", "watts": "wattage", "w": "wattage",
            "lumens": "lumens", "lm": "lumens",
            "temperatura": "color_temp", "temp_color": "color_temp", "cct": "color_temp",
            "irc": "cri", "color_rendering": "cri",
            "ip": "ip_rating", "proteccion": "ip_rating",
            "voltaje": "voltage", "tension": "voltage",
            "regulable": "dimmable", "dimmer": "dimmable",
            "precio": "price_usd", "price": "price_usd", "costo": "price_usd",
            "nivel": "property_level", "gama": "property_level",
            "espacio": "space_type", "uso": "space_type",
            "interior_exterior": "indoor_outdoor",
        }
        df.rename(columns=col_map, inplace=True)

        added = 0
        for _, row in df.iterrows():
            lamp = Lamp(
                brand=str(row.get("brand", "Unknown")),
                model=str(row.get("model", "Unknown")),
                category=str(row.get("category", "")) if pd.notna(row.get("category")) else "",
                wattage=float(row["wattage"]) if pd.notna(row.get("wattage")) else None,
                lumens=int(row["lumens"]) if pd.notna(row.get("lumens")) else None,
                color_temp=str(row.get("color_temp", "")) if pd.notna(row.get("color_temp")) else "",
                cri=int(row["cri"]) if pd.notna(row.get("cri")) else None,
                ip_rating=str(row.get("ip_rating", "")) if pd.notna(row.get("ip_rating")) else "",
                voltage=str(row.get("voltage", "")) if pd.notna(row.get("voltage")) else "",
                dimmable=bool(row.get("dimmable", False)),
                indoor_outdoor=str(row.get("indoor_outdoor", "indoor")),
                property_level=str(row.get("property_level", "mid")),
                space_type=str(row.get("space_type", "")) if pd.notna(row.get("space_type")) else "",
                price_usd=float(row["price_usd"]) if pd.notna(row.get("price_usd")) else None,
                sku=str(row.get("sku", "")) if pd.notna(row.get("sku")) else "",
                description=str(row.get("description", "")) if pd.notna(row.get("description")) else "",
            )
            db.add(lamp)
            added += 1

        db.commit()
        tmp_path.unlink(missing_ok=True)
        return templates.TemplateResponse("lamp_import.html", {
            "request": request,
            "success": f"Successfully imported {added} lamps."
        })

    except Exception as e:
        tmp_path.unlink(missing_ok=True)
        return templates.TemplateResponse("lamp_import.html", {
            "request": request,
            "error": f"Import failed: {str(e)}"
        })


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


@app.post("/projects/new")
async def new_project(
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
    file_path = ""
    file_type = "manual"
    extracted_text = ""
    extracted_data = {}

    if file and file.filename:
        ext = Path(file.filename).suffix.lower()
        if ext not in (".pdf", ".dwg", ".dxf"):
            return templates.TemplateResponse("project_form.html", {
                "request": request,
                "error": "Only PDF, DWG, or DXF files accepted."
            })
        save_path = UPLOAD_DIR / f"project_{file.filename}"
        with open(save_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        file_path = str(save_path)
        file_type = ext.lstrip(".")
        result = parse_file(file_path)
        extracted_text = result.get("raw_text", "")
        extracted_data = result.get("extracted", {})

        # Auto-fill missing fields from extracted data
        if not total_sqm and extracted_data.get("total_sqm"):
            total_sqm = extracted_data["total_sqm"]
        if not property_type and extracted_data.get("property_type"):
            property_type = extracted_data["property_type"]
        if not property_level and extracted_data.get("property_level"):
            property_level = extracted_data["property_level"]
        if not rooms_detail and extracted_data.get("rooms"):
            rooms_detail = ",".join(extracted_data["rooms"])
        if not style and extracted_data.get("style"):
            style = extracted_data["style"]

    project = Project(
        name=name, client_name=client_name, property_type=property_type,
        property_level=property_level, total_sqm=total_sqm, num_rooms=num_rooms,
        rooms_detail=rooms_detail, style=style, budget_usd=budget_usd,
        special_requirements=special_requirements, file_path=file_path,
        file_type=file_type, extracted_text=extracted_text, status="analyzed",
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return RedirectResponse(f"/projects/{project.id}/recommend", status_code=303)


@app.get("/projects/{project_id}", response_class=HTMLResponse)
def project_detail(project_id: int, request: Request, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(404)
    proposals = db.query(Proposal).filter(Proposal.project_id == project_id).all()
    return templates.TemplateResponse("project_detail.html", {
        "request": request, "project": project, "proposals": proposals
    })


@app.get("/projects/{project_id}/recommend", response_class=HTMLResponse)
def recommend(project_id: int, request: Request, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(404)

    # Build project dict for engines
    rooms = []
    if project.rooms_detail:
        rooms = [r.strip() for r in project.rooms_detail.replace(";", ",").split(",") if r.strip()]
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
        return templates.TemplateResponse("proposals.html", {
            "request": request,
            "project": project,
            "proposals": [],
            "error": "No lamps in database. Please import your lamp catalog first.",
        })

    raw_proposals = get_recommendations(db, project_dict, num_proposals=3)
    if not raw_proposals:
        return templates.TemplateResponse("proposals.html", {
            "request": request, "project": project, "proposals": [],
            "error": "Could not generate recommendations. Check that your lamp database has entries with matching property levels.",
        })

    enriched = generate_proposal_narrative(project_dict, raw_proposals, project.extracted_text or "")

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

    return templates.TemplateResponse("proposals.html", {
        "request": request,
        "project": project,
        "proposals": enriched,
    })


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
# CSV Template download
# ---------------------------------------------------------------------------
@app.get("/lamps/template")
def download_template():
    import io
    from fastapi.responses import StreamingResponse
    headers = ["brand","model","category","wattage","lumens","color_temp","cri",
               "ip_rating","voltage","dimmable","beam_angle","dimensions",
               "color_finish","indoor_outdoor","property_level","space_type",
               "price_usd","sku","description"]
    sample = ["Philips","CorePro LED","downlight","9","806","3000K","80",
              "IP20","220V","True","36","Ø120mm","White","indoor","mid",
              "living,bedroom","45","PH-CORE-9","Efficient LED downlight"]
    csv_content = ",".join(headers) + "\n" + ",".join(sample) + "\n"
    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=lamp_template.csv"}
    )
