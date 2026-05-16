"""
OCR service for GradeOps — Qwen2-VL-2B primary, TrOCR fallback.

Qwen2-VL-2B (Qwen/Qwen2-VL-2B-Instruct) is a multimodal vision-language
model that understands complex handwritten exam pages including:
  - Mathematical formulas and expressions
  - Tables and multi-column layouts
  - Mixed handwriting + printed text
  - Diagrams with annotations

TrOCR is kept as a lightweight fallback for when Qwen is not downloaded.

Usage:
  OCR_MODEL=qwen2-vl   (default, best accuracy)
  OCR_MODEL=trocr      (fast, needs good single-line images)
"""
import os
import logging
import base64
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps
import numpy as np

logger = logging.getLogger(__name__)

_OCR_MODEL = os.getenv("OCR_MODEL", "qwen2-vl")

# Lazy-loaded singletons
_qwen_processor = None
_qwen_model = None
_trocr_processor = None
_trocr_model = None


# ── Qwen2-VL loader ────────────────────────────────────────────────────────────

def _load_qwen():
    global _qwen_processor, _qwen_model
    if _qwen_processor is not None:
        return _qwen_processor, _qwen_model

    from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
    model_id = "Qwen/Qwen2-VL-2B-Instruct"
    logger.info("[OCR] Loading %s...", model_id)

    _qwen_processor = AutoProcessor.from_pretrained(model_id)

    import torch
    if torch.backends.mps.is_available():
        device = torch.device("mps")
        _qwen_model = Qwen2VLForConditionalGeneration.from_pretrained(
            model_id, torch_dtype=torch.float16
        ).to(device)
        logger.info("[OCR] Qwen2-VL-2B loaded on MPS (Apple GPU).")
    else:
        _qwen_model = Qwen2VLForConditionalGeneration.from_pretrained(
            model_id, torch_dtype="auto", device_map="auto"
        )
        logger.info("[OCR] Qwen2-VL-2B loaded on CPU.")

    return _qwen_processor, _qwen_model


# ── TrOCR loader (fallback) ────────────────────────────────────────────────────

def _load_trocr():
    global _trocr_processor, _trocr_model
    if _trocr_processor is not None:
        return _trocr_processor, _trocr_model

    from transformers import TrOCRProcessor, VisionEncoderDecoderModel
    for model_id in [
        os.getenv("TROCR_MODEL", "microsoft/trocr-large-handwritten"),
        "microsoft/trocr-base-handwritten",
    ]:
        try:
            logger.info("[OCR] Loading TrOCR: %s (local only)...", model_id)
            _trocr_processor = TrOCRProcessor.from_pretrained(model_id, local_files_only=True)
            _trocr_model = VisionEncoderDecoderModel.from_pretrained(model_id, local_files_only=True)
            logger.info("[OCR] TrOCR loaded: %s", model_id)
            return _trocr_processor, _trocr_model
        except Exception as e:
            logger.warning("[OCR] %s not cached: %s", model_id, e)
            _trocr_processor = None
            _trocr_model = None

    raise RuntimeError("No TrOCR model cached. Download trocr-base-handwritten first.")


# ── Qwen2-VL inference ─────────────────────────────────────────────────────────

def _qwen_ocr(image: Image.Image) -> str:
    """
    Use Qwen2-VL to transcribe all handwritten content from an exam page.
    Returns a plain-text transcript preserving mathematical notation.
    """
    processor, model = _load_qwen()

    # Resize to max 1280px on longest side (Qwen2-VL sweet spot)
    max_side = 1280
    w, h = image.size
    scale = min(max_side / max(w, h), 1.0)
    if scale < 1.0:
        image = image.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {
                    "type": "text",
                    "text": (
                        "OCR the text in this image. Include all handwritten text, "
                        "mathematical expressions, equations, table values, and "
                        "numerical calculations. Output the transcription only."
                    ),
                },
            ],
        }
    ]

    text_input = processor.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )

    # Process with vision inputs
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
        # Fallback without qwen_vl_utils
        inputs = processor(
            text=[text_input],
            images=[image],
            return_tensors="pt",
        )

    import torch
    device = next(model.parameters()).device
    inputs = {k: v.to(device) if isinstance(v, torch.Tensor) else v for k, v in inputs.items()}

    generated_ids = model.generate(
        **inputs,
        max_new_tokens=512,
        do_sample=False,
    )
    # Strip the prompt tokens
    generated_ids_trimmed = [
        out[len(inp):]
        for inp, out in zip(inputs["input_ids"], generated_ids)
    ]
    output = processor.batch_decode(
        generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
    )[0]
    return output.strip()


# ── TrOCR inference (fallback) ─────────────────────────────────────────────────

def _trocr_ocr(image: Image.Image) -> str:
    """
    TrOCR fallback: horizontal-projection line segmentation + batch inference.
    Works best for simple single-column handwriting.
    """
    processor, model = _load_trocr()

    gray = image.convert("L")
    gray = ImageOps.autocontrast(gray, cutoff=1)
    arr = np.array(gray, dtype=np.uint8)
    if arr.mean() < 128:
        arr = 255 - arr

    # Find text lines via horizontal projection
    ink = arr < 200
    row_sums = ink.sum(axis=1)

    in_line = False
    lines: list[tuple[int, int]] = []
    start = 0
    min_h = 12
    pad = 6

    for y, v in enumerate(row_sums):
        if not in_line and v > 2:
            in_line = True
            start = y
        elif in_line and v <= 2:
            in_line = False
            if (y - start) >= min_h:
                lines.append((max(0, start - pad), min(arr.shape[0], y + pad)))
    if in_line and (len(row_sums) - start) >= min_h:
        lines.append((max(0, start - pad), arr.shape[0]))

    if not lines:
        lines = [(0, arr.shape[0])]

    logger.info("[OCR] TrOCR: %d lines found.", len(lines))
    results: list[str] = []
    BATCH = 8

    for i in range(0, len(lines), BATCH):
        crops = []
        for y0, y1 in lines[i: i + BATCH]:
            crop = arr[y0:y1, :]
            if crop.shape[0] < 32:
                crop = np.pad(crop, ((0, 32 - crop.shape[0]), (0, 0)), constant_values=255)
            crops.append(Image.fromarray(crop).convert("RGB"))

        pixel_values = processor(images=crops, return_tensors="pt").pixel_values
        ids = model.generate(pixel_values, max_new_tokens=128)
        texts = processor.batch_decode(ids, skip_special_tokens=True)
        results.extend(t.strip() for t in texts if t.strip())

    return "\n".join(results)


# ── Public entry point ─────────────────────────────────────────────────────────

def run_ocr(image_path: str) -> str:
    """
    Transcribe all handwritten text from an image file.
    Uses Qwen2-VL-2B by default (best for complex exam pages),
    falls back to TrOCR if Qwen is not available.
    """
    image = Image.open(image_path).convert("RGB")

    if _OCR_MODEL == "trocr":
        return _trocr_ocr(image)

    # Default: Qwen2-VL
    try:
        return _qwen_ocr(image)
    except Exception as e:
        logger.warning("[OCR] Qwen2-VL failed (%s), falling back to TrOCR.", e)
        try:
            return _trocr_ocr(image)
        except Exception as e2:
            logger.error("[OCR] TrOCR also failed: %s", e2)
            return ""
