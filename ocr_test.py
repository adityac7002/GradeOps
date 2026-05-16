from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import numpy as np

print("Downloading the GradeOps Handwriting AI...")
print("(This is a larger vision model, so it might take a couple of minutes to download!)")

# Load the TrOCR processor and model directly (pipeline is not compatible with TrOCR)
processor = TrOCRProcessor.from_pretrained("microsoft/trocr-base-handwritten")
model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-handwritten")

print("Model loaded successfully! Reading your image...")


def preprocess_for_trocr(image: Image.Image) -> Image.Image:
    """
    Enhances a low-contrast handwritten image (e.g., faint pencil on paper)
    so TrOCR can recognise it reliably.

    Steps:
    1. Convert to greyscale
    2. Auto-level (stretch the full dynamic range to 0-255)
    3. Enhance contrast further
    4. Denoise lightly
    5. Auto-crop to the text bounding box (remove empty margins)
    6. Pad with white so the model sees clean borders
    """
    # 1. Greyscale
    gray = image.convert("L")

    # 2. Auto-level: stretch histogram so darkest → 0, brightest → 255
    gray = ImageOps.autocontrast(gray, cutoff=1)  # clip top/bottom 1%

    # 3. Contrast boost
    gray = ImageEnhance.Contrast(gray).enhance(2.5)

    # 4. Gentle denoise (median-like via min-filter then blur)
    gray = gray.filter(ImageFilter.MedianFilter(size=3))
    gray = gray.filter(ImageFilter.SMOOTH)

    # 5. Auto-crop: find bounding box of dark (ink) pixels
    arr = np.array(gray)
    ink = arr < 180  # pixels darker than 180 are ink after enhancement
    rows = np.where(ink.any(axis=1))[0]
    cols = np.where(ink.any(axis=0))[0]

    if len(rows) == 0 or len(cols) == 0:
        # No ink found – return enhanced image as-is (TrOCR handles it)
        return gray.convert("RGB")

    pad = 20
    top    = max(0, rows[0]  - pad)
    bottom = min(arr.shape[0], rows[-1] + pad)
    left   = max(0, cols[0]  - pad)
    right  = min(arr.shape[1], cols[-1] + pad)

    cropped = gray.crop((left, top, right, bottom))

    # 6. Pad to white so the model doesn't see hard-edge artefacts
    padded = ImageOps.expand(cropped, border=20, fill=255)

    return padded.convert("RGB")


# Load, preprocess and run OCR
image = Image.open("test.jpg").convert("RGB")
processed = preprocess_for_trocr(image)

pixel_values = processor(images=processed, return_tensors="pt").pixel_values
generated_ids = model.generate(pixel_values, max_new_tokens=64)
result = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]

print("\n--- GRADE_OPS OCR RESULT ---")
print(result)