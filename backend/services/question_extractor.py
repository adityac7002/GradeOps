"""
Question Paper Extractor — GradeOps

Given a question paper PDF, this service:
1. Renders each page as an image
2. Feeds each page to Qwen2-VL with a structured extraction prompt
3. Returns a list of ExtractedQuestion objects with:
   - question number
   - full question text / prompt
   - any given data (formulas, tables, reference values)
   - total marks
   - suggested rubric items (auto-generated, fully editable)

Falls back to a regex-based TrOCR approach if Qwen is not available.
"""
import json
import logging
import os
import re
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF
from PIL import Image

logger = logging.getLogger(__name__)

_LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
_OCR_MODEL    = os.getenv("OCR_MODEL", "qwen2-vl")


# ── Page rendering ─────────────────────────────────────────────────────────────

def _render_pages(pdf_path: str, dpi: int = 150) -> list[Image.Image]:
    """Render all pages of a PDF as PIL Images."""
    doc = fitz.open(pdf_path)
    scale = dpi / 72
    mat = fitz.Matrix(scale, scale)
    pages = []
    for page in doc:
        pix = page.get_pixmap(matrix=mat)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        pages.append(img)
    doc.close()
    return pages


# ── Qwen2-VL extraction ────────────────────────────────────────────────────────

_QP_PROMPT = """\
This is a page from an exam question paper.

Extract ALL questions visible on this page. For each question output a JSON object.
Return a JSON array (may be empty [] if no questions on this page).

Each object must have:
- "number": question number as integer (use sub-question like 1 for Q1, Q1a etc.)
- "prompt": full question text exactly as written, including all sub-parts
- "given_data": any formulas, tables, or reference data given IN the question (null if none)
- "marks": total marks for this question as a number
- "rubric_items": array of suggested marking criteria, each with:
    - "description": what the student must demonstrate
    - "points": marks for this criterion
    - "keywords": 2-4 key terms that indicate this criterion is met

Respond ONLY with a valid JSON array. No markdown, no explanation."""


def _extract_with_qwen(pages: list[Image.Image]) -> list[dict]:
    """Use Qwen2-VL to extract questions from each page."""
    from backend.services.ocr import _load_qwen

    processor, model = _load_qwen()
    all_questions: list[dict] = []
    seen_numbers: set[int] = set()

    for page_num, page_img in enumerate(pages):
        # Resize to 1280px max
        w, h = page_img.size
        scale = min(1280 / max(w, h), 1.0)
        if scale < 1.0:
            page_img = page_img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": page_img},
                    {"type": "text", "text": _QP_PROMPT},
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
            inputs = processor(text=[text_input], images=[page_img], return_tensors="pt")

        import torch
        device = next(model.parameters()).device
        inputs = {k: v.to(device) if isinstance(v, torch.Tensor) else v for k, v in inputs.items()}

        generated_ids = model.generate(**inputs, max_new_tokens=1024, do_sample=False)
        generated_ids_trimmed = [
            out[len(inp):] for inp, out in zip(inputs["input_ids"], generated_ids)
        ]
        raw = processor.batch_decode(
            generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
        )[0].strip()

        # Strip markdown fences
        raw_json = raw.strip("` \n")
        if raw_json.startswith("json"):
            raw_json = raw_json[4:].strip()

        try:
            page_questions = json.loads(raw_json)
            if not isinstance(page_questions, list):
                page_questions = [page_questions]
            for q in page_questions:
                n = int(q.get("number", 0))
                if n > 0 and n not in seen_numbers:
                    seen_numbers.add(n)
                    all_questions.append(q)
        except json.JSONDecodeError as e:
            logger.warning("[QP] Page %d JSON parse error: %s | raw: %s", page_num + 1, e, raw[:200])

    return all_questions


# ── LLM text extraction fallback ───────────────────────────────────────────────

_TEXT_EXTRACT_PROMPT = """\
Below is OCR text from an exam question paper.

Extract all questions as a JSON array. Each object:
{{
  "number": <int>,
  "prompt": "<full question text>",
  "given_data": "<any given formulas/data or null>",
  "marks": <int>,
  "rubric_items": [
    {{"description": "<criterion>", "points": <float>, "keywords": ["<kw1>","<kw2>"]}}
  ]
}}

OCR Text:
\"\"\"
{ocr_text}
\"\"\"

Respond ONLY with a valid JSON array."""


def _extract_with_llm(ocr_text: str) -> list[dict]:
    """Use Ollama/OpenAI to extract questions from OCR text."""
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import JsonOutputParser

    if _LLM_PROVIDER == "openai":
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    elif _LLM_PROVIDER == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0)
    else:
        from langchain_ollama import ChatOllama
        llm = ChatOllama(model=_OLLAMA_MODEL, temperature=0)

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an exam question parser. Always respond with valid JSON only."),
        ("human", _TEXT_EXTRACT_PROMPT),
    ])
    chain = prompt | llm | JsonOutputParser()
    result = chain.invoke({"ocr_text": ocr_text[:4000]})
    return result if isinstance(result, list) else [result]


def _extract_with_trocr(pages: list[Image.Image]) -> list[dict]:
    """TrOCR + LLM fallback for when Qwen is unavailable."""
    from backend.services.ocr import _trocr_ocr
    full_text = "\n".join(_trocr_ocr(page) for page in pages)
    logger.info("[QP] Extracted %d chars via TrOCR, sending to LLM...", len(full_text))
    return _extract_with_llm(full_text)


# ── Schema normalisation ───────────────────────────────────────────────────────

def _normalize(raw_questions: list[dict]) -> list[dict]:
    """
    Normalize extracted question data into a consistent schema.
    Fills defaults, validates mark totals, de-duplicates.
    """
    seen: set[int] = set()
    result = []
    for q in sorted(raw_questions, key=lambda x: int(x.get("number", 0))):
        n = int(q.get("number", 0))
        if n == 0 or n in seen:
            continue
        seen.add(n)

        marks = float(q.get("marks", q.get("max_points", 10)))

        # Normalize rubric items
        rubric_items = []
        for ri in q.get("rubric_items", []):
            rubric_items.append({
                "description": ri.get("description", ""),
                "points": float(ri.get("points", 0)),
                "keywords": ri.get("keywords", []),
            })

        # If rubric items don't add up, rescale or add a catch-all
        total_ri = sum(r["points"] for r in rubric_items)
        if rubric_items and abs(total_ri - marks) > 0.5:
            scale = marks / total_ri if total_ri > 0 else 1
            for ri in rubric_items:
                ri["points"] = round(ri["points"] * scale, 1)

        if not rubric_items:
            rubric_items = [{"description": "Complete and correct answer", "points": marks, "keywords": []}]

        result.append({
            "number": n,
            "prompt": q.get("prompt", "").strip(),
            "given_data": q.get("given_data") or None,
            "max_points": marks,
            "rubric_items": rubric_items,
        })

    return result


# ── Public entry point ─────────────────────────────────────────────────────────

def extract_questions_from_paper(pdf_path: str) -> list[dict]:
    """
    Extract all questions from a question paper PDF.

    Returns a list of dicts:
    [
      {
        "number": 1,
        "prompt": "Using Euler's method...",
        "given_data": "h = 0.5, y(0) = 1",
        "max_points": 10.0,
        "rubric_items": [
          {"description": "Correct setup", "points": 4, "keywords": ["Euler", "step"]},
          ...
        ]
      },
      ...
    ]
    """
    logger.info("[QP] Extracting questions from %s", pdf_path)
    pages = _render_pages(pdf_path)
    logger.info("[QP] Rendered %d pages", len(pages))

    raw: list[dict] = []

    if _OCR_MODEL == "qwen2-vl":
        try:
            raw = _extract_with_qwen(pages)
            logger.info("[QP] Qwen extracted %d raw questions", len(raw))
        except Exception as e:
            logger.warning("[QP] Qwen failed (%s), falling back to TrOCR+LLM", e)
            raw = _extract_with_trocr(pages)
    else:
        raw = _extract_with_trocr(pages)

    normalized = _normalize(raw)
    logger.info("[QP] Final: %d questions extracted", len(normalized))
    return normalized
