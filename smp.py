import fitz  # PyMuPDF
import numpy as np
import easyocr
import re

reader = easyocr.Reader(['en'], gpu=True)

# Extract links (with label and target page) from the TOC page
def extract_toc_links(pdf_path: str, toc_page: int = 0):
    doc = fitz.open(pdf_path)
    links = doc[toc_page].get_links()
    toc_links = []
    for l in links:
        if "page" in l:
            toc_links.append({
                "label": l.get("uri", "").strip() if "uri" in l else "",  # fallback
                "page": l["page"]
            })
    return toc_links, len(doc)

# Extract visible text from TOC page using OCR
def extract_toc_text(pdf_path: str, toc_page: int = 0):
    doc = fitz.open(pdf_path)
    pix = doc[toc_page].get_pixmap(dpi=300)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    lines = reader.readtext(img, detail=0)
    return lines

# Match TOC text lines to corresponding link targets
def match_lines_to_links(toc_lines, toc_links):
    result = []
    for i, line in enumerate(toc_lines):
        if i < len(toc_links):
            result.append((line.strip(), toc_links[i]['page']))
    return result

# Normalize section titles into standard categories
def normalize_section_name(name: str):
    name = name.lower()
    if "call" in name:
        return "Earnings Transcript"
    elif "transcript" in name:
        return "Earnings Transcript"
    elif "presentation" in name:
        return "Earnings Release"
    elif "6-k" in name:
        return "6-K"
    elif "20-f" in name:
        return "20-F"
    elif "news" in name:
        return "Recent News"
    elif "research" in name:
        return "Equity Research"
    else:
        return name.title()

# Build final TOC output: [level, normalized name, start, end]
def build_final_toc(matched, total_pages):
    result = []
    for i, (name, start_page) in enumerate(matched):
        end_page = matched[i + 1][1] - 1 if i + 1 < len(matched) else total_pages - 1
        label = normalize_section_name(name)
        result.append([1, label, start_page, end_page])  # Always Level 1
    return result

# Main driver function
def process_pdf(pdf_path: str):
    toc_links, total_pages = extract_toc_links(pdf_path, toc_page=0)
    toc_text = extract_toc_text(pdf_path, toc_page=0)
    matched = match_lines_to_links(toc_text, toc_links)
    return build_final_toc(matched, total_pages)
