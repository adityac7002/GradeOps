import sys
sys.path.insert(0, '.')
from backend.database import SessionLocal
from backend import models

db = SessionLocal()
answers = db.query(models.Answer).join(models.StudentPaper).filter(models.StudentPaper.exam_id == 4).all()
for a in answers:
    a.status = 'uploaded'
    a.ocr_text = None
    a.ai_grade = None
    a.ai_justification = None
db.commit()

exam = db.query(models.Exam).filter_by(id=4).first()
if exam:
    exam.status = 'uploaded'
    for p in exam.papers:
        p.status = 'uploaded'
db.commit()
print('Reset exam 4')
db.close()
