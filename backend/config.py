"""
Centralized configuration via pydantic-settings.

All environment variables are validated at startup.
Missing critical values cause immediate, clear failures
instead of silent runtime errors deep in the stack.
"""
import os
import secrets
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings
from pydantic import field_validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ── App ──────────────────────────────────────────────────────────────
    APP_NAME: str = "GradeOps"
    APP_VERSION: str = "2.1.0"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # ── Security ─────────────────────────────────────────────────────────
    SECRET_KEY: str = secrets.token_urlsafe(64)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours

    # ── Database ─────────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./gradeops.db"
    DATABASE_ECHO: bool = False

    # ── CORS ─────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:3000",
    ]

    # ── Storage ──────────────────────────────────────────────────────────
    STORAGE_DIR: str = "storage"
    MAX_UPLOAD_SIZE_MB: int = 100

    # ── AI / LLM ─────────────────────────────────────────────────────────
    GOOGLE_API_KEY: str = ""
    LLM_PROVIDER: Literal["ollama", "openai", "gemini"] = "ollama"
    OLLAMA_MODEL: str = "llama3.2"
    OCR_MODEL: Literal["qwen2-vl", "trocr", "gemini"] = "gemini"

    # ── Background Tasks ─────────────────────────────────────────────────
    TASK_MAX_RETRIES: int = 3
    TASK_RETRY_DELAY_SECONDS: int = 5
    GRADING_CONCURRENCY: int = 4  # Parallel LLM calls

    # ── Rate Limiting ────────────────────────────────────────────────────
    RATE_LIMIT_LOGIN_PER_MINUTE: int = 10
    RATE_LIMIT_UPLOAD_PER_MINUTE: int = 5

    # ── Seed Data ────────────────────────────────────────────────────────
    SEED_ADMIN_EMAIL: str = "admin@gradeops.com"
    SEED_ADMIN_PASSWORD: str = "admin123"
    SEED_TA_EMAIL: str = "ta@gradeops.com"
    SEED_TA_PASSWORD: str = "ta123"

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str, info) -> str:
        env = info.data.get("ENVIRONMENT", "development")
        if env == "production" and (len(v) < 32 or v == secrets.token_urlsafe(64)):
            raise ValueError(
                "SECRET_KEY must be explicitly set to a strong value in production. "
                "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
            )
        return v

    @field_validator("GOOGLE_API_KEY")
    @classmethod
    def validate_google_key(cls, v: str, info) -> str:
        ocr = info.data.get("OCR_MODEL", "gemini")
        llm = info.data.get("LLM_PROVIDER", "ollama")
        if (ocr == "gemini" or llm == "gemini") and not v:
            import logging
            logging.getLogger(__name__).warning(
                "GOOGLE_API_KEY not set — Gemini OCR/grading will be unavailable."
            )
        return v

    @property
    def storage_path(self) -> Path:
        p = Path(self.STORAGE_DIR)
        p.mkdir(exist_ok=True)
        return p

    @property
    def is_sqlite(self) -> bool:
        return "sqlite" in self.DATABASE_URL

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton — parsed once at startup."""
    return Settings()
