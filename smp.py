import fitz  # PyMuPDF
import easyocr
import numpy as np

reader = easyocr.Reader(['en'], gpu=True)

# --- 1. Extract page links from the first few pages
def extract_toc_links(pdf_path, max_pages=3):
    doc = fitz.open(pdf_path)
    toc_links = []
    for page_num in range(min(max_pages, len(doc))):
        links = doc[page_num].get_links()
        for l in links:
            if "page" in l:
                label = l.get("uri", "").strip() if "uri" in l else ""
                toc_links.append({"label": label, "page": l["page"]})
    return toc_links, len(doc)

# --- 2. Extract ToC text from the first few pages using OCR
def extract_toc_text(pdf_path, max_pages=3):
    doc = fitz.open(pdf_path)
    toc_text = []
    for page_num in range(min(max_pages, len(doc))):
        pix = doc[page_num].get_pixmap(dpi=300)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        lines = reader.readtext(img, detail=0)
        toc_text.extend(lines)
    return toc_text

# --- 3. Match lines with page numbers using string similarity
from difflib import get_close_matches

def match_lines_to_links(toc_text, toc_links):
    matched = []
    for line in toc_text:
        best = get_close_matches(line, [l['label'] for l in toc_links if l['label']], n=1, cutoff=0.4)
        if best:
            for l in toc_links:
                if l['label'] == best[0]:
                    matched.append((line, l['page']))
                    break
    matched.sort(key=lambda x: x[1])
    return matched

# --- 4. Normalize section names
def normalize_section_name(name):
    name = name.strip().title()
    mapping = {
        "6-K": "6K",
        "Form 6-K": "6K",
        "20-F": "20F",
        "Form 20-F": "20F",
        "Call": "Earnings Transcript",
        "Transcript": "Earnings Transcript",
        "Presentation": "Earnings Release",
        "Newsrun": "Recent News",
        "Research": "Equity Research"
    }
    for k, v in mapping.items():
        if k.lower() in name.lower():
            return v
    return name

# --- 5. Build final ToC: [1, 'Section Name', start, end]
def build_final_toc(matched, total_pages):
    result = []
    for i, (name, start_page) in enumerate(matched):
        end_page = matched[i + 1][1] - 1 if i + 1 < len(matched) else total_pages - 1
        label = normalize_section_name(name)
        result.append([1, label, start_page, end_page])
    return result

# --- 6. Master function
def process_pdf(pdf_path):
    toc_links, total_pages = extract_toc_links(pdf_path)
    toc_text = extract_toc_text(pdf_path)
    matched = match_lines_to_links(toc_text, toc_links)
    return build_final_toc(matched, total_pages)
