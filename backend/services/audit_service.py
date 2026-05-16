from typing import Any
from sqlalchemy.orm import Session
from backend.db import models

def log_action(
    db: Session,
    user_id: int,
    action: str,
    target_type: str,
    target_id: int,
    details: Any = None
):
    """Log an administrative or operational action for audit purposes."""
    log = models.AuditLog(
        user_id=user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        details=details
    )
    db.add(log)
    db.commit()
