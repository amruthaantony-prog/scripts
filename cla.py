from paddleocr import PaddleOCR
from pdf2image import convert_from_path

# Step 1: Convert PDF pages to images
pages = convert_from_path("sample.pdf", dpi=300)

# Step 2: Initialize OCR
ocr = PaddleOCR(use_angle_cls=True, lang='en')

# Step 3: Run OCR on each page
for i, page in enumerate(pages):
    result = ocr.ocr(page, cls=True)
    print(f"--- Page {i+1} ---")
    for line in result[0]:
        _, (text, confidence) = line
        print(text, confidence)
