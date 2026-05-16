from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


# ── Auth ──────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: str
    role: str = Field(default="ta", pattern="^(instructor|ta)$")


class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: str
    is_active: bool

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ── Rubric ────────────────────────────────────────────────────────────────────

class RubricItemCreate(BaseModel):
    description: str
    points: float
    keywords: list[str] = []


class RubricItemOut(RubricItemCreate):
    id: int
    question_id: int
    model_config = {"from_attributes": True}


class QuestionCreate(BaseModel):
    number: int
    prompt: Optional[str] = None
    given_data: Optional[str] = None
    max_points: float = 10.0
    rubric_items: list[RubricItemCreate] = []


class QuestionOut(BaseModel):
    id: int
    exam_id: int
    number: int
    prompt: Optional[str]
    given_data: Optional[str] = None
    max_points: float
    rubric_items: list[RubricItemOut]
    model_config = {"from_attributes": True}


# ── Exam ──────────────────────────────────────────────────────────────────────

class ExamCreate(BaseModel):
    title: str
    course: str


class ExamOut(BaseModel):
    id: int
    title: str
    course: str
    status: str
    owner_id: int
    created_at: datetime
    question_paper_path: Optional[str] = None
    qp_extracted: bool = False
    questions: list[QuestionOut] = []
    model_config = {"from_attributes": True}


class ExamSummary(BaseModel):
    id: int
    title: str
    course: str
    status: str
    created_at: datetime
    paper_count: int = 0
    graded_count: int = 0
    model_config = {"from_attributes": True}


# ── Papers ────────────────────────────────────────────────────────────────────

class PaperOut(BaseModel):
    id: int
    exam_id: int
    student_id: str
    student_name: Optional[str]
    status: str
    model_config = {"from_attributes": True}


# ── Answers ───────────────────────────────────────────────────────────────────

class AnswerOut(BaseModel):
    id: int
    paper_id: int
    question_id: int
    image_path: Optional[str]
    ocr_text: Optional[str]
    ai_grade: Optional[float]
    ai_justification: Optional[str]
    ta_grade: Optional[float]
    ta_override_reason: Optional[str]
    final_grade: Optional[float]
    plagiarism_flag: bool
    plagiarism_score: Optional[float]
    status: str
    reviewed_at: Optional[datetime]
    # Nested for dashboard convenience
    student_id: Optional[str] = None
    student_name: Optional[str] = None
    question_number: Optional[int] = None
    max_points: Optional[float] = None
    rubric_items: list[RubricItemOut] = []
    model_config = {"from_attributes": True}


class TAReview(BaseModel):
    action: str = Field(pattern="^(approve|override)$")
    ta_grade: Optional[float] = None
    ta_override_reason: Optional[str] = None


# ── Grading pipeline ──────────────────────────────────────────────────────────

class GradeResult(BaseModel):
    grade: float
    justification: str
    rubric_breakdown: list[dict] = []


# ── Plagiarism ────────────────────────────────────────────────────────────────

class PlagiarismPair(BaseModel):
    answer_id_a: int
    answer_id_b: int
    student_id_a: str
    student_id_b: str
    question_number: int
    similarity_score: float
    ocr_text_a: Optional[str]
    ocr_text_b: Optional[str]


# ── Dashboard ─────────────────────────────────────────────────────────────────

class DashboardStats(BaseModel):
    total_answers: int
    pending: int
    approved: int
    overridden: int
    graded: int
    plagiarism_flagged: int


# ── Question Paper Upload ─────────────────────────────────────────────────────

class ExtractedRubricItem(BaseModel):
    description: str
    points: float
    keywords: list[str] = []


class ExtractedQuestion(BaseModel):
    number: int
    prompt: str
    given_data: Optional[str] = None
    max_points: float
    rubric_items: list[ExtractedRubricItem] = []


class QuestionPaperUploadOut(BaseModel):
    exam_id: int
    question_paper_path: str
    extracted_questions: list[ExtractedQuestion]
    message: str
