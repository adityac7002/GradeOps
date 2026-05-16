import logging
import traceback
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend import models
from backend.db.schemas import AnswerOut, TAReview, DashboardStats
from backend.core.security import get_current_user, require_role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["grading"])


# ── Trigger grading pipeline ───────────────────────────────────────────────────

@router.post("/exams/{exam_id}/grade", status_code=202)
def trigger_grading(
    exam_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("instructor")),
):
    exam = db.query(models.Exam).filter(
        models.Exam.id == exam_id,
        models.Exam.owner_id == current_user.id,
    ).first()
    if not exam:
        raise HTTPException(404, "Exam not found")
    if not exam.questions:
        raise HTTPException(400, "Set the rubric before grading")
    # Allow re-trigger if stuck (processing) — resets state

    exam.status = "processing"
    db.commit()

    background_tasks.add_task(_run_grading_pipeline, exam_id)
    return {"message": "Grading pipeline started", "exam_id": exam_id}


def _run_grading_pipeline(exam_id: int):
    """Background task: OCR → AI grade each answer for every paper in the exam."""
    from backend.db.session import SessionLocal
    from backend.services.pdf_processor import extract_answer_images
    from backend.services.ocr import run_ocr
    from backend.services.grader import grade_answer

    db = SessionLocal()
    try:
        exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
        if not exam:
            return

        for paper in exam.papers:
            paper.status = "processing"
            db.commit()

            # Extract one image per question from the PDF
            try:
                images = extract_answer_images(paper.pdf_path, len(exam.questions))
            except Exception:
                logger.error("[PDF] Error processing %s:\n%s", paper.pdf_path, traceback.format_exc())
                paper.status = "graded"  # skip, leave answers empty
                db.commit()
                continue

            for question in exam.questions:
                img_path = images.get(question.number)

                # OCR (best-effort — vision grading doesn't require it)
                ocr_text = ""
                if img_path:
                    try:
                        ocr_text = run_ocr(img_path)
                        logger.info("[OCR] Q%d: %d chars", question.number, len(ocr_text))
                    except Exception:
                        logger.error("[OCR] Error:\n%s", traceback.format_exc())

                # AI grading — always attempt if we have rubric items
                ai_grade, ai_justification = None, None
                if question.rubric_items:
                    try:
                        result = grade_answer(
                            ocr_text=ocr_text,
                            rubric_items=[{
                                "description": ri.description,
                                "points": ri.points,
                                "keywords": ri.keywords or [],
                            } for ri in question.rubric_items],
                            max_points=question.max_points,
                            image_path=img_path,
                            question_prompt=question.prompt,    # from QP extraction
                            given_data=question.given_data,     # from QP extraction
                        )
                        ai_grade = result["grade"]
                        ai_justification = result["justification"]
                        logger.info("[Grader] Q%d: %.1f / %.1f", question.number, ai_grade, question.max_points)
                    except Exception:
                        logger.error("[Grader] Error:\n%s", traceback.format_exc())


                # Delete any existing answer for this paper+question before re-inserting
                db.query(models.Answer).filter(
                    models.Answer.paper_id == paper.id,
                    models.Answer.question_id == question.id,
                ).delete()

                answer = models.Answer(
                    paper_id=paper.id,
                    question_id=question.id,
                    image_path=img_path,
                    ocr_text=ocr_text,
                    ai_grade=ai_grade,
                    ai_justification=ai_justification,
                    status="graded" if ai_grade is not None else "ocr_done",
                )
                db.add(answer)

            paper.status = "graded"
            db.commit()

        exam.status = "graded"
        db.commit()
    except Exception:
        logger.error("[Pipeline] Fatal error for exam %d:\n%s", exam_id, traceback.format_exc())
        try:
            exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
            if exam:
                exam.status = "error"
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


# ── Single answer ──────────────────────────────────────────────────────────────

@router.get("/answers/{answer_id}", response_model=AnswerOut)
def get_answer(
    answer_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    answer = db.query(models.Answer).filter(models.Answer.id == answer_id).first()
    if not answer:
        raise HTTPException(404, "Answer not found")
    return _enrich_answer(answer)


@router.patch("/answers/{answer_id}/review", response_model=AnswerOut)
def review_answer(
    answer_id: int,
    payload: TAReview,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("ta", "instructor")),
):
    answer = db.query(models.Answer).filter(models.Answer.id == answer_id).first()
    if not answer:
        raise HTTPException(404, "Answer not found")

    if payload.action == "approve":
        answer.final_grade = answer.ai_grade
        answer.status = "approved"
    else:  # override
        if payload.ta_grade is None:
            raise HTTPException(400, "ta_grade required for override")
        answer.ta_grade = payload.ta_grade
        answer.ta_override_reason = payload.ta_override_reason
        answer.final_grade = payload.ta_grade
        answer.status = "overridden"

    answer.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(answer)
    return _enrich_answer(answer)


# ── Dashboard feed ─────────────────────────────────────────────────────────────

@router.get("/exams/{exam_id}/dashboard")
def dashboard_feed(
    exam_id: int,
    question_id: Optional[int] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    q = (
        db.query(models.Answer)
        .join(models.StudentPaper)
        .filter(models.StudentPaper.exam_id == exam_id)
    )
    if question_id:
        q = q.filter(models.Answer.question_id == question_id)
    if status:
        q = q.filter(models.Answer.status == status)

    total = q.count()
    answers = q.offset(skip).limit(limit).all()
    return {"total": total, "items": [_enrich_answer(a) for a in answers]}


@router.get("/exams/{exam_id}/stats", response_model=DashboardStats)
def exam_stats(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    answers = (
        db.query(models.Answer)
        .join(models.StudentPaper)
        .filter(models.StudentPaper.exam_id == exam_id)
        .all()
    )
    statuses = [a.status for a in answers]
    return DashboardStats(
        total_answers=len(answers),
        pending=statuses.count("pending"),
        approved=statuses.count("approved"),
        overridden=statuses.count("overridden"),
        graded=statuses.count("graded") + statuses.count("ocr_done"),
        plagiarism_flagged=sum(1 for a in answers if a.plagiarism_flag),
    )


# ── Helpers ────────────────────────────────────────────────────────────────────

def _enrich_answer(answer: models.Answer) -> AnswerOut:
    from backend.db.schemas import RubricItemOut
    paper = answer.paper
    question = answer.question
    rubric_items = [
        RubricItemOut(
            id=ri.id,
            question_id=ri.question_id,
            description=ri.description,
            points=ri.points,
            keywords=ri.keywords or [],
        )
        for ri in question.rubric_items
    ]
    return AnswerOut(
        id=answer.id,
        paper_id=answer.paper_id,
        question_id=answer.question_id,
        image_path=answer.image_path,
        ocr_text=answer.ocr_text,
        ai_grade=answer.ai_grade,
        ai_justification=answer.ai_justification,
        ta_grade=answer.ta_grade,
        ta_override_reason=answer.ta_override_reason,
        final_grade=answer.final_grade,
        plagiarism_flag=answer.plagiarism_flag,
        plagiarism_score=answer.plagiarism_score,
        status=answer.status,
        reviewed_at=answer.reviewed_at,
        student_id=paper.student_id,
        student_name=paper.student_name,
        question_number=question.number,
        max_points=question.max_points,
        rubric_items=rubric_items,
    )
