import fitz
import numpy as np
import re

# === Constants ===
BROKER_NAMES = [
    "jpmorgan", "morgan stanley", "nomura", "bnp paribas",
    "bofa global research", "goldman sachs", "ubs", "barclays", "hsbc", "jefferies",
    "credit suisse", "citigroup", "rbc", "evercore", "wells fargo"
]


# === TOC Processing ===

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


def match_lines_to_links(toc_text, toc_links):
    matched = []
    for line in toc_text:
        stripped_line = line.strip()
        if not stripped_line or len(stripped_line) < 4:
            continue
        if re.match(r"^[A-Da-d][\).]?$", stripped_line):
            continue
        for link in toc_links:
            if stripped_line.lower() in link['text'].lower().strip():
                matched.append((stripped_line, link["page"]))
                break
    return matched


def normalize_section_name(name):
    name = name.lower()
    if any(x in name for x in ["10-k", "10-q", "form"]):
        return "Forms"
    elif "transcript" in name or "call" in name:
        return "Earnings Transcript"
    elif "press" in name or "presentation" in name:
        if "investor" in name or "02.15.2024" in name:
            return "Investor Presentation"
        return "Earnings Release"
    elif "news" in name:
        return "Recent News"
    elif "equity" in name:
        return "Equity Research"
    elif any(b in name for b in BROKER_NAMES):
        return name.title()
    else:
        return name.title()


def build_final_toc(matched, total_pages):
    result = []
    for i, (name, start_page) in enumerate(matched):
        end_page = matched[i + 1][1] - 1 if i + 1 < len(matched) else total_pages - 1
        label = normalize_section_name(name)

        # Skip TOC-only headings (like "Earnings Update", "Investor Presentation" if just container)
        if label in ["Earnings Release", "Investor Presentation", "Equity Research"] and end_page - start_page <= 1:
            continue

        result.append([1, label, start_page, end_page])
    return result

def merge_fragments(matched):
    merged = []
    skip_next = False
    for i in range(len(matched)):
        if skip_next:
            skip_next = False
            continue

        current = matched[i]
        if i + 1 < len(matched):
            next_line = matched[i + 1]
            if current[1] == next_line[1]:  # same page
                combined_text = f"{current[0]} {next_line[0]}"
                merged.append([combined_text, current[1]])
                skip_next = True
                continue

        merged.append(list(current))
    return merged

def merge_equity_research_sections(toc_list):
    merged = []
    i = 0
    while i < len(toc_list):
        label_lower = toc_list[i][1].lower()
        if label_lower == "equity research":
            merged_start = toc_list[i][2]
            i += 1
            merged_end = merged_start
            while i < len(toc_list) and any(b in toc_list[i][1].lower() for b in BROKER_NAMES):
                merged_end = toc_list[i][3]
                i += 1
            merged.append([1, "Equity Research", merged_start, merged_end])
        else:
            merged.append(toc_list[i])
            i += 1
    return merged


def merge_adjacent_same_labels(toc_list):
    result = []
    for entry in toc_list:
        if result and entry[1] == result[-1][1]:
            result[-1][3] = entry[3]  # Extend end page
        else:
            result.append(entry)
    return result


# === Main ===

def process_pdf(pdf_path):
    with fitz.open(pdf_path) as doc:
        total_pages = len(doc)
        toc_page = find_toc_page(doc)
        toc_links = extract_toc_links(doc, toc_page)
        toc_text = extract_toc_text(doc, toc_page)
        matched = match_lines_to_links(toc_text, toc_links)

        final = build_final_toc(matched, total_pages)
        final = merge_equity_research_sections(final)
        final = merge_adjacent_same_labels(final)
        return final
