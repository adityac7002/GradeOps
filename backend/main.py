"""
GradeOps — Application Entry Point

Production-grade FastAPI bootstrap:
- Centralized config validation at startup (fail fast)
- Structured logging before anything else
- Proper lifespan context manager
- Full middleware stack (CORS, request IDs, error handling)
- Health check endpoint
- Static file serving with proper path isolation
- Seed data guarded behind environment check
"""
import logging
import time
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

# ── Bootstrap logging FIRST before any other import ──────────────────────────
from backend.core.logging import setup_logging
setup_logging()

# ── Now load everything else ──────────────────────────────────────────────────
from backend.config import get_settings
from backend.db.session import engine, Base, SessionLocal
from backend.db import models  # noqa: F401 — ensures models are registered
from backend.api.v1.api import api_router
from backend.middleware.request_id import RequestIDMiddleware
from backend.middleware.error_handler import ErrorHandlerMiddleware

logger = logging.getLogger("gradeops.main")
settings = get_settings()

_startup_time = time.time()
FRONTEND_BUILD = Path("frontend/dist")
STORAGE_DIR = Path(settings.STORAGE_DIR)


# ── Lifespan (startup / shutdown) ────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Startup:
    1. Create DB tables (idempotent — Alembic handles migrations in production)
    2. Ensure storage directories exist
    3. Seed demo users in non-production environments
    4. Log configuration summary

    Shutdown:
    1. Flush logs
    """
    logger.info("=" * 60)
    logger.info("GradeOps v%s starting (%s)", settings.APP_VERSION, settings.ENVIRONMENT)

    # 1. Database tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables verified")

    # 2. Storage directories
    for subdir in ["", "exams"]:
        (STORAGE_DIR / subdir).mkdir(parents=True, exist_ok=True)
    logger.info("Storage directories ready at: %s", STORAGE_DIR.absolute())

    # 3. Seed demo users (non-production only)
    if settings.ENVIRONMENT != "production":
        _seed_users()

    # 4. Config summary
    logger.info("LLM provider: %s | OCR model: %s", settings.LLM_PROVIDER, settings.OCR_MODEL)
    logger.info("CORS origins: %s", settings.CORS_ORIGINS)
    logger.info("Ready to accept requests")
    logger.info("=" * 60)

    yield

    logger.info("GradeOps shutting down cleanly")


def _seed_users() -> None:
    """Seed demo admin + TA accounts if they don't exist."""
    from backend.core.security import hash_password

    db = SessionLocal()
    try:
        seeded = []
        for email, password, role in [
            (settings.SEED_ADMIN_EMAIL, settings.SEED_ADMIN_PASSWORD, "instructor"),
            (settings.SEED_TA_EMAIL, settings.SEED_TA_PASSWORD, "ta"),
        ]:
            if not db.query(models.User).filter(models.User.email == email).first():
                db.add(models.User(
                    email=email,
                    password_hash=hash_password(password),
                    role=role,
                    full_name="Admin" if role == "instructor" else "Teaching Assistant",
                ))
                seeded.append(email)
        if seeded:
            db.commit()
            logger.info("Seeded demo accounts: %s", seeded)
    except Exception as e:
        logger.warning("Seed users failed (non-fatal): %s", e)
        db.rollback()
    finally:
        db.close()


# ── App factory ───────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    description="AI-assisted handwritten exam evaluation — Human-in-the-Loop grading platform.",
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
    lifespan=lifespan,
)

# ── Middleware (order matters — outermost runs first) ─────────────────────────

app.add_middleware(ErrorHandlerMiddleware)  # 1. Catch all exceptions
app.add_middleware(RequestIDMiddleware)     # 2. Attach correlation ID

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID", "X-Response-Time"],
)

# ── Routes ────────────────────────────────────────────────────────────────────

app.include_router(api_router, prefix="/api/v1")
app.include_router(api_router, prefix="/api")  # compatibility alias

# Storage files (answer images, PDFs) — served with basic path isolation
if STORAGE_DIR.exists():
    app.mount("/storage", StaticFiles(directory=str(STORAGE_DIR)), name="storage")


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/health", tags=["ops"], include_in_schema=False)
def health_check():
    """
    Health check for load balancers and monitoring (Kubernetes liveness probe).

    Returns 200 if the app is up and can reach the database.
    """
    from backend.db.schemas import HealthResponse

    # Quick DB connectivity check
    db_status = "ok"
    try:
        db = SessionLocal()
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
        db.close()
    except Exception as e:
        db_status = f"error: {e}"

    return HealthResponse(
        status="ok" if db_status == "ok" else "degraded",
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        database=db_status,
        uptime_seconds=round(time.time() - _startup_time, 1),
    )


# ── SPA fallback (serve React app) ───────────────────────────────────────────

if FRONTEND_BUILD.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_BUILD / "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        """Catch-all: serve React SPA for any non-API path."""
        # Don't catch API or storage paths
        if full_path.startswith("api/") or full_path.startswith("storage/"):
            return JSONResponse(status_code=404, content={"error": "NOT_FOUND", "message": "Path not found."})
        return FileResponse(str(FRONTEND_BUILD / "index.html"))
else:
    @app.get("/", include_in_schema=False)
    def root():
        return {
            "message": "GradeOps API is online",
            "version": settings.APP_VERSION,
            "docs": "/docs",
            "health": "/health",
        }
