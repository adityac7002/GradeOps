import os
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

load_dotenv()

from backend.db.session import engine, Base, SessionLocal
from backend.db import models
from backend.core.security import hash_password
from backend.api.v1.api import api_router

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FRONTEND_BUILD = Path("frontend/dist")
STORAGE_DIR = Path("storage")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Create tables
    Base.metadata.create_all(bind=engine)
    
    # 2. Ensure storage dirs exist
    STORAGE_DIR.mkdir(exist_ok=True)
    (STORAGE_DIR / "exams").mkdir(exist_ok=True)
    
    # 3. Seed users for Day 1
    db = SessionLocal()
    try:
        if not db.query(models.User).filter(models.User.email == "admin@gradeops.com").first():
            logger.info("Seeding admin (instructor) user...")
            admin = models.User(
                email="admin@gradeops.com",
                password_hash=hash_password("admin123"),
                role="instructor"
            )
            db.add(admin)
        
        if not db.query(models.User).filter(models.User.email == "ta@gradeops.com").first():
            logger.info("Seeding TA user...")
            ta = models.User(
                email="ta@gradeops.com",
                password_hash=hash_password("ta123"),
                role="ta"
            )
            db.add(ta)
        
        db.commit()
    finally:
        db.close()
        
    yield

app = FastAPI(
    title="GradeOps — AI Grading Platform",
    description="Enterprise-grade AI-assisted handwritten exam evaluation",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS config as per Day 1 requirements
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include v1 API
app.include_router(api_router, prefix="/api")

# Serve storage files (answer crops, etc)
app.mount("/storage", StaticFiles(directory="storage"), name="storage")

# Serve React frontend
if FRONTEND_BUILD.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_BUILD / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        index = FRONTEND_BUILD / "index.html"
        return FileResponse(str(index))
else:
    @app.get("/", include_in_schema=False)
    async def root():
        return {
            "message": "GradeOps API is online!",
            "docs": "/docs",
            "status": "Day 1 Skeleton Active"
        }
