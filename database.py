from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./lamp_advisor.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Lamp(Base):
    __tablename__ = "lamps"

    id = Column(Integer, primary_key=True, index=True)
    brand = Column(String(100), nullable=False)
    model = Column(String(200), nullable=False)
    category = Column(String(50))          # pendant, spot, panel, strip, downlight, wall, floor, track
    subcategory = Column(String(100))
    wattage = Column(Float)
    lumens = Column(Integer)
    efficacy_lm_w = Column(Float)          # lumens per watt
    color_temp = Column(String(50))        # 2700K, 3000K, 4000K, etc. or "tunable"
    cri = Column(Integer)                  # Color Rendering Index (80, 90, 95, 97)
    ip_rating = Column(String(20))         # IP20, IP44, IP65, IP67
    voltage = Column(String(50))           # 220V, 12V, 24V
    dimmable = Column(Boolean, default=False)
    beam_angle = Column(Float)             # degrees
    dimensions = Column(String(100))       # WxHxD in mm
    color_finish = Column(String(100))
    indoor_outdoor = Column(String(20))    # indoor, outdoor, both
    property_level = Column(String(20))    # basic, mid, premium, luxury
    space_type = Column(String(200))       # living_room, kitchen, bathroom, office, hotel, retail, etc.
    price_usd = Column(Float)
    currency = Column(String(10), default="USD")
    stock = Column(Integer, default=0)
    sku = Column(String(100))
    image_url = Column(String(500))
    datasheet_url = Column(String(500))
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    client_name = Column(String(200))
    property_type = Column(String(50))     # residential, commercial, office, hotel, restaurant, retail
    property_level = Column(String(20))    # basic, mid, premium, luxury
    total_sqm = Column(Float)
    num_rooms = Column(Integer)
    rooms_detail = Column(Text)            # JSON string with room breakdown
    style = Column(String(100))            # modern, classic, minimalist, industrial, etc.
    budget_usd = Column(Float)
    special_requirements = Column(Text)
    file_path = Column(String(500))
    file_type = Column(String(20))         # pdf, dwg, dxf, manual
    extracted_text = Column(Text)
    status = Column(String(20), default="pending")  # pending, analyzed, proposed
    created_at = Column(DateTime, default=datetime.utcnow)


class Proposal(Base):
    __tablename__ = "proposals"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, nullable=False)
    proposal_number = Column(Integer)      # 1, 2, or 3
    title = Column(String(200))
    description = Column(Text)
    total_price_usd = Column(Float)
    lamps_json = Column(Text)              # JSON list of {lamp_id, quantity, room, notes}
    ai_justification = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    email         = Column(String(200), unique=True, nullable=False, index=True)
    name          = Column(String(200), nullable=False)
    password_hash = Column(String(200), nullable=False)
    is_admin      = Column(Boolean, default=False)
    is_approved   = Column(Boolean, default=False)
    created_at    = Column(DateTime, default=datetime.utcnow)


def init_db():
    Base.metadata.create_all(bind=engine)
    _seed_admin()


def _seed_admin():
    """Ensure the default admin user always exists after every deploy."""
    from services.auth import hash_password
    admin_email = os.getenv("ADMIN_EMAIL", "carnalbro@gmail.com")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
    admin_name = os.getenv("ADMIN_NAME", "Marco")
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == admin_email).first()
        if not existing:
            db.add(User(
                email=admin_email,
                name=admin_name,
                password_hash=hash_password(admin_password),
                is_admin=True,
                is_approved=True,
            ))
            db.commit()
    finally:
        db.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
