from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.db.session import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="ta")  # "instructor" | "ta"
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    exams: Mapped[list["Exam"]] = relationship("Exam", back_populates="owner")


class Exam(Base):
    __tablename__ = "exams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    rubric_json: Mapped[Optional[dict]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(30), default="draft")
    # draft | processing | graded | complete
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    owner: Mapped["User"] = relationship("User", back_populates="exams")
    students: Mapped[list["Student"]] = relationship("Student", back_populates="exam", cascade="all, delete-orphan")
    submissions: Mapped[list["Submission"]] = relationship("Submission", back_populates="exam", cascade="all, delete-orphan")
    questions: Mapped[list["Question"]] = relationship("Question", back_populates="exam", cascade="all, delete-orphan")


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    exam_id: Mapped[int] = mapped_column(Integer, ForeignKey("exams.id"), nullable=False)
    roll_no: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(255))

    exam: Mapped["Exam"] = relationship("Exam", back_populates="students")
    submissions: Mapped[list["Submission"]] = relationship("Submission", back_populates="student")


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    exam_id: Mapped[int] = mapped_column(Integer, ForeignKey("exams.id"), nullable=False)
    student_id: Mapped[int] = mapped_column(Integer, ForeignKey("students.id"), nullable=False)
    pdf_path: Mapped[str] = mapped_column(String(500), nullable=False)
    num_pages: Mapped[int] = mapped_column(Integer, default=1)

    exam: Mapped["Exam"] = relationship("Exam", back_populates="submissions")
    student: Mapped["Student"] = relationship("Student", back_populates="submissions")
    answers: Mapped[list["Answer"]] = relationship("Answer", back_populates="submission", cascade="all, delete-orphan")


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    exam_id: Mapped[int] = mapped_column(Integer, ForeignKey("exams.id"), nullable=False)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    max_marks: Mapped[float] = mapped_column(Float, default=10.0)

    exam: Mapped["Exam"] = relationship("Exam", back_populates="questions")
    answers: Mapped[list["Answer"]] = relationship("Answer", back_populates="question")


class Answer(Base):
    __tablename__ = "answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    submission_id: Mapped[int] = mapped_column(Integer, ForeignKey("submissions.id"), nullable=False)
    question_id: Mapped[int] = mapped_column(Integer, ForeignKey("questions.id"), nullable=False)
    crop_path: Mapped[Optional[str]] = mapped_column(String(500))
    transcribed_text: Mapped[Optional[str]] = mapped_column(Text)
    ocr_confidence: Mapped[Optional[float]] = mapped_column(Float)
    extraction_status: Mapped[str] = mapped_column(String(30), default="pending")
    # pending | completed | failed

    submission: Mapped["Submission"] = relationship("Submission", back_populates="answers")
    question: Mapped["Question"] = relationship("Question", back_populates="answers")
    grade: Mapped[Optional["Grade"]] = relationship("Grade", back_populates="answer", uselist=False, cascade="all, delete-orphan")


class Grade(Base):
    __tablename__ = "grades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    answer_id: Mapped[int] = mapped_column(Integer, ForeignKey("answers.id"), nullable=False, unique=True)
    ai_score: Mapped[Optional[float]] = mapped_column(Float)
    ai_breakdown_json: Mapped[Optional[dict]] = mapped_column(JSON)
    ai_justification: Mapped[Optional[str]] = mapped_column(Text)
    ai_confidence: Mapped[Optional[float]] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    # pending | graded | reviewed
    final_score: Mapped[Optional[float]] = mapped_column(Float)
    ta_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"))
    ta_notes: Mapped[Optional[str]] = mapped_column(Text)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    answer: Mapped["Answer"] = relationship("Answer", back_populates="grade")


class PlagiarismFlag(Base):
    __tablename__ = "plagiarism_flags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    exam_id: Mapped[int] = mapped_column(Integer, ForeignKey("exams.id"), nullable=False)
    question_id: Mapped[int] = mapped_column(Integer, ForeignKey("questions.id"), nullable=False)
    answer_ids_json: Mapped[list] = mapped_column(JSON, nullable=False) # list of IDs
    similarity: Mapped[float] = mapped_column(Float, nullable=False)
    cluster_id: Mapped[Optional[str]] = mapped_column(String(50))


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(100))
    target_type: Mapped[str] = mapped_column(String(50))
    target_id: Mapped[int] = mapped_column(Integer)
    details: Mapped[Optional[dict]] = mapped_column(JSON)
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship("User")
