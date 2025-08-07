import fitz  # PyMuPDF
import numpy as np
import re

# OCR reader assumed imported and initialized, e.g.:
# import easyocr
# reader = easyocr.Reader(['en'])

def find_toc_page(doc):
    for page_num in range(min(3, len(doc))):  # Only first 3 pages
        page = doc.load_page(page_num)
        links = page.get_links()
        if len(links) > 5:
            return page_num
    return 0

def extract_toc_links(doc, toc_page):
    toc_links = []
    page = doc.load_page(toc_page)
    for link in page.get_links():
        if "page" in link:
            text = page.get_textbox(link.get("from")) or ""
            toc_links.append({
                "text": text.strip(),
                "page": int(link["page"])
            })
    return toc_links

def extract_toc_text(doc, toc_page):
    page = doc.load_page(toc_page)
    pix = page.get_pixmap(dpi=500)
    image_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    lines = reader.readtext(image_array, detail=0)
    return lines

# def clean_toc_line(line):
#     stripped = line.strip()
#     if not stripped or len(stripped) < 4:
#         return None
#     if re.match(r"^[A-Da-d][\).]?$", stripped):
#         return None

#     # Remove common date patterns like (Mar 12, 2025), Feb 2025, etc.
#     stripped = re.sub(r"\(?\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2} \w+ \d{4}|\w+ \d{1,2}, \d{4}|\w+ \d{4}|\d{4})\b\)?", "", stripped)
#     stripped = re.sub(r"\s{2,}", " ", stripped).strip()  # remove extra spaces
#     return stripped if len(stripped) >= 4 else None
def clean_toc_line(line):
    stripped = line.strip()
    if not stripped or len(stripped) < 4:
        return None
    if re.match(r"^[A-Da-d][\).]?$", stripped):
        return None

    # Remove parenthetical date expressions
    stripped = re.sub(r"\(?(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.? \d{1,2},? ?\d{0,4}\)?", "", stripped, flags=re.IGNORECASE)

    # Remove trailing empty brackets (e.g. leftover "()")
    stripped = re.sub(r"\(\s*\)", "", stripped)

    # Remove multiple spaces
    stripped = re.sub(r"\s{2,}", " ", stripped).strip()

    return stripped if len(stripped) >= 4 else None



def match_lines_to_links(toc_text, toc_links):
    matched = []
    for line in toc_text:
        cleaned = clean_toc_line(line)
        if not cleaned:
            continue
        for link in toc_links:
            if cleaned.lower() in link['text'].lower().strip():
                matched.append((cleaned, link["page"]))
                break
    return matched

def normalize_section_name(name):
    lowered = name.lower()

    if "investor" in lowered:
        return "Investor Presentation"
    
    if "presentation" in lowered and "earnings" in lowered:
        return "Earnings Release"
    
    if any(x in lowered for x in ["10-k", "10-q", "20-f", "40-f", "6-k", "8-k"]):
        return name.strip()  # Leave as-is
    
    if "transcript" in lowered or "call" in lowered:
        return "Earnings Transcript"
    
    if "press" in lowered:
        return "Earnings Release"
    
    if "news" in lowered:
        return "Recent News"
    
    if "equity" in lowered:
        return "Equity Research"
    
    return name.strip().title()

def build_final_toc(matched, total_pages):
    result = []
    for i, (name, start_page) in enumerate(matched):
        next_page = matched[i + 1][1] if i + 1 < len(matched) else total_pages
        end_page = max(start_page, next_page - 1)
        label = normalize_section_name(name)
        result.append([1, label, start_page, end_page])
    return result

BROKER_NAMES = [
    "jpmorgan", "morgan stanley", "nomura", "bnp paribas",
    "bofa global research", "goldman sachs", "ubs", "barclays", "hsbc", "jefferies",
    "credit suisse", "citigroup", "rbc", "evercore", "wells fargo"
]

def merge_equity_research_sections(toc_list):
    merged = []
    i = 0
    broker_block = []

    while i < len(toc_list):
        label = toc_list[i][1]
        norm_label = normalize(label)
        matched_broker = None

        for b in BROKER_NAMES:
            if normalize(b) in norm_label:
                matched_broker = b.title()
                break

        if matched_broker:
            broker_block.append([2, matched_broker, toc_list[i][2], toc_list[i][3]])
            i += 1
        else:
            if broker_block:
                # Insert Level 1 'Equity Research' wrapper before current item
                start_page = broker_block[0][2]
                end_page = broker_block[-1][3]
                merged.append([1, "Equity Research", start_page, end_page])
                merged.extend(broker_block)
                broker_block = []
            merged.append(toc_list[i])
            i += 1

    # Edge case: if brokers are the last items
    if broker_block:
        start_page = broker_block[0][2]
        end_page = broker_block[-1][3]
        merged.append([1, "Equity Research", start_page, end_page])
        merged.extend(broker_block)

    return merged


def process_pdf(pdf_path):
    with fitz.open(pdf_path) as doc:
        total_pages = len(doc)
        toc_page = find_toc_page(doc)
        toc_links = extract_toc_links(doc, toc_page)
        toc_text = extract_toc_text(doc, toc_page)
        matched = match_lines_to_links(toc_text, toc_links)
        toc = build_final_toc(matched, total_pages)
        final_toc = merge_equity_research_sections(toc)
        return final_toc
