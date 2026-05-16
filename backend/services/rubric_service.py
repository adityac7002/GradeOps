from typing import Dict, Any, List
from pydantic import ValidationError
from backend.db.schemas import RubricSchema

def validate_rubric(rubric_data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validates the rubric JSON against the standard schema.
    Returns (is_valid, error_message).
    """
    try:
        RubricSchema.model_validate(rubric_data)
        return True, ""
    except ValidationError as e:
        # Format the pydantic error into a human-readable string
        errors = []
        for err in e.errors():
            loc = " -> ".join([str(x) for x in err["loc"]])
            msg = err["msg"]
            errors.append(f"[{loc}]: {msg}")
        return False, "; ".join(errors)

def get_questions_from_rubric(rubric_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extracts question metadata from a validated rubric."""
    return rubric_data.get("questions", [])
