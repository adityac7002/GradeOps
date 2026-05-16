from fastapi import APIRouter
from backend.api.v1.endpoints import auth, exams, rubrics, grading, plagiarism

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(exams.router, prefix="/exams", tags=["exams"])
api_router.include_router(rubrics.router, prefix="/exams", tags=["rubrics"])
api_router.include_router(grading.router, prefix="/exams", tags=["grading"])
api_router.include_router(plagiarism.router, prefix="/exams", tags=["plagiarism"])
