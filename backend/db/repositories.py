"""
Repository layer for GradeOps.

All database queries live here — no raw ORM queries in endpoints.
Each repository owns one model and exposes typed, named query methods.

Benefits:
- Endpoints stay thin (auth + validation only)
- Query logic is testable in isolation
- Easy to swap storage backend
- N+1 issues fixed with explicit joinedload()
"""
import math
from typing import Optional
from datetime import datetime, timezone

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, func

from backend.db import models
from backend.db.schemas import PaginationParams
from backend.exceptions import NotFoundError


# ── Base repository ──────────────────────────────────────────────────────────

class BaseRepository:
    def __init__(self, db: Session):
        self.db = db


# ── User ─────────────────────────────────────────────────────────────────────

class UserRepository(BaseRepository):

    def get_by_id(self, user_id: int) -> Optional[models.User]:
        return self.db.get(models.User, user_id)

    def get_by_email(self, email: str) -> Optional[models.User]:
        return (
            self.db.query(models.User)
            .filter(models.User.email == email, models.User.is_active == True)
            .first()
        )

    def create(self, email: str, password_hash: str, role: str, full_name: Optional[str] = None) -> models.User:
        user = models.User(
            email=email,
            password_hash=password_hash,
            role=role,
            full_name=full_name,
        )
        self.db.add(user)
        self.db.flush()
        return user


# ── Exam ─────────────────────────────────────────────────────────────────────

class ExamRepository(BaseRepository):

    def get_by_id(self, exam_id: int) -> Optional[models.Exam]:
        return self.db.get(models.Exam, exam_id)

    def get_by_id_or_raise(self, exam_id: int) -> models.Exam:
        exam = self.get_by_id(exam_id)
        if not exam:
            raise NotFoundError("Exam", exam_id)
        return exam

    def get_by_owner(self, owner_id: int, status: Optional[str] = None) -> list[models.Exam]:
        q = self.db.query(models.Exam).filter(models.Exam.owner_id == owner_id)
        if status:
            q = q.filter(models.Exam.status == status)
        return q.order_by(models.Exam.created_at.desc()).all()

    def get_all(self, pagination: PaginationParams) -> tuple[list[models.Exam], int]:
        base_q = self.db.query(models.Exam)
        total = base_q.count()
        items = (
            base_q
            .order_by(models.Exam.created_at.desc())
            .offset(pagination.offset)
            .limit(pagination.page_size)
            .all()
        )
        return items, total

    def create(self, title: str, owner_id: int, rubric_json: Optional[dict] = None,
               course_code: Optional[str] = None) -> models.Exam:
        exam = models.Exam(
            title=title,
            owner_id=owner_id,
            rubric_json=rubric_json,
            course_code=course_code,
            status="draft",
        )
        self.db.add(exam)
        self.db.flush()
        return exam

    def update_status(self, exam: models.Exam, status: str) -> models.Exam:
        exam.status = status
        self.db.flush()
        return exam

    def count_answers(self, exam_id: int) -> tuple[int, int, int]:
        """Returns (total, completed, failed) answer counts."""
        rows = (
            self.db.query(models.Answer.extraction_status, func.count(models.Answer.id))
            .join(models.Submission)
            .filter(models.Submission.exam_id == exam_id)
            .group_by(models.Answer.extraction_status)
            .all()
        )
        counts = {status: cnt for status, cnt in rows}
        total = sum(counts.values())
        return total, counts.get("completed", 0), counts.get("failed", 0)


# ── Answer ───────────────────────────────────────────────────────────────────

class AnswerRepository(BaseRepository):

    def get_by_id(self, answer_id: int) -> Optional[models.Answer]:
        return (
            self.db.query(models.Answer)
            .options(
                joinedload(models.Answer.grade),
                joinedload(models.Answer.question),
                joinedload(models.Answer.submission).joinedload(models.Submission.student),
            )
            .filter(models.Answer.id == answer_id)
            .first()
        )

    def get_by_id_or_raise(self, answer_id: int) -> models.Answer:
        answer = self.get_by_id(answer_id)
        if not answer:
            raise NotFoundError("Answer", answer_id)
        return answer

    def list_for_exam(
        self,
        exam_id: int,
        extraction_status: Optional[str] = None,
        grade_status: Optional[str] = None,
        pagination: Optional[PaginationParams] = None,
    ) -> tuple[list[models.Answer], int]:
        q = (
            self.db.query(models.Answer)
            .join(models.Submission)
            .options(
                joinedload(models.Answer.grade),
                joinedload(models.Answer.question),
                joinedload(models.Answer.submission).joinedload(models.Submission.student),
            )
            .filter(models.Submission.exam_id == exam_id)
        )
        if extraction_status:
            q = q.filter(models.Answer.extraction_status == extraction_status)
        if grade_status:
            q = q.join(models.Grade).filter(models.Grade.status == grade_status)

        total = q.count()
        if pagination:
            q = q.offset(pagination.offset).limit(pagination.page_size)

        return q.all(), total

    def pending_extraction(self, exam_id: int) -> list[models.Answer]:
        return (
            self.db.query(models.Answer)
            .join(models.Submission)
            .options(
                joinedload(models.Answer.question),
                joinedload(models.Answer.submission).joinedload(models.Submission.exam),
            )
            .filter(
                models.Submission.exam_id == exam_id,
                models.Answer.extraction_status == "pending",
            )
            .all()
        )

    def pending_grading(self, exam_id: int) -> list[models.Answer]:
        return (
            self.db.query(models.Answer)
            .join(models.Submission)
            .options(
                joinedload(models.Answer.question),
                joinedload(models.Answer.submission).joinedload(models.Submission.exam),
            )
            .filter(
                models.Submission.exam_id == exam_id,
                models.Answer.extraction_status == "completed",
            )
            .outerjoin(models.Grade)
            .filter(
                (models.Grade.id == None) | (models.Grade.status == "pending")
            )
            .all()
        )


# ── Grade ────────────────────────────────────────────────────────────────────

class GradeRepository(BaseRepository):

    def get_for_answer(self, answer_id: int) -> Optional[models.Grade]:
        return (
            self.db.query(models.Grade)
            .filter(models.Grade.answer_id == answer_id)
            .first()
        )

    def upsert(
        self,
        answer_id: int,
        ai_score: float,
        ai_breakdown_json: dict,
        ai_justification: str,
        ai_confidence: float = 0.0,
    ) -> models.Grade:
        grade = self.get_for_answer(answer_id)
        if not grade:
            grade = models.Grade(answer_id=answer_id)
            self.db.add(grade)

        grade.ai_score = ai_score
        grade.ai_breakdown_json = ai_breakdown_json
        grade.ai_justification = ai_justification
        grade.ai_confidence = ai_confidence
        grade.status = "graded"
        grade.final_score = ai_score
        self.db.flush()
        return grade

    def apply_review(
        self,
        grade: models.Grade,
        final_score: float,
        ta_id: int,
        ta_notes: Optional[str],
        status: str = "reviewed",
    ) -> models.Grade:
        grade.final_score = final_score
        grade.ta_id = ta_id
        grade.ta_notes = ta_notes
        grade.status = status
        grade.reviewed_at = datetime.now(timezone.utc)
        self.db.flush()
        return grade

    def analytics(self, exam_id: int) -> list[models.Grade]:
        """Load all grades for an exam in one query with joins."""
        return (
            self.db.query(models.Grade)
            .join(models.Answer)
            .join(models.Submission)
            .filter(models.Submission.exam_id == exam_id)
            .all()
        )


# ── ProcessingTask ────────────────────────────────────────────────────────────

class TaskRepository(BaseRepository):

    def create(self, exam_id: int, task_type: str, total_items: int = 0) -> models.ProcessingTask:
        task = models.ProcessingTask(
            exam_id=exam_id,
            task_type=task_type,
            status="pending",
            total_items=total_items,
        )
        self.db.add(task)
        self.db.flush()
        return task

    def get_latest(self, exam_id: int, task_type: str) -> Optional[models.ProcessingTask]:
        return (
            self.db.query(models.ProcessingTask)
            .filter(
                models.ProcessingTask.exam_id == exam_id,
                models.ProcessingTask.task_type == task_type,
            )
            .order_by(models.ProcessingTask.created_at.desc())
            .first()
        )

    def mark_running(self, task: models.ProcessingTask) -> None:
        task.status = "running"
        self.db.flush()

    def increment_progress(self, task: models.ProcessingTask) -> None:
        task.completed_items += 1
        task.progress = (task.completed_items / task.total_items * 100) if task.total_items > 0 else 0
        self.db.flush()

    def mark_complete(self, task: models.ProcessingTask, message: str = "Completed") -> None:
        task.status = "completed"
        task.progress = 100.0
        task.message = message
        self.db.flush()

    def mark_failed(self, task: models.ProcessingTask, error: str) -> None:
        task.status = "failed"
        task.error_details = error
        self.db.flush()


# ── Audit ─────────────────────────────────────────────────────────────────────

class AuditRepository(BaseRepository):

    def log(
        self,
        user_id: int,
        action: str,
        target_type: str,
        target_id: int,
        details: Optional[dict] = None,
        ip_address: Optional[str] = None,
    ) -> None:
        log = models.AuditLog(
            user_id=user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=details,
            ip_address=ip_address,
        )
        self.db.add(log)
        self.db.flush()
