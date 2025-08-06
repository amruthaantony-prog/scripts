import fitz  # PyMuPDF
import easyocr
import re

# Load EasyOCR
reader = easyocr.Reader(['en'], gpu=True)

def extract_toc_links(pdf_path):
    doc = fitz.open(pdf_path)
    toc_links = []

    for page_num in range(min(3, len(doc))):  # Only first 3 pages
        page = doc.load_page(page_num)
        for link in page.get_links():
            if "page" in link:
                text = page.get_textbox(link['from']) or ""
                toc_links.append({
                    "text": text.strip(),
                    "page": link["page"]
                })

    return toc_links, len(doc)

def extract_toc_text(pdf_path):
    doc = fitz.open(pdf_path)
    toc_text = []

    for page_num in range(min(3, len(doc))):
        pix = doc[page_num].get_pixmap(dpi=500)
        image = fitz.Pixmap(pix, 0) if pix.alpha else pix
        img_array = image.samples.reshape(image.height, image.width, image.n)
        lines = reader.readtext(img_array, detail=0)
        toc_text.extend(lines)

    return toc_text

def match_lines_to_links(toc_text, toc_links):
    matched = []
    for line in toc_text:
        for link in toc_links:
            if line.lower().strip() in link['text'].lower().strip():
                matched.append([line.strip(), link['page']])
                break
    return matched

def normalize_section_name(name):
    name = name.lower()
    if any(x in name for x in ["10-k", "10-q", "form"]):
        return "Forms"
    elif "transcript" in name or "call" in name:
        return "Earnings Transcript"
    elif "press" in name or "presentation" in name:
        return "Earnings Release"
    elif "research" in name:
        return "Equity Research"
    elif "investor" in name:
        return "Investor Presentation"
    else:
        return name.title()

def build_final_toc(matched, total_pages):
    result = []
    for i, (name, start_page) in enumerate(matched):
        end_page = matched[i+1][1] - 1 if i+1 < len(matched) else total_pages - 1
        label = normalize_section_name(name)
        result.append([1, label, start_page, end_page])  # Level 1
    return result

def process_pdf(pdf_path):
    toc_links, total_pages = extract_toc_links(pdf_path)
    toc_text = extract_toc_text(pdf_path)
    matched = match_lines_to_links(toc_text, toc_links)
    return build_final_toc(matched, total_pages)

# Example usage
pdf_path = "your_pib_file.pdf"
toc_output = process_pdf(pdf_path)

print(toc_output)
