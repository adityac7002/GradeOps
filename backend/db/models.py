"""
SQLAlchemy ORM models for GradeOps.

Changes from previous version (audit fixes):
- Added `ProcessingTask` model (was in schemas but missing from DB)
- Added `updated_at` timestamps to ALL models
- Added `created_at` where missing (Student, Submission, Question, Answer, Grade)
- Added composite indexes for common query patterns
- Added proper index on foreign keys
- Fixed `review_answer` — `Grade` model now tracks reviewer info properly
- Added `is_active` soft-delete flag on User
- Hardened column constraints
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey, Index, Integer,
    JSON, String, Text, func, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.db.session import Base


# ── Mixin for common timestamp columns ───────────────────────────────────────

class TimestampMixin:
    """Adds created_at and updated_at to any model."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


# ── User ─────────────────────────────────────────────────────────────────────

class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="ta", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    exams: Mapped[list["Exam"]] = relationship("Exam", back_populates="owner")


# ── Exam ─────────────────────────────────────────────────────────────────────

class Exam(TimestampMixin, Base):
    __tablename__ = "exams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    course_code: Mapped[Optional[str]] = mapped_column(String(50))
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    rubric_json: Mapped[Optional[dict]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False)
    # Statuses: draft | processing | extracting | ready_for_grading | grading | complete | error

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="exams")
    students: Mapped[list["Student"]] = relationship("Student", back_populates="exam", cascade="all, delete-orphan")
    submissions: Mapped[list["Submission"]] = relationship("Submission", back_populates="exam", cascade="all, delete-orphan")
    questions: Mapped[list["Question"]] = relationship("Question", back_populates="exam", cascade="all, delete-orphan")
    tasks: Mapped[list["ProcessingTask"]] = relationship("ProcessingTask", back_populates="exam", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_exams_owner_status", "owner_id", "status"),
    )


# ── Student ──────────────────────────────────────────────────────────────────

class Student(TimestampMixin, Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    exam_id: Mapped[int] = mapped_column(Integer, ForeignKey("exams.id"), nullable=False, index=True)
    roll_no: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(255))

    # Relationships
    exam: Mapped["Exam"] = relationship("Exam", back_populates="students")
    submissions: Mapped[list["Submission"]] = relationship("Submission", back_populates="student")

    __table_args__ = (
        UniqueConstraint("exam_id", "roll_no", name="uq_student_exam_roll"),
    )


# ── Submission ───────────────────────────────────────────────────────────────

class Submission(TimestampMixin, Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    exam_id: Mapped[int] = mapped_column(Integer, ForeignKey("exams.id"), nullable=False, index=True)
    student_id: Mapped[int] = mapped_column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    pdf_path: Mapped[str] = mapped_column(String(500), nullable=False)
    num_pages: Mapped[int] = mapped_column(Integer, default=1)

    # Relationships
    exam: Mapped["Exam"] = relationship("Exam", back_populates="submissions")
    student: Mapped["Student"] = relationship("Student", back_populates="submissions")
    answers: Mapped[list["Answer"]] = relationship("Answer", back_populates="submission", cascade="all, delete-orphan")


# ── Question ─────────────────────────────────────────────────────────────────

class Question(TimestampMixin, Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    exam_id: Mapped[int] = mapped_column(Integer, ForeignKey("exams.id"), nullable=False, index=True)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    max_marks: Mapped[float] = mapped_column(Float, default=10.0)

    # Relationships
    exam: Mapped["Exam"] = relationship("Exam", back_populates="questions")
    answers: Mapped[list["Answer"]] = relationship("Answer", back_populates="question")

    __table_args__ = (
        UniqueConstraint("exam_id", "number", name="uq_question_exam_number"),
        Index("ix_questions_exam_number", "exam_id", "number"),
    )


# ── Answer ───────────────────────────────────────────────────────────────────

class Answer(TimestampMixin, Base):
    __tablename__ = "answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    submission_id: Mapped[int] = mapped_column(Integer, ForeignKey("submissions.id"), nullable=False, index=True)
    question_id: Mapped[int] = mapped_column(Integer, ForeignKey("questions.id"), nullable=False, index=True)
    crop_path: Mapped[Optional[str]] = mapped_column(String(500))
    transcribed_text: Mapped[Optional[str]] = mapped_column(Text)
    ocr_confidence: Mapped[Optional[float]] = mapped_column(Float)
    extraction_status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    # Statuses: pending | completed | failed

    # Relationships
    submission: Mapped["Submission"] = relationship("Submission", back_populates="answers")
    question: Mapped["Question"] = relationship("Question", back_populates="answers")
    grade: Mapped[Optional["Grade"]] = relationship("Grade", back_populates="answer", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_answers_submission_question", "submission_id", "question_id"),
        Index("ix_answers_extraction_status", "extraction_status"),
    )


# ── Grade ────────────────────────────────────────────────────────────────────

class Grade(TimestampMixin, Base):
    __tablename__ = "grades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    answer_id: Mapped[int] = mapped_column(Integer, ForeignKey("answers.id"), nullable=False, unique=True)

    # AI scoring
    ai_score: Mapped[Optional[float]] = mapped_column(Float)
    ai_breakdown_json: Mapped[Optional[dict]] = mapped_column(JSON)
    ai_justification: Mapped[Optional[str]] = mapped_column(Text)
    ai_confidence: Mapped[Optional[float]] = mapped_column(Float)

    # Review workflow
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    # Statuses: pending | graded | reviewed
    final_score: Mapped[Optional[float]] = mapped_column(Float)
    ta_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"))
    ta_notes: Mapped[Optional[str]] = mapped_column(Text)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Relationships
    answer: Mapped["Answer"] = relationship("Answer", back_populates="grade")

    __table_args__ = (
        Index("ix_grades_status", "status"),
    )


# ── Plagiarism Flag ──────────────────────────────────────────────────────────

class PlagiarismFlag(TimestampMixin, Base):
    __tablename__ = "plagiarism_flags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    exam_id: Mapped[int] = mapped_column(Integer, ForeignKey("exams.id"), nullable=False, index=True)
    question_id: Mapped[int] = mapped_column(Integer, ForeignKey("questions.id"), nullable=False)
    answer_ids_json: Mapped[list] = mapped_column(JSON, nullable=False)
    similarity: Mapped[float] = mapped_column(Float, nullable=False)
    cluster_id: Mapped[Optional[str]] = mapped_column(String(50))


# ── Processing Task ──────────────────────────────────────────────────────────

class ProcessingTask(TimestampMixin, Base):
    """
    Tracks long-running background tasks (OCR extraction, grading, plagiarism).
    Previously existed only in schemas — now has a real database model.
    """
    __tablename__ = "processing_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    exam_id: Mapped[int] = mapped_column(Integer, ForeignKey("exams.id"), nullable=False, index=True)
    task_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # Types: extraction | grading | plagiarism
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    # Statuses: pending | running | completed | failed
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    total_items: Mapped[int] = mapped_column(Integer, default=0)
    completed_items: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[Optional[str]] = mapped_column(String(500))
    error_details: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    exam: Mapped["Exam"] = relationship("Exam", back_populates="tasks")

    __table_args__ = (
        Index("ix_tasks_exam_type", "exam_id", "task_type"),
        Index("ix_tasks_status", "status"),
    )


# ── Audit Log ────────────────────────────────────────────────────────────────

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_id: Mapped[int] = mapped_column(Integer)
    details: Mapped[Optional[dict]] = mapped_column(JSON)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    user: Mapped["User"] = relationship("User")

    __table_args__ = (
        Index("ix_audit_user_action", "user_id", "action"),
        Index("ix_audit_target", "target_type", "target_id"),
    )
