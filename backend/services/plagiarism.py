"""
Plagiarism detection using TF-IDF cosine similarity.
Compares OCR transcripts of answers to the same question across all students.
"""
import math
import re
from collections import Counter
from itertools import combinations

from sqlalchemy.orm import Session
from backend import models


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\b[a-z]{2,}\b", text.lower())


def _tfidf_vectors(corpus: list[list[str]]) -> list[dict[str, float]]:
    """Compute TF-IDF vector for each document in corpus."""
    N = len(corpus)
    # Document frequency
    df: Counter = Counter()
    for doc in corpus:
        df.update(set(doc))

    vectors = []
    for doc in corpus:
        tf = Counter(doc)
        total = len(doc) or 1
        vec = {}
        for term, count in tf.items():
            tf_score = count / total
            idf_score = math.log((N + 1) / (df[term] + 1)) + 1
            vec[term] = tf_score * idf_score
        vectors.append(vec)
    return vectors


def _cosine_similarity(a: dict[str, float], b: dict[str, float]) -> float:
    common = set(a) & set(b)
    dot = sum(a[t] * b[t] for t in common)
    norm_a = math.sqrt(sum(v ** 2 for v in a.values()))
    norm_b = math.sqrt(sum(v ** 2 for v in b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def detect_plagiarism(
    exam_id: int,
    db: Session,
    threshold: float = 0.75,
) -> None:
    """
    Run TF-IDF plagiarism detection on all graded answers for exam_id.
    Updates plagiarism_flag and plagiarism_score on Answer rows in-place.
    """
    exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if not exam:
        return

    # Group answers by question
    for question in exam.questions:
        answers = (
            db.query(models.Answer)
            .join(models.StudentPaper)
            .filter(
                models.StudentPaper.exam_id == exam_id,
                models.Answer.question_id == question.id,
                models.Answer.ocr_text != None,
                models.Answer.ocr_text != "",
            )
            .all()
        )

        if len(answers) < 2:
            continue

        corpus = [_tokenize(a.ocr_text or "") for a in answers]
        vectors = _tfidf_vectors(corpus)

        for i, j in combinations(range(len(answers)), 2):
            sim = _cosine_similarity(vectors[i], vectors[j])
            if sim >= threshold:
                answers[i].plagiarism_flag = True
                answers[j].plagiarism_flag = True
                # Store the max similarity score seen for each answer
                answers[i].plagiarism_score = max(answers[i].plagiarism_score or 0, sim)
                answers[j].plagiarism_score = max(answers[j].plagiarism_score or 0, sim)

    db.commit()
