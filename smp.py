import fitz
import easyocr
import re

def extract_toc_easyocr(pdf_path):
    # Step 1: Render page 0 to image
    doc = fitz.open(pdf_path)
    pix = doc[0].get_pixmap(dpi=300)
    img_path = "page0.png"
    pix.save(img_path)

    # Step 2: OCR
    reader = easyocr.Reader(['en'])
    results = reader.readtext(img_path, detail=0)

    # Step 3: Parse lines into TOC entries
    toc = []
    section_header = None
    page_number_pattern = re.compile(r'(.+?)\s+(\d{1,4})$')  # e.g. "Q4 2024 Form 8-K 67"

    for line in results:
        line = line.strip()
        if not line or line.lower() in ["table of contents", "march 18, 2025"]:
            continue

        match = page_number_pattern.match(line)
        if match:
            title = match.group(1).strip()
            page = match.group(2).strip()
            toc.append([2, title, page])
        else:
            toc.append([1, line, "0"])  # assume page 0 for headers

    return toc
