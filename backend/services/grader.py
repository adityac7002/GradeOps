"""
Agentic grading service for GradeOps.

Two modes depending on what's available:

1. **Vision grading** (best quality):
   - Qwen2-VL looks at the answer image directly
   - Grades against the rubric in a single forward pass
   - No OCR errors or lost context

2. **Text grading** (fallback):
   - Works on OCR transcript
   - Uses LangChain + Ollama / OpenAI / Gemini

Mode is selected automatically:
  - If OCR_MODEL=qwen2-vl AND the image path is available → vision grading
  - Otherwise → text grading via LangChain

LLM provider for text grading is configured via LLM_PROVIDER env var:
  - ollama  (default, local)
  - openai
  - gemini
"""
import os
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

_LLM_PROVIDER  = os.getenv("LLM_PROVIDER", "ollama")
_OLLAMA_MODEL  = os.getenv("OLLAMA_MODEL", "llama3.2")
_OCR_MODEL     = os.getenv("OCR_MODEL", "qwen2-vl")

# Lazy singletons
_llm = None


# ── LangChain LLM loader ───────────────────────────────────────────────────────

def _get_llm():
    global _llm
    if _llm is not None:
        return _llm

    if _LLM_PROVIDER == "openai":
        from langchain_openai import ChatOpenAI
        _llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    elif _LLM_PROVIDER == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        _llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0)
    else:  # ollama
        from langchain_ollama import ChatOllama
        _llm = ChatOllama(model=_OLLAMA_MODEL, temperature=0)

    return _llm


# ── Rubric formatter ───────────────────────────────────────────────────────────

def _format_rubric(rubric_items: list[dict]) -> str:
    lines = []
    for i, item in enumerate(rubric_items, 1):
        kw = ", ".join(item.get("keywords") or [])
        kw_str = f" [keywords: {kw}]" if kw else ""
        lines.append(f"  {i}. {item['description']} ({item['points']} pts){kw_str}")
    return "\n".join(lines)


_JSON_SCHEMA = """{
  "grade": <float 0 to max_points>,
  "justification": "<1-3 sentence explanation>",
  "rubric_breakdown": [
    {"item": "<criterion>", "awarded": <float>, "max": <float>, "reason": "<brief>"}
  ]
}"""


# ── Vision grading via Qwen2-VL ────────────────────────────────────────────────

def _grade_with_vision(
    image_path: str,
    rubric_items: list[dict],
    max_points: float,
    question_prompt: str | None = None,
    given_data: str | None = None,
) -> dict[str, Any]:
    """
    Feed the answer image directly to Qwen2-VL with the rubric.
    Bypasses OCR entirely — the VLM sees the handwriting as-is.
    """
    from PIL import Image
    from backend.services.ocr import _load_qwen

    processor, model = _load_qwen()

    image = Image.open(image_path).convert("RGB")
    # Resize to 1280px max side
    w, h = image.size
    scale = min(1280 / max(w, h), 1.0)
    if scale < 1.0:
        image = image.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    rubric_text = _format_rubric(rubric_items)

    question_context = ""
    if question_prompt:
        question_context = f"The question asked:\n\"\"\"{question_prompt}\"\"\""
        if given_data:
            question_context += f"\n\nGiven data / formulas:\n{given_data}"
        question_context += "\n\n"

    prompt = (
        f"You are an expert exam grader. Grade this handwritten student answer.\n\n"
        f"{question_context}"
        f"Rubric (max {max_points} pts total):\n{rubric_text}\n\n"
        f"Instructions:\n"
        f"- Read ALL handwriting carefully, including formulas, tables, and calculations.\n"
        f"- Use the question context to judge if the student understood what was asked.\n"
        f"- Award partial credit where partial understanding is shown.\n"
        f"- Grade must be between 0 and {max_points}.\n"
        f"- Respond ONLY with valid JSON, no markdown, no extra text.\n\n"
        f"JSON format:\n{_JSON_SCHEMA}"
    )

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": prompt},
            ],
        }
    ]

    text_input = processor.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )

    try:
        from qwen_vl_utils import process_vision_info
        image_inputs, video_inputs = process_vision_info(messages)
        inputs = processor(
            text=[text_input],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt",
        )
    except ImportError:
        inputs = processor(text=[text_input], images=[image], return_tensors="pt")

    import torch
    device = next(model.parameters()).device
    inputs = {k: v.to(device) if isinstance(v, torch.Tensor) else v for k, v in inputs.items()}

    generated_ids = model.generate(**inputs, max_new_tokens=512, do_sample=False)
    generated_ids_trimmed = [
        out[len(inp):] for inp, out in zip(inputs["input_ids"], generated_ids)
    ]
    raw = processor.batch_decode(
        generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
    )[0].strip()

    # Parse JSON — strip any markdown fences
    raw_json = raw.strip("` \n")
    if raw_json.startswith("json"):
        raw_json = raw_json[4:].strip()

    result = json.loads(raw_json)
    grade = float(result.get("grade", 0))
    grade = max(0.0, min(float(max_points), grade))
    return {
        "grade": round(grade, 2),
        "justification": result.get("justification", ""),
        "rubric_breakdown": result.get("rubric_breakdown", []),
    }


# ── Text grading via LangChain ─────────────────────────────────────────────────

_GRADE_PROMPT_TEMPLATE = """\
You are an expert exam grader. Evaluate this student answer against the rubric.

{question_context}Student answer (transcribed):
\"\"\"
{ocr_text}
\"\"\"

Rubric (max {max_points} pts total):
{rubric_text}

Rules:
- Grade strictly based on the rubric.
- Use the question context (if provided) to judge correctness.
- Award partial credit where partial understanding is demonstrated.
- Grade must be between 0 and {max_points}.
- Respond ONLY with valid JSON, no markdown, no extra text.

JSON format:
{schema}"""


def _grade_with_text(
    ocr_text: str,
    rubric_items: list[dict],
    max_points: float,
    question_prompt: str | None = None,
    given_data: str | None = None,
    retries: int = 3,
) -> dict[str, Any]:
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import JsonOutputParser

    llm = _get_llm()
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert exam grader. Always respond with valid JSON only."),
        ("human", _GRADE_PROMPT_TEMPLATE),
    ])
    chain = prompt | llm | JsonOutputParser()

    rubric_text = _format_rubric(rubric_items)
    question_context = ""
    if question_prompt:
        question_context = f"The question asked:\n\"\"\"{question_prompt}\"\"\""
        if given_data:
            question_context += f"\n\nGiven data / formulas:\n{given_data}"
        question_context = question_context + "\n\n"

    last_err = None
    for attempt in range(retries):
        try:
            result = chain.invoke({
                "ocr_text": ocr_text,
                "rubric_text": rubric_text,
                "max_points": max_points,
                "schema": _JSON_SCHEMA,
                "question_context": question_context,
            })
            grade = float(result.get("grade", 0))
            grade = max(0.0, min(float(max_points), grade))
            return {
                "grade": round(grade, 2),
                "justification": result.get("justification", ""),
                "rubric_breakdown": result.get("rubric_breakdown", []),
            }
        except Exception as e:
            last_err = e
            logger.warning("[Grader] Attempt %d/%d failed: %s", attempt + 1, retries, e)

    return {
        "grade": 0.0,
        "justification": f"Grading failed after {retries} attempts: {last_err}",
        "rubric_breakdown": [],
    }


# ── Public entry point ─────────────────────────────────────────────────────────

def grade_answer(
    ocr_text: str,
    rubric_items: list[dict],
    max_points: float,
    image_path: str | None = None,
    question_prompt: str | None = None,
    given_data: str | None = None,
    retries: int = 3,
) -> dict[str, Any]:
    """
    Grade a student answer.

    If Qwen2-VL is configured AND an image_path is provided,
    uses vision grading (feeds image + rubric + question directly to VLM).
    Otherwise falls back to text-based grading via LangChain + Ollama.

    Args:
        ocr_text:        Transcribed answer text (used for text-mode fallback)
        rubric_items:    List of {description, points, keywords} dicts
        max_points:      Maximum score for this question
        image_path:      Path to the cropped answer image (enables vision grading)
        question_prompt: Full question text from the question paper
        given_data:      Any given formulas/data from the question paper
        retries:         Number of retry attempts on JSON parse error

    Returns: {grade, justification, rubric_breakdown}
    """
    # Try vision grading first (most accurate)
    if _OCR_MODEL == "qwen2-vl" and image_path:
        for attempt in range(retries):
            try:
                logger.info("[Grader] Vision grading attempt %d/%d", attempt + 1, retries)
                return _grade_with_vision(
                    image_path, rubric_items, max_points,
                    question_prompt=question_prompt,
                    given_data=given_data,
                )
            except json.JSONDecodeError as e:
                logger.warning("[Grader] JSON parse error attempt %d: %s", attempt + 1, e)
            except Exception as e:
                logger.warning("[Grader] Vision grading failed attempt %d: %s", attempt + 1, e)
                break  # Qwen not available, fall through

    # Text grading fallback
    if not ocr_text or not ocr_text.strip():
        logger.warning("[Grader] No OCR text and vision grading unavailable — returning 0.")
        return {
            "grade": 0.0,
            "justification": "Could not extract text from answer image.",
            "rubric_breakdown": [],
        }

    return _grade_with_text(
        ocr_text, rubric_items, max_points,
        question_prompt=question_prompt,
        given_data=given_data,
        retries=retries,
    )
