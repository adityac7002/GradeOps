import logging
import json
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from google.genai import types
from backend.db import models
from backend.services.gemini_service import gemini

logger = logging.getLogger(__name__)

class GradingAgent:
    def __init__(self, db: Session):
        self.db = db

    def run_pipeline(self, answer_id: int):
        """
        Full grading pipeline for a single answer.
        load_context -> evaluate_criteria -> compute_score -> generate_justification -> persist
        """
        # 1. Load Context
        context = self._load_context(answer_id)
        if not context:
            return

        # 2. Evaluate each criterion (Fan-out)
        evaluations = self._evaluate_criteria(context)

        # 3. Compute Score (Pure Python)
        ai_score, ai_breakdown = self._compute_score(evaluations, context["max_marks"])

        # 4. Generate Justification
        justification = self._generate_justification(evaluations)

        # 5. Persist Grade
        self._persist_grade(answer_id, ai_score, ai_breakdown, justification)

    def _load_context(self, answer_id: int) -> Dict[str, Any]:
        ans = self.db.query(models.Answer).filter(models.Answer.id == answer_id).first()
        if not ans:
            return None

        exam = ans.submission.exam
        rubric = exam.rubric_json or {}
        # Find the specific question meta in rubric
        q_meta = next((q for q in rubric.get("questions", []) if q["number"] == ans.question.number), {})
        
        return {
            "answer_text": ans.transcribed_text,
            "image_path": ans.crop_path,
            "max_marks": ans.question.max_marks,
            "criteria": q_meta.get("criteria", []),
            "answer_key": q_meta.get("answer_key", ""),
            "common_deductions": q_meta.get("common_deductions", [])
        }

    def _evaluate_criteria(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Evaluate each criterion. In a true production environment, 
        this would fan out to multiple parallel LLM calls.
        For now, we'll use a single structured call that evaluates all criteria 
        at once to save tokens and time while maintaining the multimodal context.
        """
        results = []
        
        criteria_list = context["criteria"]
        if not criteria_list:
            return []

        prompt = f"""
        Evaluate the student's answer against these criteria.
        
        Student Transcription:
        \"\"\"{context["answer_text"]}\"\"\"
        
        Reference Solution:
        \"\"\"{context["answer_key"]}\"\"\"
        
        Criteria (Pay strict attention to the maximum marks per criterion):
        {json.dumps(criteria_list, indent=2)}
        
        CRITICAL RULES:
        1. 'marks_awarded' MUST NOT exceed the maximum points allowed for that specific criterion.
        2. If 'status' is 'not_met', marks_awarded must be 0.
        3. If 'status' is 'partial', marks_awarded must be strictly greater than 0 but less than the maximum points.
        
        Return a list of evaluations, one for each criterion ID.
        For each evaluation, provide:
        - status: "met" | "partial" | "not_met"
        - marks_awarded: float
        - evidence: quote from the student's work
        - reasoning: brief explanation
        """

        # Gemini Multimodal Call
        with open(context["image_path"], "rb") as f:
            image_data = f.read()

        try:
            # We use the same gemini service but with a custom schema for the list of criteria
            response = gemini.client.models.generate_content(
                model=gemini.model_id,
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_bytes(data=image_data, mime_type="image/png"),
                            types.Part.from_text(text=prompt)
                        ]
                    )
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    # Schema for a list of criterion evaluations
                    response_schema={
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "criterion_id": {"type": "string"},
                                "status": {"type": "string", "enum": ["met", "partial", "not_met"]},
                                "marks_awarded": {"type": "number"},
                                "evidence": {"type": "string"},
                                "reasoning": {"type": "string"}
                            },
                            "required": ["criterion_id", "status", "marks_awarded", "evidence", "reasoning"]
                        }
                    }
                ),
            )
            return response.parsed
        except Exception as e:
            logger.error(f"Criteria evaluation failed: {e}")
            return []

    def _compute_score(self, evaluations: List[Dict[str, Any]], max_marks: float) -> Tuple[float, Dict[str, Any]]:
        """Pure Python scoring logic."""
        total = sum(e["marks_awarded"] for e in evaluations)
        total = max(0.0, min(max_marks, total))
        
        breakdown = {
            "criteria_evals": evaluations,
            "raw_total": total
        }
        return total, breakdown

    def _generate_justification(self, evaluations: List[Dict[str, Any]]) -> str:
        """Concise summary for TA review."""
        if not evaluations:
            return "No criteria evaluated."
        
        met = [e["reasoning"] for e in evaluations if e["status"] == "met"]
        partial = [e["reasoning"] for e in evaluations if e["status"] == "partial"]
        not_met = [e["reasoning"] for e in evaluations if e["status"] == "not_met"]

        summary = []
        if met:
            summary.append(f"Successfully {met[0].lower()}")
        if partial:
            summary.append(f"Partially {partial[0].lower()}")
        if not_met:
            summary.append(f"Missed {not_met[0].lower()}")
            
        return ". ".join(summary) + "."

    def _persist_grade(self, answer_id: int, score: float, breakdown: Dict[str, Any], justification: str):
        grade = self.db.query(models.Grade).filter(models.Grade.answer_id == answer_id).first()
        if not grade:
            grade = models.Grade(answer_id=answer_id)
            self.db.add(grade)
        
        grade.ai_score = score
        grade.ai_breakdown_json = breakdown
        grade.ai_justification = justification
        grade.ai_confidence = 0.9 # Heuristic
        grade.status = "graded"
        grade.final_score = score
        
        self.db.commit()
