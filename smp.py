import fitz  # PyMuPDF

def extract_clean_toc(pdf_path, max_toc_pages=2, indent_threshold=100):
    """
    Extracts a clean TOC from the first few pages of the PDF based on embedded hyperlinks.
    
    Args:
        pdf_path (str): Path to the input PDF.
        max_toc_pages (int): Number of pages to check for TOC (default: 2).
        indent_threshold (int): x0 threshold to determine level (default: 100).
    
    Returns:
        list of [level, section name, page number]
    """
    doc = fitz.open(pdf_path)
    toc_entries = []

    for page_no in range(min(max_toc_pages, len(doc))):
        page = doc[page_no]
        links = page.get_links()

        for link in links:
            if "page" not in link or not link.get("from"):
                continue

            target_page = link["page"] + 1  # convert 0-based to 1-based
            rect = link["from"]
            text = page.get_text("text", clip=rect).strip()

            if not text or text.isspace():
                continue

            level = 2 if rect.x0 > indent_threshold else 1
            toc_entries.append([level, text, target_page])

    return toc_entries
