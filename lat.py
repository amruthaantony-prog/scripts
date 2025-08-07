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

def clean_toc_line(line):
    stripped = line.strip()
    if not stripped or len(stripped) < 4:
        return None
    if re.match(r"^[A-Da-d][\).]?$", stripped):
        return None

    # Remove common date patterns like (Mar 12, 2025), Feb 2025, etc.
    stripped = re.sub(r"\(?\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2} \w+ \d{4}|\w+ \d{1,2}, \d{4}|\w+ \d{4}|\d{4})\b\)?", "", stripped)
    stripped = re.sub(r"\s{2,}", " ", stripped).strip()  # remove extra spaces
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

    while i < len(toc_list):
        current = toc_list[i]
        label_lower = current[1].lower()

        # Start of Equity Research block
        if label_lower == "equity research":
            equity_start = current[2]
            i += 1

            level2_brokers = []
            equity_end = equity_start

            # Loop through broker reports
            while i < len(toc_list):
                broker_label = toc_list[i][1].lower()
                if any(b in broker_label for b in BROKER_NAMES):
                    broker = toc_list[i]
                    level2_brokers.append([2, broker[1].strip().title(), broker[2], broker[3]])
                    equity_end = broker[3]
                    i += 1
                else:
                    break

            # Add Level 1 Equity Research section
            merged.append([1, "Equity Research", equity_start, equity_end])
            # Add Level 2 brokers
            merged.extend(level2_brokers)

        else:
            merged.append(current)
            i += 1

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
