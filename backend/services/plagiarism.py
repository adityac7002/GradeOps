import logging
import numpy as np
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from backend.db import models
from backend.services.gemini_service import gemini

logger = logging.getLogger(__name__)

def run_plagiarism_check(db: Session, exam_id: int):
    """
    Day 11: Plagiarism detection logic.
    1. Extract solution skeletons.
    2. Embed skeletons.
    3. Pairwise cosine similarity.
    4. Flag clusters.
    """
    # 1. Get all graded answers for this exam
    answers = db.query(models.Answer).join(models.Submission).filter(
        models.Submission.exam_id == exam_id,
        models.Answer.extraction_status == "completed"
    ).all()
    
    if len(answers) < 2:
        return

    # 2. Extract and Embed (Batched for speed)
    # Note: In a real demo, you'd cache these.
    skeletons = []
    answer_ids = []
    
    for ans in answers:
        # Step 2a: Reasoning Skeleton extraction
        prompt = f"Extract a 'reasoning skeleton' from this answer—an ordered list of solution steps. Answer: {ans.transcribed_text}"
        try:
            # Simple text generation for skeleton
            skeleton_res = gemini.client.models.generate_content(
                model=gemini.model_id,
                contents=prompt
            )
            skeleton_text = skeleton_res.text
            
            # Step 2b: Embedding
            embed_res = gemini.client.models.embed_content(
                model="text-embedding-004",
                contents=skeleton_text
            )
            embedding = embed_res.embeddings[0].values
            
            skeletons.append(embedding)
            answer_ids.append(ans.id)
        except Exception as e:
            logger.error(f"Embedding failed for answer {ans.id}: {e}")

    if not skeletons:
        return

    # 3. Pairwise Cosine Similarity
    embeddings_matrix = np.array(skeletons)
    # Normalize for cosine similarity
    norms = np.linalg.norm(embeddings_matrix, axis=1, keepdims=True)
    normalized = embeddings_matrix / (norms + 1e-9)
    
    # Similarity matrix
    sim_matrix = np.dot(normalized, normalized.T)
    
    # 4. Flag Pairs > 0.92
    for i in range(len(answer_ids)):
        for j in range(i + 1, len(answer_ids)):
            sim = float(sim_matrix[i, j])
            if sim > 0.92:
                # Get question_id (assume same question for simplicity or filter earlier)
                ans_a = db.query(models.Answer).get(answer_ids[i])
                ans_b = db.query(models.Answer).get(answer_ids[j])
                
                if ans_a.question_id == ans_b.question_id:
                    flag = models.PlagiarismFlag(
                        exam_id=exam_id,
                        question_id=ans_a.question_id,
                        answer_ids_json=[ans_a.id, ans_b.id],
                        similarity=sim
                    )
                    db.add(flag)
    
    db.commit()
    logger.info(f"Plagiarism check complete for Exam {exam_id}")
