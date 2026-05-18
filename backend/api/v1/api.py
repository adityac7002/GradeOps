"""
API v1 router — single source of truth.

All endpoint modules registered here with proper prefixes.
Dead grading.py and rubrics.py are no longer imported.
"""
from fastapi import APIRouter
from backend.api.v1.endpoints import auth, exams, plagiarism

api_router = APIRouter()

api_router.include_router(auth.router,       prefix="/auth",  tags=["auth"])
api_router.include_router(exams.router,      prefix="/exams", tags=["exams"])
api_router.include_router(plagiarism.router, prefix="/exams", tags=["plagiarism"])
