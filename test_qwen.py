import sys; sys.path.insert(0, '.')
import traceback
import logging

logging.basicConfig(level=logging.INFO)

from backend.database import SessionLocal
from backend import models
from backend.services.pdf_processor import extract_answer_images
from backend.services.grader import grade_answer

db = SessionLocal()
paper = db.query(models.StudentPaper).filter_by(exam_id=4).first()
if not paper:
    print('No paper')
    sys.exit(0)

print(f'Paper: {paper.pdf_path}')
try:
    images = extract_answer_images(paper.pdf_path, 1)
    img_path = images.get(1)
    if not img_path:
        print('No image')
        sys.exit(0)
    
    print(f'Testing Q1 on image: {img_path}')
    question = db.query(models.Question).filter_by(exam_id=4, number=1).first()
    
    ri = [{"description": r.description, "points": r.points, "keywords": r.keywords or []} for r in question.rubric_items]
    
    res = grade_answer(
        ocr_text="",
        rubric_items=ri,
        max_points=question.max_points,
        image_path=img_path,
        question_prompt=question.prompt,
        given_data=question.given_data
    )
    print("Grade Result:", res)
except Exception as e:
    traceback.print_exc()

