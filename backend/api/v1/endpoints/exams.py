import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, status
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.db import models
from backend.db.schemas import ExamOut, AnswerOut
from backend.core.security import require_role
from backend.services.rubric_service import validate_rubric
from backend.services.pdf_processor import split_bulk_pdf, rasterize_pdf_to_pngs

logger = logging.getLogger(__name__)
router = APIRouter(tags=["exams"])

STORAGE_DIR = Path("storage")

@router.post("/upload", response_model=ExamOut, status_code=status.HTTP_201_CREATED)
async def upload_exam_package(
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    rubric_json: str = Form(...),
    pages_per_student: int = Form(...),
    bulk_pdf: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("instructor")),
):
    # 1. Validate Rubric
    try:
        rubric_data = json.loads(rubric_json)
    except json.JSONDecodeError:
        raise HTTPException(400, detail="Invalid JSON format for rubric")
    
    is_valid, error_msg = validate_rubric(rubric_data)
    if not is_valid:
        raise HTTPException(400, detail=f"Rubric validation failed: {error_msg}")

    # 2. Create Exam
    exam = models.User(id=current_user.id) # Dummy to check relation, wait
    exam = models.Exam(
        title=title,
        owner_id=current_user.id,
        rubric_json=rubric_data,
        status="processing"
    )
    db.add(exam)
    db.flush() # Get exam.id

    # 3. Create Questions from Rubric
    for q_meta in rubric_data["questions"]:
        question = models.Question(
            exam_id=exam.id,
            number=q_meta["number"],
            max_marks=q_meta["max_marks"]
        )
        db.add(question)
    
    # 4. Save Bulk PDF
    exam_dir = STORAGE_DIR / "exams" / str(exam.id)
    exam_dir.mkdir(parents=True, exist_ok=True)
    bulk_path = exam_dir / "bulk_upload.pdf"
    
    with open(bulk_path, "wb") as f:
        shutil.copyfileobj(bulk_pdf.file, f)
    
    db.commit()
    db.refresh(exam)

    # 5. Run Background Processing (Split & Rasterize)
    background_tasks.add_task(
        _process_bulk_upload,
        exam.id,
        str(bulk_path),
        pages_per_student
    )

    return exam

@router.get("", response_model=List[ExamOut])
def list_exams(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("instructor", "ta")),
):
    if current_user.role == "instructor":
        return db.query(models.Exam).filter(models.Exam.owner_id == current_user.id).all()
    return db.query(models.Exam).all()

@router.get("/{exam_id}", response_model=ExamOut)
def get_exam(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("instructor", "ta")),
):
    exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(404, detail="Exam not found")
    return exam


@router.get("/{exam_id}/answers", response_model=List[AnswerOut])
def list_exam_answers(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("instructor", "ta")),
):
    # Join with Submission to filter by exam_id
    answers = db.query(models.Answer).join(models.Submission).filter(
        models.Submission.exam_id == exam_id
    ).all()
    return answers


@router.post("/{exam_id}/extract", status_code=status.HTTP_202_ACCEPTED)
def trigger_extraction(
    exam_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("instructor")),
):
    exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(404, "Exam not found")
    
    exam.status = "extracting"
    db.commit()
    
    background_tasks.add_task(_run_vlm_extraction, exam_id)
    return {"message": "VLM extraction started"}


@router.get("/{exam_id}/extraction-status")
def get_extraction_status(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("instructor", "ta")),
):
    exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(404, "Exam not found")
    
    total = db.query(models.Answer).join(models.Submission).filter(models.Submission.exam_id == exam_id).count()
    completed = db.query(models.Answer).join(models.Submission).filter(
        models.Submission.exam_id == exam_id,
        models.Answer.extraction_status == "completed"
    ).count()
    
    return {
        "status": exam.status,
        "total_answers": total,
        "completed_answers": completed,
        "percent": round((completed / total) * 100) if total > 0 else 0
    }


@router.post("/{exam_id}/grade", status_code=status.HTTP_202_ACCEPTED)
def trigger_grading(
    exam_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("instructor")),
):
    exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(404, "Exam not found")
    
    exam.status = "grading"
    db.commit()
    
    background_tasks.add_task(_run_grading_agent, exam_id)
    return {"message": "Grading pipeline started"}


@router.get("/{exam_id}/analytics")
def get_exam_analytics(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("instructor")),
):
    exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(404, "Exam not found")
    
    # Get all final scores
    grades = db.query(models.Grade).join(models.Answer).join(models.Submission).filter(
        models.Submission.exam_id == exam_id
    ).all()
    
    scores = [g.final_score for g in grades if g.final_score is not None]
    
    avg_score = sum(scores) / len(scores) if scores else 0
    
    # Simple histogram
    distribution = {}
    for s in scores:
        bucket = int(s)
        distribution[bucket] = distribution.get(bucket, 0) + 1

    # Time savings estimate (heuristic)
    # Manual: 4 mins per answer
    # AI: ~1 min per answer (review time)
    time_saved_hours = (len(scores) * 3) / 60
    
    return {
        "average_score": round(avg_score, 2),
        "total_graded": len(scores),
        "distribution": distribution,
        "time_saved_hours": round(time_saved_hours, 1)
    }
def review_answer(
    answer_id: int,
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("ta", "instructor")),
):
    ans = db.query(models.Answer).filter(models.Answer.id == answer_id).first()
    if not ans:
        raise HTTPException(404, "Answer not found")
    
    grade = ans.grade
    if not grade:
        grade = models.Grade(answer_id=answer_id)
        db.add(grade)
    
    grade.final_score = payload.get("final_score")
    grade.ta_notes = payload.get("ta_notes")
    grade.status = payload.get("status", "reviewed")
    grade.ta_id = current_user.id
    grade.reviewed_at = datetime.now()
    
    db.commit()
    db.refresh(ans)
    return ans


# ── Background Processors ─────────────────────────────────────────────────────

def _run_grading_agent(exam_id: int):
    """Run the GradingAgent for all completed extractions."""
    from backend.db.session import SessionLocal
    from backend.services.grading_agent import GradingAgent
    db = SessionLocal()
    try:
        answers = db.query(models.Answer).join(models.Submission).filter(
            models.Submission.exam_id == exam_id,
            models.Answer.extraction_status == "completed"
        ).all()

        agent = GradingAgent(db)
        logger.info(f"Starting Grading Agent for {len(answers)} answers in Exam {exam_id}")

        for ans in answers:
            agent.run_pipeline(ans.id)
            logger.info(f"Answer {ans.id} graded.")

        # Run Plagiarism Check
        from backend.services.plagiarism import run_plagiarism_check
        run_plagiarism_check(db, exam_id)

        exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
        if exam:
            exam.status = "complete"
            db.commit()

    except Exception as e:
        logger.error(f"Grading agent failed: {e}")
    finally:
        db.close()

def _run_vlm_extraction(exam_id: int):
    """Iterate through all pending answers and run Gemini VLM extraction."""
    from backend.db.session import SessionLocal
    from backend.services.gemini_service import gemini
    db = SessionLocal()
    try:
        answers = db.query(models.Answer).join(models.Submission).filter(
            models.Submission.exam_id == exam_id,
            models.Answer.extraction_status == "pending"
        ).all()

        logger.info(f"Starting VLM extraction for {len(answers)} answers in Exam {exam_id}")

        for ans in answers:
            # Get question context from rubric
            exam = ans.submission.exam
            rubric = exam.rubric_json or {}
            q_meta = next((q for q in rubric.get("questions", []) if q["number"] == ans.question.number), {})
            question_text = q_meta.get("answer_key", "General exam answer") # Or combine with criteria

            # Run Gemini
            result = gemini.extract_answer(ans.crop_path, question_text)
            
            ans.transcribed_text = result["transcription"]
            ans.ocr_confidence = 0.9 if result["legibility"] == "high" else 0.6
            ans.extraction_status = "completed"
            db.commit()
            logger.info(f"Answer {ans.id} extracted.")

        exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
        if exam:
            exam.status = "ready_for_grading"
            db.commit()

    except Exception as e:
        logger.error(f"VLM extraction failed: {e}")
    finally:
        db.close()


def _process_bulk_upload(exam_id: int, bulk_path: str, pages_per_student: int):
    """Split bulk PDF, create submissions/students, and rasterize pages."""
    from backend.db.session import SessionLocal
    db = SessionLocal()
    try:
        exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
        if not exam:
            return

        # 1. Split PDF
        pdf_paths = split_bulk_pdf(bulk_path, pages_per_student, exam_id)
        logger.info(f"Split bulk PDF into {len(pdf_paths)} submissions")

        questions = db.query(models.Question).filter(models.Question.exam_id == exam_id).order_by(models.Question.number).all()

        for i, pdf_path in enumerate(pdf_paths):
            # 2. Create Student (Dummy roll no for now)
            roll_no = f"S-{1000 + i}"
            student = models.Student(exam_id=exam_id, roll_no=roll_no, name=f"Student {i+1}")
            db.add(student)
            db.flush()

            # 3. Create Submission
            submission = models.Submission(
                exam_id=exam_id,
                student_id=student.id,
                pdf_path=pdf_path,
                num_pages=pages_per_student
            )
            db.add(submission)
            db.flush()

            # 4. Rasterize to PNGs
            sub_image_dir = STORAGE_DIR / "exams" / str(exam_id) / "submissions" / str(submission.id) / "pages"
            image_paths = rasterize_pdf_to_pngs(pdf_path, str(sub_image_dir))

            # 5. Create Answers (One question per page assumption)
            for j, q in enumerate(questions):
                # If we have more questions than pages, some won't have images
                # If we have more pages than questions, extra pages are ignored for now
                img_path = image_paths[j] if j < len(image_paths) else None
                
                answer = models.Answer(
                    submission_id=submission.id,
                    question_id=q.id,
                    crop_path=img_path,
                    extraction_status="pending"
                )
                db.add(answer)

        exam.status = "ready" # Ready for VLM extraction pass
        db.commit()
        logger.info(f"Processing complete for Exam {exam_id}")

    except Exception as e:
        logger.error(f"Error processing bulk upload: {e}")
        db.rollback()
    finally:
        db.close()
