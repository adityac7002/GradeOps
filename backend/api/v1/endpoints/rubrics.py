from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend import models
from backend.db.schemas import QuestionCreate, QuestionOut
from backend.core.security import require_role, get_current_user

router = APIRouter(prefix="/api/exams", tags=["rubrics"])


@router.post("/{exam_id}/rubric", response_model=list[QuestionOut], status_code=201)
def set_rubric(
    exam_id: int,
    questions: list[QuestionCreate],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("instructor")),
):
    """Replace the full rubric for an exam (idempotent)."""
    exam = db.query(models.Exam).filter(
        models.Exam.id == exam_id,
        models.Exam.owner_id == current_user.id,
    ).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    # Clear existing questions
    for q in exam.questions:
        db.delete(q)
    db.flush()

    result = []
    for q_data in questions:
        q = models.Question(
            exam_id=exam_id,
            number=q_data.number,
            prompt=q_data.prompt,
            given_data=q_data.given_data,
            max_points=q_data.max_points,
        )
        db.add(q)
        db.flush()

        for ri in q_data.rubric_items:
            item = models.RubricItem(
                question_id=q.id,
                description=ri.description,
                points=ri.points,
                keywords=ri.keywords,
            )
            db.add(item)

        db.refresh(q)
        result.append(q)

    db.commit()
    for q in result:
        db.refresh(q)
    return result


@router.get("/{exam_id}/rubric", response_model=list[QuestionOut])
def get_rubric(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    return exam.questions
