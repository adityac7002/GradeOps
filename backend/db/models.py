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
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="ta")  # "instructor" | "ta"
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    exams: Mapped[list["Exam"]] = relationship("Exam", back_populates="owner")


class Exam(Base):
    __tablename__ = "exams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    course: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="uploaded")
    # uploaded | processing | graded | reviewing | complete
    question_paper_path: Mapped[Optional[str]] = mapped_column(String(500))  # uploaded QP PDF
    qp_extracted: Mapped[bool] = mapped_column(Boolean, default=False)  # True after QP parsed
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    owner: Mapped["User"] = relationship("User", back_populates="exams")
    questions: Mapped[list["Question"]] = relationship("Question", back_populates="exam", cascade="all, delete-orphan")
    papers: Mapped[list["StudentPaper"]] = relationship("StudentPaper", back_populates="exam", cascade="all, delete-orphan")


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    exam_id: Mapped[int] = mapped_column(Integer, ForeignKey("exams.id"), nullable=False)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    prompt: Mapped[Optional[str]] = mapped_column(Text)       # full question text from QP
    given_data: Mapped[Optional[str]] = mapped_column(Text)   # formulas/tables given in QP
    max_points: Mapped[float] = mapped_column(Float, default=10.0)

    exam: Mapped["Exam"] = relationship("Exam", back_populates="questions")
    rubric_items: Mapped[list["RubricItem"]] = relationship("RubricItem", back_populates="question", cascade="all, delete-orphan")
    answers: Mapped[list["Answer"]] = relationship("Answer", back_populates="question")


class RubricItem(Base):
    __tablename__ = "rubric_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    question_id: Mapped[int] = mapped_column(Integer, ForeignKey("questions.id"), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    points: Mapped[float] = mapped_column(Float, nullable=False)
    keywords: Mapped[Optional[list]] = mapped_column(JSON)  # list[str]

    question: Mapped["Question"] = relationship("Question", back_populates="rubric_items")


class StudentPaper(Base):
    __tablename__ = "student_papers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    exam_id: Mapped[int] = mapped_column(Integer, ForeignKey("exams.id"), nullable=False)
    student_id: Mapped[str] = mapped_column(String(100), nullable=False)
    student_name: Mapped[Optional[str]] = mapped_column(String(255))
    pdf_path: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="uploaded")
    # uploaded | processing | graded

    exam: Mapped["Exam"] = relationship("Exam", back_populates="papers")
    answers: Mapped[list["Answer"]] = relationship("Answer", back_populates="paper", cascade="all, delete-orphan")


class Answer(Base):
    __tablename__ = "answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    paper_id: Mapped[int] = mapped_column(Integer, ForeignKey("student_papers.id"), nullable=False)
    question_id: Mapped[int] = mapped_column(Integer, ForeignKey("questions.id"), nullable=False)
    image_path: Mapped[Optional[str]] = mapped_column(String(500))
    ocr_text: Mapped[Optional[str]] = mapped_column(Text)
    ai_grade: Mapped[Optional[float]] = mapped_column(Float)
    ai_justification: Mapped[Optional[str]] = mapped_column(Text)
    ta_grade: Mapped[Optional[float]] = mapped_column(Float)
    ta_override_reason: Mapped[Optional[str]] = mapped_column(Text)
    final_grade: Mapped[Optional[float]] = mapped_column(Float)
    plagiarism_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    plagiarism_score: Mapped[Optional[float]] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    # pending | ocr_done | graded | approved | overridden
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    paper: Mapped["StudentPaper"] = relationship("StudentPaper", back_populates="answers")
    question: Mapped["Question"] = relationship("Question", back_populates="answers")
