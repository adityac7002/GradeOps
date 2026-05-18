"""
Rubric validation service.

Validates rubric JSON against the RubricSchema definition.
Returns (is_valid: bool, error_message: str) tuples to keep endpoint code clean.
"""
import logging
from typing import Optional

from pydantic import ValidationError

from backend.db.schemas import RubricSchema
from backend.core.logging import get_logger

logger = get_logger("services.rubric")


def validate_rubric(rubric_data: dict) -> tuple[bool, Optional[str]]:
    """
    Validate a rubric dict against the schema.

    Returns:
        (True, None) on success
        (False, error_message) on failure
    """
    try:
        parsed = RubricSchema.model_validate(rubric_data)

        # Business-logic validation beyond schema
        if not parsed.questions:
            return False, "Rubric must contain at least one question."

        for q in parsed.questions:
            if q.max_marks <= 0:
                return False, f"Question {q.number}: max_marks must be greater than 0."

            criteria_total = sum(c.marks for c in q.criteria)
            if q.criteria and criteria_total > q.max_marks:
                return False, (
                    f"Question {q.number}: criteria marks ({criteria_total}) "
                    f"exceed max_marks ({q.max_marks})."
                )

        return True, None

    except ValidationError as e:
        first_error = e.errors()[0]
        field = " → ".join(str(loc) for loc in first_error["loc"])
        return False, f"{field}: {first_error['msg']}"
    except Exception as e:
        logger.warning("Rubric validation raised unexpected error: %s", e)
        return False, str(e)
