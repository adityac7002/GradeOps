"""
Pydantic schemas for API request/response validation.

Organized by domain. All responses use from_attributes for ORM compatibility.
Replaces the previous flat schemas.py that mixed concerns and had orphaned schemas.

Key improvements:
- Typed request schemas for every mutation endpoint
- Pagination wrapper for list endpoints
- Proper Optional handling
- ProcessingTask schema now backed by a real model
"""
from datetime import datetime
from typing import Optional, Any, Generic, TypeVar
from pydantic import BaseModel, EmailStr, Field, ConfigDict


# ── Generic Pagination ───────────────────────────────────────────────────────

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated list response."""
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class PaginationParams(BaseModel):
    """Query parameters for paginated endpoints."""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


# ── Auth ─────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    role: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ── Rubric ───────────────────────────────────────────────────────────────────

class RubricCriterion(BaseModel):
    id: str
    desc: str
    marks: float = Field(ge=0)
    partial: bool = False


class RubricQuestion(BaseModel):
    number: int = Field(ge=1)
    max_marks: float = Field(ge=0)
    answer_key: Optional[str] = None
    criteria: list[RubricCriterion] = []
    common_deductions: list[dict[str, Any]] = []


class RubricSchema(BaseModel):
    questions: list[RubricQuestion]


# ── Exam ─────────────────────────────────────────────────────────────────────

class ExamCreate(BaseModel):
    """Used when creating an exam via multipart form (title comes as Form field)."""
    pass  # Title and rubric come as Form() params, not JSON body


class ExamOut(BaseModel):
    id: int
    title: str
    course_code: Optional[str] = None
    owner_id: int
    rubric_json: Optional[dict[str, Any]] = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExamDetailOut(ExamOut):
    """Extended exam response with counts."""
    total_submissions: int = 0
    total_answers: int = 0
    graded_count: int = 0


# ── Grade ────────────────────────────────────────────────────────────────────

class GradeOut(BaseModel):
    id: int
    ai_score: Optional[float] = None
    ai_breakdown_json: Optional[dict[str, Any]] = None
    ai_justification: Optional[str] = None
    ai_confidence: Optional[float] = None
    status: str
    final_score: Optional[float] = None
    ta_id: Optional[int] = None
    ta_notes: Optional[str] = None
    reviewed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ── Answer ───────────────────────────────────────────────────────────────────

class AnswerOut(BaseModel):
    id: int
    submission_id: int
    question_id: int
    crop_path: Optional[str] = None
    transcribed_text: Optional[str] = None
    ocr_confidence: Optional[float] = None
    extraction_status: str
    grade: Optional[GradeOut] = None

    model_config = ConfigDict(from_attributes=True)


# ── Review (TA Workflow) ─────────────────────────────────────────────────────

class ReviewRequest(BaseModel):
    """Typed request for TA review actions — replaces Dict[str, Any]."""
    final_score: float = Field(ge=0)
    ta_notes: Optional[str] = Field(default=None, max_length=2000)
    status: str = Field(default="reviewed", pattern="^(reviewed|approved|override)$")


# ── Processing Task ──────────────────────────────────────────────────────────

class ProcessingTaskOut(BaseModel):
    id: int
    exam_id: int
    task_type: str
    status: str
    progress: float
    total_items: int
    completed_items: int
    message: Optional[str] = None
    error_details: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Analytics ────────────────────────────────────────────────────────────────

class ExamAnalytics(BaseModel):
    """Structured analytics response — replaces untyped dict."""
    average_score: float
    median_score: float
    total_graded: int
    total_reviewed: int
    distribution: dict[str, int]
    time_saved_hours: float
    ai_ta_correlation: Optional[float] = None


# ── Extraction Status ────────────────────────────────────────────────────────

class ExtractionStatusOut(BaseModel):
    status: str
    total_answers: int
    completed_answers: int
    failed_answers: int
    percent: float


# ── Health ───────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    database: str
    uptime_seconds: float
