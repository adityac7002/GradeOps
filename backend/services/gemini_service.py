import os
import logging
from typing import Dict, Any, Optional
from google import genai
from google.genai import types
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class ExtractionResult(BaseModel):
    transcription: str
    is_blank: bool
    legibility: str # high | medium | low
    contains_diagram: bool
    diagram_description: Optional[str] = None

class GeminiService:
    def __init__(self):
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment")
        self.client = genai.Client(api_key=api_key)
        self.model_id = "gemini-2.0-flash" # Using the latest flash for speed/cost

    def extract_answer(self, image_path: str, question_text: str) -> Dict[str, Any]:
        """
        Performs VLM extraction on a handwritten answer image.
        Uses structured output to ensure reliable JSON.
        """
        logger.info(f"Extracting answer from {image_path}...")
        
        with open(image_path, "rb") as f:
            image_data = f.read()

        prompt = f"""
        You are reading a scanned handwritten exam answer. 
        Extract the text verbatim, preserving mathematical notation as LaTeX (e.g., $x^2$, $\\int$).
        
        Question Context:
        \"\"\"{question_text}\"\"\"
        
        Return the result in the specified JSON format.
        """

        try:
            response = self.client.models.generate_content(
                model=self.model_id,
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
                    response_schema=ExtractionResult,
                ),
            )
            
            # Since we used response_schema, the response is already parsed or in a clean JSON string
            return response.parsed.model_dump()
            
        except Exception as e:
            logger.error(f"Gemini extraction failed: {e}")
            return {
                "transcription": "",
                "is_blank": True,
                "legibility": "low",
                "contains_diagram": False,
                "diagram_description": f"Error: {str(e)}"
            }

# Singleton instance
gemini = GeminiService()
