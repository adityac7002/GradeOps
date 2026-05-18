"""
Plagiarism endpoints — v1.

Properly wired router with correct model references.
Replaces the dead plagiarism.py that referenced non-existent models.
"""
import logging
from fastapi import APIRouter, Depends, BackgroundTasks, status
from sqlalchemy.orm import Session

from backend.core.security import get_current_user, require_role
from backend.db import models
from backend.db.repositories import ExamRepository
from backend.db.session import get_db

logger = logging.getLogger(__name__)
router = APIRouter(tags=["plagiarism"])


@router.post("/{exam_id}/plagiarism/run", status_code=status.HTTP_202_ACCEPTED)
def run_plagiarism(
    exam_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("instructor", "ta")),
):
    """Enqueue plagiarism detection for an exam."""
    ExamRepository(db).get_by_id_or_raise(exam_id)

    def _run():
        from backend.db.session import SessionLocal
        from backend.services.plagiarism import run_plagiarism_check
        inner_db = SessionLocal()
        try:
            run_plagiarism_check(inner_db, exam_id)
        finally:
            inner_db.close()

    background_tasks.add_task(_run)
    return {"message": "Plagiarism detection queued", "exam_id": exam_id}


@router.get("/{exam_id}/plagiarism")
def get_plagiarism_report(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("instructor", "ta")),
):
    """Fetch existing plagiarism flags for an exam."""
    ExamRepository(db).get_by_id_or_raise(exam_id)

    flags = (
        db.query(models.PlagiarismFlag)
        .filter(models.PlagiarismFlag.exam_id == exam_id)
        .order_by(models.PlagiarismFlag.similarity.desc())
        .all()
    )

    return [
        {
            "id": f.id,
            "question_id": f.question_id,
            "answer_ids": f.answer_ids_json,
            "similarity": round(f.similarity, 3),
            "cluster_id": f.cluster_id,
            "created_at": f.created_at.isoformat(),
        }
        for f in flags
    ]
