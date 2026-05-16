import os
import uuid
import logging
from pathlib import Path
from typing import List, Tuple

import fitz  # PyMuPDF
from pypdf import PdfReader, PdfWriter

logger = logging.getLogger(__name__)

STORAGE_DIR = Path("storage")

def split_bulk_pdf(bulk_pdf_path: str, pages_per_student: int, exam_id: int) -> List[str]:
    """
    Split a large PDF containing many student papers into individual PDFs.
    Returns a list of paths to the created individual PDFs.
    """
    reader = PdfReader(bulk_pdf_path)
    total_pages = len(reader.pages)
    
    output_paths = []
    exam_storage = STORAGE_DIR / "exams" / str(exam_id) / "submissions"
    exam_storage.mkdir(parents=True, exist_ok=True)
    
    for i in range(0, total_pages, pages_per_student):
        writer = PdfWriter()
        # Handle cases where the last student might have fewer pages (or trailing pages)
        end_page = min(i + pages_per_student, total_pages)
        
        for page_num in range(i, end_page):
            writer.add_page(reader.pages[page_num])
        
        student_pdf_name = f"submission_{i // pages_per_student + 1}_{uuid.uuid4().hex[:8]}.pdf"
        output_path = exam_storage / student_pdf_name
        
        with open(output_path, "wb") as f:
            writer.write(f)
        
        output_paths.append(str(output_path))
        
    return output_paths

def rasterize_pdf_to_pngs(pdf_path: str, output_dir: str, dpi: int = 200) -> List[str]:
    """
    Render each page of a PDF to a PNG image.
    Used for both extraction and display in the review dashboard.
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    doc = fitz.open(pdf_path)
    image_paths = []
    
    for i in range(len(doc)):
        page = doc[i]
        # 200 DPI is the sweet spot for Gemini vision and readability
        pix = page.get_pixmap(dpi=dpi)
        
        img_name = f"page_{i + 1}.png"
        img_path = out_path / img_name
        pix.save(str(img_path))
        image_paths.append(str(img_path))
        
    doc.close()
    return image_paths
