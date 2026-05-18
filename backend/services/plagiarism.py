"""
Plagiarism detection service — Semantic Vector Embedding refactor.

Upgraded to use SentenceTransformers to capture "similar logic structures"
rather than just exact-word TF-IDF overlaps.
"""
import logging
from itertools import combinations
import numpy as np

from sqlalchemy.orm import Session
from sklearn.metrics.pairwise import cosine_similarity

from backend.db import models
from backend.core.logging import get_logger

logger = get_logger("services.plagiarism")

# Semantic similarity threshold is usually higher than TF-IDF
SIMILARITY_THRESHOLD = 0.88  

# Lazy load the HuggingFace embedding model to save memory until needed
_embedding_model = None

def _get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        logger.info("[Plagiarism] Loading SentenceTransformer (all-MiniLM-L6-v2)...")
        # all-MiniLM-L6-v2 is ultra-fast, lightweight, and great for semantic similarity
        _embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    return _embedding_model


def run_plagiarism_check(db: Session, exam_id: int) -> int:
    """
    Run Semantic Cosine Similarity check across all extracted answers for an exam.
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
        # Join with Grade to fetch the AI's logic breakdown
        answers = (
            db.query(models.Answer)
            .join(models.Submission)
            .outerjoin(models.Grade, models.Answer.id == models.Grade.answer_id)
            .filter(
                models.Submission.exam_id == exam_id,
                models.Answer.question_id == question.id,
                models.Answer.extraction_status == "completed",
                models.Answer.transcribed_text.isnot(None),
            )
            .all()
        )

        valid_data = []
        for a in answers:
            raw_text = a.transcribed_text.strip() if a.transcribed_text else ""
            if not raw_text:
                continue
                
            # THE TRICK: Append the AI's justification to the text before embedding.
            # This ensures we are comparing the underlying *logic structure* and mistakes.
            semantic_payload = f"Student Answer: {raw_text}"
            if a.grade and a.grade.ai_justification:
                semantic_payload += f"\nLogical Analysis: {a.grade.ai_justification}"
                
            valid_data.append((a.id, semantic_payload))

        if len(valid_data) < 2:
            continue

        answer_ids = [v[0] for v in valid_data]
        texts = [v[1] for v in valid_data]

        try:
            similarity_matrix = _compute_semantic_similarity(texts)
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


def _compute_semantic_similarity(texts: list[str]) -> np.ndarray:
    """Compute pairwise cosine similarity using dense vector embeddings."""
    model = _get_embedding_model()
    
    # Generate embeddings (returns a numpy array of vectors)
    embeddings = model.encode(texts, convert_to_numpy=True)
    
    # Compute cosine similarity matrix
    return cosine_similarity(embeddings)
