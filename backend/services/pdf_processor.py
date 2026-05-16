"""
PDF → per-question answer image extractor.
Uses PyMuPDF (fitz) to render each page and divide it into
equal horizontal strips — one strip per question.
"""
import uuid
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF

CROPS_DIR = Path("uploads/crops")
CROPS_DIR.mkdir(parents=True, exist_ok=True)


def extract_answer_images(
    pdf_path: str,
    num_questions: int,
    dpi: int = 150,
) -> dict[int, Optional[str]]:
    """
    Render each page of a PDF and divide horizontally into equal strips,
    one per question. Returns {question_number: image_path}.

    For a multi-page PDF, questions are spread across pages proportionally.
    """
    doc = fitz.open(pdf_path)
    total_pages = len(doc)

    # Distribute questions across pages
    qs_per_page = max(1, num_questions // total_pages)
    remainder = num_questions % total_pages

    result: dict[int, Optional[str]] = {}
    q_idx = 1
    scale = dpi / 72  # points → pixels

    for page_num in range(total_pages):
        if q_idx > num_questions:
            break

        page = doc[page_num]
        pw = page.rect.width   # points
        ph = page.rect.height  # points

        # How many questions land on this page?
        qs_on_this_page = qs_per_page + (1 if page_num < remainder else 0)
        strip_h = ph / qs_on_this_page  # height per strip in points

        for i in range(qs_on_this_page):
            if q_idx > num_questions:
                break

            y0 = i * strip_h
            y1 = (i + 1) * strip_h if i < qs_on_this_page - 1 else ph

            # Render only this strip using a clip rect
            clip = fitz.Rect(0, y0, pw, y1)
            mat = fitz.Matrix(scale, scale)
            pix = page.get_pixmap(matrix=mat, clip=clip)

            out_path = CROPS_DIR / f"{uuid.uuid4()}.png"
            pix.save(str(out_path))
            result[q_idx] = str(out_path)
            q_idx += 1

    doc.close()
    return result
