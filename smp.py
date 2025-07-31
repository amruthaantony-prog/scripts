import fitz

def extract_structured_toc(pdf_path):
    doc = fitz.open(pdf_path)
    entries = []

    for page_no in range(len(doc)):
        links = doc[page_no].get_links()
        for link in links:
            if "page" in link:
                target_page = link["page"] + 1
                rect = link["from"]
                y0 = rect.y0
                text = doc[page_no].get_text("text", clip=rect).strip()
                if text:
                    entries.append((page_no + 1, y0, text, target_page))

    # Sort by TOC page, then y-position (top to bottom)
    entries.sort(key=lambda x: (x[0], x[1]))

    # Assign levels based on y-diff or indentation (naive logic below)
    structured = []
    last_y = None
    for toc_page, y0, text, target_page in entries:
        if last_y is None:
            level = 1
        elif y0 - last_y > 15:
            level = 2
        else:
            level = 1
        last_y = y0
        structured.append([level, text, target_page])

    return structured
