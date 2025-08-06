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
    elif "news" in name:
        return "Recent News"
    elif "equity" in name:
        return "Equity Research"
    else:
        return name.title()

def build_final_toc(matched, total_pages):
    result = []
    for i, (name, start_page) in enumerate(matched):
        end_page = matched[i + 1][1] - 1 if i + 1 < len(matched) else total_pages - 1
        label = normalize_section_name(name)
        result.append([1, label, start_page, end_page])
    return result

def process_pdf(pdf_path):
    with fitz.open(pdf_path) as doc:
        total_pages = len(doc)
        toc_page = find_toc_page(doc)
        toc_links = extract_toc_links(doc, toc_page)
        toc_text = extract_toc_text(doc, toc_page)
        matched = match_lines_to_links(toc_text, toc_links)
        return build_final_toc(matched, total_pages)
