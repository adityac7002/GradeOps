import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

load_dotenv()

from backend.db.session import engine, Base
from backend.api.v1.endpoints import auth, exams, rubrics, grading, plagiarism

FRONTEND_BUILD = Path("frontend/dist")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all DB tables on startup
    Base.metadata.create_all(bind=engine)
    # Ensure upload dirs exist
    Path("uploads").mkdir(exist_ok=True)
    Path("uploads/crops").mkdir(exist_ok=True)
    yield


app = FastAPI(
    title="GradeOps API",
    description="Human-in-the-Loop AI exam grading platform",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow the Vite dev server and same-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev
        "http://localhost:8000",  # FastAPI self
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API routers ────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(exams.router)
app.include_router(rubrics.router)
app.include_router(grading.router)
app.include_router(plagiarism.router)


# ── Serve uploaded images ──────────────────────────────────────────────────────
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


# ── Serve React frontend (production build) ────────────────────────────────────
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
            "note": "Frontend not built yet — run: cd frontend && npm run build",
        }
