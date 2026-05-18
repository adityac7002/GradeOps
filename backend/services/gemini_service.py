"""
Gemini VLM service — production hardened.

Changes from previous version:
- GeminiService is NOT a module-level singleton; instantiated lazily
- Missing API key raises ExternalServiceError, not ImportError on startup
- Retry logic with exponential backoff
- Structured return types instead of raw dicts
- Proper exception propagation with typed errors
"""
import logging
import time
from typing import Optional, TypedDict

from backend.config import get_settings
from backend.exceptions import ExternalServiceError, OCRError
from backend.core.logging import get_logger

logger = get_logger("services.gemini")


class ExtractionResult(TypedDict):
    transcription: str
    legibility: str          # high | medium | low
    answer_quality: str      # complete | partial | blank
    confidence: float


class GeminiService:
    """Wrapper around the Google GenAI SDK for VLM-based answer extraction."""

    def __init__(self):
        settings = get_settings()
        if not settings.GOOGLE_API_KEY:
            raise ExternalServiceError(
                "Gemini API",
                "GOOGLE_API_KEY is not configured. "
                "Set it in .env or switch OCR_MODEL to 'trocr' in settings."
            )
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.GOOGLE_API_KEY)
            self._model = genai.GenerativeModel("gemini-2.0-flash")
        except ImportError:
            raise ExternalServiceError(
                "Gemini SDK",
                "google-generativeai package is not installed. Run: pip install google-generativeai"
            )

    def extract_answer(
        self,
        image_path: str,
        question_context: str = "",
        max_retries: int = 3,
    ) -> ExtractionResult:
        """
        Extract handwritten answer text from an image.

        Args:
            image_path: Path to the cropped answer image (PNG/JPEG)
            question_context: The question text for contextual OCR
            max_retries: Number of retry attempts on transient failures

        Returns:
            ExtractionResult with transcription and quality metadata

        Raises:
            OCRError: If extraction fails after all retries
        """
        import google.generativeai as genai
        import PIL.Image

        prompt = self._build_extraction_prompt(question_context)

        for attempt in range(1, max_retries + 1):
            try:
                image = PIL.Image.open(image_path)
                response = self._model.generate_content(
                    [prompt, image],
                    generation_config={"response_mime_type": "application/json"},
                )

                import json
                raw = response.text.strip()
                # Strip markdown code fences if present
                if raw.startswith("```"):
                    raw = raw.split("```")[1]
                    if raw.startswith("json"):
                        raw = raw[4:]
                data = json.loads(raw)

                return ExtractionResult(
                    transcription=str(data.get("transcription", "")).strip(),
                    legibility=data.get("legibility", "medium"),
                    answer_quality=data.get("answer_quality", "partial"),
                    confidence=float(data.get("confidence", 0.7)),
                )

            except Exception as e:
                if attempt == max_retries:
                    logger.error(
                        "Gemini extraction failed for %s after %d attempts: %s",
                        image_path, max_retries, e
                    )
                    raise OCRError(f"Gemini extraction failed: {e}") from e

                wait = 2 ** attempt
                logger.warning(
                    "Gemini extraction attempt %d/%d failed for %s, retrying in %ds: %s",
                    attempt, max_retries, image_path, wait, e
                )
                time.sleep(wait)

        # Unreachable but satisfies type checker
        raise OCRError("Extraction exhausted all retries.")

    def _build_extraction_prompt(self, question_context: str) -> str:
        context_line = f'The question being answered is: "{question_context}"' if question_context else ""
        return f"""You are an expert handwriting OCR system specialized in academic exam papers.

{context_line}

Carefully transcribe exactly what is written in this handwritten student answer image.

Return a JSON object with these fields:
{{
  "transcription": "<exact text as written, preserving math notation>",
  "legibility": "<high|medium|low>",
  "answer_quality": "<complete|partial|blank>",
  "confidence": <0.0 to 1.0>
}}

Rules:
- Transcribe EXACTLY what is written, including errors
- Do NOT correct spelling or grammar
- For math: use LaTeX notation where clear (e.g. x^2, \\frac{{a}}{{b}})
- If truly illegible, set transcription to "[illegible]" and legibility to "low"
- If blank, set transcription to "" and answer_quality to "blank"
"""
