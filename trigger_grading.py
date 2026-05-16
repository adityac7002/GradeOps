import sys, json, urllib.request, urllib.error
sys.path.insert(0, '.')
from backend.database import SessionLocal
from backend import models
from backend.auth import create_access_token

db = SessionLocal()
exam = db.query(models.Exam).filter_by(id=4).first()
if not exam:
    print('Exam 4 not found')
    sys.exit(1)

token = create_access_token({'sub': str(exam.owner_id)})
req = urllib.request.Request(
    'http://localhost:8000/api/exams/4/grade',
    method='POST',
    headers={'Authorization': f'Bearer {token}'}
)
try:
    with urllib.request.urlopen(req) as response:
        print(response.read().decode('utf-8'))
except urllib.error.HTTPError as e:
    err_text = e.read().decode('utf-8')
    print(f'HTTP Error: {e.code} - {err_text}')
