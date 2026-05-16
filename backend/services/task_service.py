from sqlalchemy.orm import Session
from backend.db import models

def create_task(db: Session, task_type: str, target_id: int, message: str = "") -> models.ProcessingTask:
    task = models.ProcessingTask(
        task_type=task_type,
        target_id=target_id,
        message=message,
        status="pending"
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task

def update_task_progress(db: Session, task_id: int, progress: float, message: str = None):
    task = db.query(models.ProcessingTask).filter(models.ProcessingTask.id == task_id).first()
    if task:
        task.progress = progress
        if message:
            task.message = message
        task.status = "running"
        db.commit()

def mark_task_complete(db: Session, task_id: int, message: str = "Completed"):
    task = db.query(models.ProcessingTask).filter(models.ProcessingTask.id == task_id).first()
    if task:
        task.status = "completed"
        task.progress = 100.0
        task.message = message
        db.commit()

def mark_task_failed(db: Session, task_id: int, error: str):
    task = db.query(models.ProcessingTask).filter(models.ProcessingTask.id == task_id).first()
    if task:
        task.status = "failed"
        task.error_details = error
        db.commit()
