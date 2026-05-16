from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend import models
from backend.db.schemas import PlagiarismPair
from backend.core.security import get_current_user

router = APIRouter(prefix="/api/exams", tags=["plagiarism"])


@router.post("/{exam_id}/plagiarism/run", status_code=202)
def run_plagiarism(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    from fastapi import BackgroundTasks
    from backend.services.plagiarism import detect_plagiarism
    detect_plagiarism(exam_id, db)
    return {"message": "Plagiarism detection complete"}


@router.get("/{exam_id}/plagiarism", response_model=list[PlagiarismPair])
def get_plagiarism_report(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(404, "Exam not found")

    flagged_answers = (
        db.query(models.Answer)
        .join(models.StudentPaper)
        .filter(
            models.StudentPaper.exam_id == exam_id,
            models.Answer.plagiarism_flag == True,
        )
        .all()
    )

    # Group by question and find pairs
    from itertools import combinations
    by_question: dict[int, list[models.Answer]] = {}
    for a in flagged_answers:
        by_question.setdefault(a.question_id, []).append(a)

    pairs: list[PlagiarismPair] = []
    for q_id, answers in by_question.items():
        for a, b in combinations(answers, 2):
            score = max(a.plagiarism_score or 0, b.plagiarism_score or 0)
            if score >= 0.75:
                pairs.append(PlagiarismPair(
                    answer_id_a=a.id,
                    answer_id_b=b.id,
                    student_id_a=a.paper.student_id,
                    student_id_b=b.paper.student_id,
                    question_number=a.question.number,
                    similarity_score=round(score, 3),
                    ocr_text_a=a.ocr_text,
                    ocr_text_b=b.ocr_text,
                ))
    return pairs
