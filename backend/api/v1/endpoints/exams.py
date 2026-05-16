import os
import uuid
import asyncio
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, BackgroundTasks
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend import models
from backend.db.schemas import ExamCreate, ExamOut, ExamSummary, QuestionPaperUploadOut
from backend.core.security import get_current_user, require_role

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

router = APIRouter(prefix="/api/exams", tags=["exams"])


@router.post("", response_model=ExamOut, status_code=201)
async def create_exam(
    title: str = Form(...),
    course: str = Form(...),
    student_id: str = Form(...),
    student_name: Optional[str] = Form(None),
    pdf: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("instructor")),
):
    """Upload a single student exam PDF and register it under an exam."""
    # Create exam if it doesn't exist (simple: one exam per upload batch)
    exam = models.Exam(title=title, course=course, owner_id=current_user.id)
    db.add(exam)
    db.flush()

    # Save PDF
    safe_name = f"{uuid.uuid4()}.pdf"
    pdf_path = UPLOAD_DIR / str(exam.id) / safe_name
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    content = await pdf.read()
    pdf_path.write_bytes(content)

    paper = models.StudentPaper(
        exam_id=exam.id,
        student_id=student_id,
        student_name=student_name,
        pdf_path=str(pdf_path),
    )
    db.add(paper)
    db.commit()
    db.refresh(exam)
    return exam


@router.post("/batch", response_model=ExamOut, status_code=201)
async def create_exam_batch(
    title: str = Form(...),
    course: str = Form(...),
    pdfs: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("instructor")),
):
    """Upload multiple student exam PDFs for one exam in a single request."""
    exam = models.Exam(title=title, course=course, owner_id=current_user.id)
    db.add(exam)
    db.flush()

    for i, pdf in enumerate(pdfs):
        safe_name = f"{uuid.uuid4()}.pdf"
        pdf_path = UPLOAD_DIR / str(exam.id) / safe_name
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        content = await pdf.read()
        pdf_path.write_bytes(content)

        # Derive student_id from filename stem
        stem = Path(pdf.filename or f"student_{i+1}").stem
        paper = models.StudentPaper(
            exam_id=exam.id,
            student_id=stem,
            student_name=None,
            pdf_path=str(pdf_path),
        )
        db.add(paper)

    db.commit()
    db.refresh(exam)
    return exam


@router.get("", response_model=list[ExamSummary])
def list_exams(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if current_user.role == "instructor":
        exams = db.query(models.Exam).filter(models.Exam.owner_id == current_user.id).all()
    else:
        exams = db.query(models.Exam).all()

    result = []
    for exam in exams:
        paper_count = len(exam.papers)
        graded_count = sum(1 for p in exam.papers if p.status == "graded")
        result.append(ExamSummary(
            id=exam.id,
            title=exam.title,
            course=exam.course,
            status=exam.status,
            created_at=exam.created_at,
            paper_count=paper_count,
            graded_count=graded_count,
        ))
    return result


@router.get("/{exam_id}", response_model=ExamOut)
def get_exam(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    return exam


@router.delete("/{exam_id}", status_code=204)
def delete_exam(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("instructor")),
):
    exam = db.query(models.Exam).filter(models.Exam.id == exam_id, models.Exam.owner_id == current_user.id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    db.delete(exam)
    db.commit()


@router.post("/{exam_id}/question-paper", response_model=QuestionPaperUploadOut, status_code=202)
async def upload_question_paper(
    exam_id: int,
    background_tasks: BackgroundTasks,
    qp_pdf: UploadFile = File(..., description="Question paper PDF"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("instructor")),
):
    """
    Upload the question paper PDF for an exam.
    GradeOps will automatically:
    - Extract all questions and their marks
    - Generate a rubric scaffold for each question
    - Pre-populate the rubric editor in the UI
    """
    exam = db.query(models.Exam).filter(
        models.Exam.id == exam_id,
        models.Exam.owner_id == current_user.id,
    ).first()
    if not exam:
        raise HTTPException(404, "Exam not found")

    # Save the question paper PDF
    qp_dir = UPLOAD_DIR / str(exam_id) / "question_paper"
    qp_dir.mkdir(parents=True, exist_ok=True)
    qp_path = qp_dir / "question_paper.pdf"
    content = await qp_pdf.read()
    qp_path.write_bytes(content)

    exam.question_paper_path = str(qp_path)
    exam.qp_extracted = False
    db.commit()

    # Run extraction synchronously (returns quickly for small QPs,
    # runs in thread for larger ones via background_tasks)
    background_tasks.add_task(_run_qp_extraction, exam_id, str(qp_path))

    return QuestionPaperUploadOut(
        exam_id=exam_id,
        question_paper_path=str(qp_path),
        extracted_questions=[],   # populated once background task finishes
        message="Question paper uploaded. Extraction running in background — poll GET /api/exams/{id} to see results.",
    )


@router.get("/{exam_id}/question-paper/status")
def qp_extraction_status(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Poll this endpoint to check if QP extraction has completed."""
    exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(404, "Exam not found")
    questions = [
        {
            "number": q.number,
            "prompt": q.prompt,
            "given_data": q.given_data,
            "max_points": q.max_points,
            "rubric_items": [
                {"description": ri.description, "points": ri.points, "keywords": ri.keywords or []}
                for ri in q.rubric_items
            ],
        }
        for q in sorted(exam.questions, key=lambda x: x.number)
    ]
    return {
        "qp_extracted": exam.qp_extracted,
        "question_paper_path": exam.question_paper_path,
        "questions": questions,
    }


# ── Background QP extraction task ─────────────────────────────────────────────

def _run_qp_extraction(exam_id: int, qp_path: str) -> None:
    """Background task: extract questions from QP PDF and upsert into DB."""
    import traceback
    import logging
    from backend.db.session import SessionLocal
    from backend.services.question_extractor import extract_questions_from_paper

    log = logging.getLogger(__name__)
    db = SessionLocal()
    try:
        log.info("[QP] Starting extraction for exam %d", exam_id)
        extracted = extract_questions_from_paper(qp_path)

        exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
        if not exam:
            return

        for q_data in extracted:
            # Upsert question by number
            question = db.query(models.Question).filter(
                models.Question.exam_id == exam_id,
                models.Question.number == q_data["number"],
            ).first()

            if question is None:
                question = models.Question(
                    exam_id=exam_id,
                    number=q_data["number"],
                )
                db.add(question)
                db.flush()

            question.prompt = q_data["prompt"]
            question.given_data = q_data.get("given_data")
            question.max_points = q_data["max_points"]

            # Replace existing rubric items with AI-generated ones
            db.query(models.RubricItem).filter(
                models.RubricItem.question_id == question.id
            ).delete()

            for ri in q_data.get("rubric_items", []):
                db.add(models.RubricItem(
                    question_id=question.id,
                    description=ri["description"],
                    points=ri["points"],
                    keywords=ri.get("keywords", []),
                ))

        exam.qp_extracted = True
        db.commit()
        log.info("[QP] Extraction complete for exam %d — %d questions", exam_id, len(extracted))

    except Exception:
        log.error("[QP] Extraction failed for exam %d:\n%s", exam_id, traceback.format_exc())
        db.rollback()
    finally:
        db.close()
