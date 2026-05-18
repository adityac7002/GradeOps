"""
Plagiarism detection service — production refactor.

Key fixes from audit:
- References only models that actually exist (PlagiarismFlag, Answer, Submission)
- No reference to Answer.plagiarism_flag (column that didn't exist)
- Stores results in PlagiarismFlag table correctly
- Operates per-question for meaningful comparisons
"""
import logging
from itertools import combinations
from typing import Optional

from sqlalchemy.orm import Session, joinedload
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from backend.db import models
from backend.core.logging import get_logger

logger = get_logger("services.plagiarism")

SIMILARITY_THRESHOLD = 0.80  # Flag pairs above this cosine similarity


def run_plagiarism_check(db: Session, exam_id: int) -> int:
    """
    Run TF-IDF cosine similarity check across all extracted answers for an exam.

    Operates question-by-question so comparisons are meaningful.

    Returns:
        Number of suspicious pairs detected
    """
    # Clear old flags for this exam
    db.query(models.PlagiarismFlag).filter(
        models.PlagiarismFlag.exam_id == exam_id
    ).delete()
    db.flush()

    questions = (
        db.query(models.Question)
        .filter(models.Question.exam_id == exam_id)
        .all()
    )

    total_flags = 0

    for question in questions:
        answers = (
            db.query(models.Answer)
            .join(models.Submission)
            .filter(
                models.Submission.exam_id == exam_id,
                models.Answer.question_id == question.id,
                models.Answer.extraction_status == "completed",
                models.Answer.transcribed_text.isnot(None),
            )
            .all()
        )

        valid = [(a.id, a.transcribed_text) for a in answers if a.transcribed_text and a.transcribed_text.strip()]

        if len(valid) < 2:
            continue

        answer_ids = [v[0] for v in valid]
        texts = [v[1] for v in valid]

        try:
            similarity_matrix = _compute_similarity(texts)
        except Exception as e:
            logger.warning("Could not compute similarity for Q%d: %s", question.number, e)
            continue

        for i, j in combinations(range(len(texts)), 2):
            score = float(similarity_matrix[i, j])
            if score >= SIMILARITY_THRESHOLD:
                flag = models.PlagiarismFlag(
                    exam_id=exam_id,
                    question_id=question.id,
                    answer_ids_json=[answer_ids[i], answer_ids[j]],
                    similarity=score,
                )
                db.add(flag)
                total_flags += 1
                logger.info(
                    "Plagiarism flag: exam=%d, Q%d, answers=%d vs %d, similarity=%.2f",
                    exam_id, question.number, answer_ids[i], answer_ids[j], score
                )

    db.commit()
    logger.info("Plagiarism check complete for exam %d: %d flags", exam_id, total_flags)
    return total_flags


def _compute_similarity(texts: list[str]) -> np.ndarray:
    """Compute pairwise TF-IDF cosine similarity matrix."""
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        min_df=1,
        stop_words="english",
        strip_accents="unicode",
    )
    matrix = vectorizer.fit_transform(texts)
    return cosine_similarity(matrix)
