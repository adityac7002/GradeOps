"""
Structured exception hierarchy for GradeOps.

Every exception maps to an HTTP status code and a machine-readable error code.
The global handler in main.py converts these into consistent JSON responses:

    {
        "error": "EXAM_NOT_FOUND",
        "message": "Exam with id 42 does not exist.",
        "details": null
    }
"""
from typing import Any, Optional


class GradeOpsError(Exception):
    """Base exception — all app errors inherit from this."""
    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, message: str = "An unexpected error occurred.", details: Optional[Any] = None):
        self.message = message
        self.details = details
        super().__init__(self.message)


# ── Auth / Access ────────────────────────────────────────────────────────────

class AuthenticationError(GradeOpsError):
    status_code = 401
    error_code = "AUTHENTICATION_FAILED"

    def __init__(self, message: str = "Could not validate credentials."):
        super().__init__(message)


class AuthorizationError(GradeOpsError):
    status_code = 403
    error_code = "FORBIDDEN"

    def __init__(self, message: str = "You do not have permission to perform this action."):
        super().__init__(message)


class RateLimitError(GradeOpsError):
    status_code = 429
    error_code = "RATE_LIMITED"

    def __init__(self, message: str = "Too many requests. Please try again later."):
        super().__init__(message)


# ── Resource ─────────────────────────────────────────────────────────────────

class NotFoundError(GradeOpsError):
    status_code = 404
    error_code = "NOT_FOUND"

    def __init__(self, resource: str = "Resource", identifier: Any = None):
        msg = f"{resource} not found." if not identifier else f"{resource} with id {identifier} does not exist."
        super().__init__(msg)


class ConflictError(GradeOpsError):
    status_code = 409
    error_code = "CONFLICT"

    def __init__(self, message: str = "Resource already exists."):
        super().__init__(message)


# ── Validation ───────────────────────────────────────────────────────────────

class ValidationError(GradeOpsError):
    status_code = 422
    error_code = "VALIDATION_ERROR"

    def __init__(self, message: str = "Input validation failed.", details: Any = None):
        super().__init__(message, details)


class InvalidRubricError(ValidationError):
    error_code = "INVALID_RUBRIC"


class InvalidFileError(ValidationError):
    error_code = "INVALID_FILE"

    def __init__(self, message: str = "Invalid file format or size."):
        super().__init__(message)


# ── Processing ───────────────────────────────────────────────────────────────

class ProcessingError(GradeOpsError):
    status_code = 500
    error_code = "PROCESSING_ERROR"


class OCRError(ProcessingError):
    error_code = "OCR_FAILED"


class GradingError(ProcessingError):
    error_code = "GRADING_FAILED"


class ExternalServiceError(GradeOpsError):
    status_code = 502
    error_code = "EXTERNAL_SERVICE_ERROR"

    def __init__(self, service: str = "external service", message: str = ""):
        super().__init__(f"Failed to communicate with {service}. {message}".strip())
