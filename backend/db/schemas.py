from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field


# ── Auth ──────────────────────────────────────────────────────────────────────

class UserOut(BaseModel):
    id: int
    email: EmailStr
    role: str

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ── Rubric ────────────────────────────────────────────────────────────────────

class RubricCriterion(BaseModel):
    id: str
    desc: str
    marks: float
    partial: bool = False


class RubricQuestion(BaseModel):
    number: int
    max_marks: float
    answer_key: Optional[str] = None
    criteria: List[RubricCriterion]
    common_deductions: List[Dict[str, Any]] = []


class RubricSchema(BaseModel):
    questions: List[RubricQuestion]


# ── Exam ──────────────────────────────────────────────────────────────────────

class ExamOut(BaseModel):
    id: int
    title: str
    owner_id: int
    rubric_json: Optional[Dict[str, Any]] = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Submission & Paper ────────────────────────────────────────────────────────

class SubmissionOut(BaseModel):
    id: int
    exam_id: int
    student_id: int
    pdf_path: str
    num_pages: int

    model_config = {"from_attributes": True}


# ── Answer & Grade ────────────────────────────────────────────────────────────

class GradeOut(BaseModel):
    ai_score: Optional[float] = None
    ai_breakdown_json: Optional[Dict[str, Any]] = None
    ai_justification: Optional[str] = None
    ai_confidence: Optional[float] = None
    status: str
    final_score: Optional[float] = None
    reviewed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AnswerOut(BaseModel):
    id: int
    submission_id: int
    question_id: int
    crop_path: Optional[str] = None
    transcribed_text: Optional[str] = None
    ocr_confidence: Optional[float] = None
    extraction_status: str
    grade: Optional[GradeOut] = None

    model_config = {"from_attributes": True}


# ── Operational ───────────────────────────────────────────────────────────────

class ProcessingTaskOut(BaseModel):
    id: int
    task_type: str
    target_id: int
    status: str
    progress: float
    message: Optional[str] = None
    error_details: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
