import fitz  # PyMuPDF
import numpy as np
from PIL import Image
import easyocr

reader = easyocr.Reader(['en'])  # You can add other languages if needed

def convert_pdf_to_text_easyocr(pdf_path, start_page, end_page):
    pdf_document = fitz.open(pdf_path)
    ocr_text = ""

    for page_num in range(start_page - 1, end_page):
        if page_num < 0 or page_num >= pdf_document.page_count:
            print(f"Page number {page_num} is out of range")
            continue

        # Render PDF page to image
        page = pdf_document.load_page(page_num)
        pix = page.get_pixmap()
        image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        # Convert to NumPy array for EasyOCR
        np_image = np.array(image)

        # Run OCR using EasyOCR
        text_lines = reader.readtext(np_image, detail=0)  # `detail=0` returns only text
        page_text = "\n".join(text_lines)

        ocr_text += f"\n--- Page {page_num + 1} ---\n{page_text}"

    return ocr_text
