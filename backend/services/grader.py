"""
Core grading service — production refactor.

Canonical single implementation replacing the two parallel versions:
- services/grader.py (LangChain + Ollama)
- services/grading_agent.py (Gemini)

Design:
- Strategy pattern: provider selected at call time from settings
- All providers return the same GradingResult TypedDict
- Confidence is derived from rubric criteria coverage, not hardcoded
- Handles blank/illegible answers gracefully
"""
import logging
from typing import Optional, TypedDict

from backend.config import get_settings
from backend.core.logging import get_logger

logger = get_logger("services.grader")


class CriterionResult(TypedDict):
    criterion_id: str
    description: str
    marks_possible: float
    marks_awarded: float
    status: str          # met | partial | not_met
    reasoning: str


class GradingResult(TypedDict):
    grade: float
    max_marks: float
    justification: str
    rubric_breakdown: list[CriterionResult]
    confidence: float
    grading_mode: str    # gemini | ollama | openai | heuristic


def grade_answer(
    transcribed_text: str,
    rubric_items: list[dict],
    max_marks: float,
    image_path: Optional[str] = None,
    answer_key: Optional[str] = None,
) -> GradingResult:
    """
    Grade a student answer using the configured LLM provider.

    Args:
        transcribed_text: OCR-extracted student answer text
        rubric_items: List of {description, points, keywords} dicts
        max_marks: Maximum possible marks for this question
        image_path: Optional path to answer image (for vision grading)
        answer_key: Optional model answer for comparison

    Returns:
        GradingResult with score, breakdown, and justification
    """
    settings = get_settings()

    # Handle blank or illegible answers immediately
    if not transcribed_text or transcribed_text.strip() in ("", "[illegible]", "[blank]"):
        return _blank_result(max_marks, rubric_items)

    provider = settings.LLM_PROVIDER
    logger.info("Grading with provider=%s, max_marks=%.1f", provider, max_marks)

    try:
        if provider == "gemini":
            return _grade_with_gemini(transcribed_text, rubric_items, max_marks, image_path, answer_key)
        elif provider == "ollama":
            return _grade_with_ollama(transcribed_text, rubric_items, max_marks, answer_key)
        elif provider == "openai":
            return _grade_with_openai(transcribed_text, rubric_items, max_marks, answer_key)
        else:
            logger.warning("Unknown provider %s, falling back to heuristic", provider)
            return _heuristic_grade(transcribed_text, rubric_items, max_marks)
    except Exception as e:
        logger.error("Grading failed with provider %s: %s", provider, e)
        return _heuristic_grade(transcribed_text, rubric_items, max_marks)


# ── Provider implementations ─────────────────────────────────────────────────

def _grade_with_gemini(
    text: str,
    rubric_items: list[dict],
    max_marks: float,
    image_path: Optional[str],
    answer_key: Optional[str],
) -> GradingResult:
    """Grade using Gemini — supports multimodal (text + image)."""
    from backend.services.gemini_service import GeminiService
    import google.generativeai as genai
    import PIL.Image
    import json

    settings = get_settings()
    genai.configure(api_key=settings.GOOGLE_API_KEY)
    model = genai.GenerativeModel("gemini-2.0-flash")

    prompt = _build_grading_prompt(text, rubric_items, max_marks, answer_key)
    parts = [prompt]

    if image_path:
        try:
            parts.append(PIL.Image.open(image_path))
        except Exception:
            pass

    response = model.generate_content(
        parts,
        generation_config={"response_mime_type": "application/json"},
    )
    return _parse_grading_response(response.text, rubric_items, max_marks, "gemini")


def _grade_with_ollama(
    text: str,
    rubric_items: list[dict],
    max_marks: float,
    answer_key: Optional[str],
) -> GradingResult:
    """Grade using locally hosted Ollama."""
    import requests
    import json

    settings = get_settings()
    prompt = _build_grading_prompt(text, rubric_items, max_marks, answer_key)

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": settings.OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        },
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    return _parse_grading_response(data.get("response", "{}"), rubric_items, max_marks, "ollama")


def _grade_with_openai(
    text: str,
    rubric_items: list[dict],
    max_marks: float,
    answer_key: Optional[str],
) -> GradingResult:
    """Grade using OpenAI GPT-4o."""
    from openai import OpenAI
    import json

    settings = get_settings()
    client = OpenAI(api_key=settings.GOOGLE_API_KEY)  # Uses OPENAI_API_KEY if settings added

    prompt = _build_grading_prompt(text, rubric_items, max_marks, answer_key)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a strict but fair academic examiner. Return only JSON."},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
    )
    return _parse_grading_response(response.choices[0].message.content, rubric_items, max_marks, "openai")


# ── Prompt builder ───────────────────────────────────────────────────────────

def _build_grading_prompt(
    text: str,
    rubric_items: list[dict],
    max_marks: float,
    answer_key: Optional[str],
) -> str:
    rubric_str = "\n".join(
        f"  - Criterion {i+1}: {item['description']} [{item['points']} marks]"
        f"{' | Keywords: ' + ', '.join(item['keywords']) if item.get('keywords') else ''}"
        for i, item in enumerate(rubric_items)
    )
    answer_key_str = f"\nModel Answer:\n{answer_key}" if answer_key else ""

    return f"""You are a strict but fair academic examiner grading a student's handwritten answer.

STUDENT ANSWER:
{text}
{answer_key_str}

RUBRIC (Total: {max_marks} marks):
{rubric_str}

Evaluate the student's answer against each criterion. Return a JSON object:
{{
  "total_score": <float, 0 to {max_marks}>,
  "justification": "<one paragraph explanation>",
  "criteria_evaluations": [
    {{
      "criterion_index": <int, 0-based>,
      "marks_awarded": <float>,
      "status": "<met|partial|not_met>",
      "reasoning": "<one sentence>"
    }}
  ]
}}

Rules:
- Be strict but fair — partial credit only where criteria explicitly allows it
- Total score must equal the sum of marks_awarded across all criteria
- Total score cannot exceed {max_marks}
- Base evaluation on actual content, not word count
"""


def _parse_grading_response(
    raw: str,
    rubric_items: list[dict],
    max_marks: float,
    mode: str,
) -> GradingResult:
    """Parse LLM JSON response into typed GradingResult."""
    import json

    # Strip markdown fences
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        parts = cleaned.split("```")
        cleaned = parts[1].lstrip("json").strip() if len(parts) > 1 else cleaned

    data = json.loads(cleaned)

    raw_score = float(data.get("total_score", 0))
    score = max(0.0, min(raw_score, max_marks))

    criteria_evals = data.get("criteria_evaluations", [])
    breakdown: list[CriterionResult] = []

    for i, item in enumerate(rubric_items):
        eval_data = next((e for e in criteria_evals if e.get("criterion_index") == i), {})
        awarded = float(eval_data.get("marks_awarded", 0))
        awarded = max(0.0, min(awarded, item["points"]))
        breakdown.append(CriterionResult(
            criterion_id=f"c{i+1}",
            description=item["description"],
            marks_possible=item["points"],
            marks_awarded=awarded,
            status=eval_data.get("status", "not_met"),
            reasoning=eval_data.get("reasoning", ""),
        ))

    # Confidence: ratio of criteria evaluated vs total
    criteria_with_reasoning = sum(1 for b in breakdown if b["reasoning"])
    confidence = criteria_with_reasoning / len(rubric_items) if rubric_items else 0.5

    return GradingResult(
        grade=score,
        max_marks=max_marks,
        justification=data.get("justification", ""),
        rubric_breakdown=breakdown,
        confidence=round(confidence, 2),
        grading_mode=mode,
    )


# ── Fallbacks ────────────────────────────────────────────────────────────────

def _blank_result(max_marks: float, rubric_items: list[dict]) -> GradingResult:
    """Return a zero score for blank/illegible answers."""
    breakdown = [
        CriterionResult(
            criterion_id=f"c{i+1}",
            description=item["description"],
            marks_possible=item["points"],
            marks_awarded=0.0,
            status="not_met",
            reasoning="Answer was blank or illegible.",
        )
        for i, item in enumerate(rubric_items)
    ]
    return GradingResult(
        grade=0.0,
        max_marks=max_marks,
        justification="Answer was blank or could not be read.",
        rubric_breakdown=breakdown,
        confidence=1.0,
        grading_mode="heuristic",
    )


def _heuristic_grade(text: str, rubric_items: list[dict], max_marks: float) -> GradingResult:
    """
    Keyword-matching fallback when all LLM providers fail.
    Preserves grading continuity — marks as low-confidence.
    """
    text_lower = text.lower()
    breakdown: list[CriterionResult] = []
    total = 0.0

    for i, item in enumerate(rubric_items):
        keywords = [k.lower() for k in item.get("keywords", [])]
        matched = [k for k in keywords if k in text_lower]
        ratio = len(matched) / len(keywords) if keywords else 0.0
        awarded = round(item["points"] * ratio, 1)
        total += awarded
        breakdown.append(CriterionResult(
            criterion_id=f"c{i+1}",
            description=item["description"],
            marks_possible=item["points"],
            marks_awarded=awarded,
            status="met" if ratio >= 0.8 else "partial" if ratio > 0 else "not_met",
            reasoning=f"Keyword matching: {len(matched)}/{len(keywords)} keywords found.",
        ))

    return GradingResult(
        grade=min(total, max_marks),
        max_marks=max_marks,
        justification="Graded by keyword heuristic (LLM unavailable). Manual review recommended.",
        rubric_breakdown=breakdown,
        confidence=0.3,
        grading_mode="heuristic",
    )
