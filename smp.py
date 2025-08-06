import fitz  # PyMuPDF
import easyocr
import numpy as np

# Initialize EasyOCR reader
reader = easyocr.Reader(['en'], gpu=True, download_enabled=False)

def extract_toc_links(pdf_path):
    doc = fitz.open(pdf_path)
    toc_page = 0
    links = doc[toc_page].get_links()
    total_pages = len(doc)
    toc_links = [{'label': l['uri'], 'page': l['page']} for l in links if 'page' in l]
    return toc_links, total_pages

def extract_toc_text(pdf_path):
    doc = fitz.open(pdf_path)
    toc_text = []
    page_num = 0  # Assuming TOC is on first page
    pix = doc[page_num].get_pixmap(dpi=500)
    image = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    lines = reader.readtext(image, detail=0)
    toc_text.extend(lines)
    return toc_text

def match_lines_to_links(toc_lines, toc_links):
    result = []
    link_texts = [link['label'] for link in toc_links]
    pages = [link['page'] for link in toc_links]

    for i, line in enumerate(toc_lines):
        for j, text in enumerate(link_texts):
            if text and text.lower().strip() in line.lower():
                result.append((line.strip(), pages[j]))
                break
    return result

def normalize_section_name(raw):
    raw = raw.lower()
    if "6-k" in raw:
        return "6-K"
    elif "20-f" in raw or "10-k" in raw:
        return "20-F"
    elif "call" in raw or "transcript" in raw:
        return "Earnings Transcript"
    elif "presentation" in raw:
        return "Earnings Release"
    elif "newsrun" in raw:
        return "Recent News"
    elif any(broker in raw for broker in [
        "jpmorgan", "morgan", "bofa", "nomura", "barclays",
        "rbc", "goldman", "wells", "deutsche", "citigroup", "equity research"
    ]):
        return "Equity Research"
    return raw.strip().title()

def build_final_toc(matched, total_pages):
    result = []
    for i, (name, start_page) in enumerate(matched):
        try:
            end_page = int(matched[i+1][1]) - 1 if i+1 < len(matched) else total_pages - 1
        except:
            end_page = total_pages - 1
        label = normalize_section_name(name)
        result.append([1, label, int(start_page), end_page])  # force Level = 1
    return merge_equity_research(result)

def merge_equity_research(toc_list):
    merged = []
    current = None
    for entry in toc_list:
        level, name, start, end = entry
        if name == "Equity Research":
            if current is None:
                current = [level, name, start, end]
            else:
                current[3] = end  # extend end page
        else:
            if current:
                merged.append(current)
                current = None
            merged.append([level, name, start, end])
    if current:
        merged.append(current)
    return merged

def process_pdf(pdf_path):
    toc_links, total_pages = extract_toc_links(pdf_path)
    toc_text = extract_toc_text(pdf_path)
    matched = match_lines_to_links(toc_text, toc_links)
    return build_final_toc(matched, total_pages)
