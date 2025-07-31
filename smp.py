import fitz  # PyMuPDF

def extract_clean_toc(pdf_path):
    doc = fitz.open(pdf_path)
    toc_entries = []
    max_pages_to_check = 2
    indent_threshold = 100  # px
    seen_entries = set()

    for page_no in range(min(max_pages_to_check, len(doc))):
        page = doc[page_no]

        # Step 1: Extract all clickable TOC links
        links = page.get_links()
        for link in links:
            if "page" not in link or not link.get("from"):
                continue

            target_page = link["page"] + 1  # 0-based to 1-based
            rect = link["from"]
            text = page.get_text("text", clip=rect).strip()
            if not text or text.isspace():
                continue

            level = 2 if rect.x0 > indent_threshold else 1
            key = (text.lower(), target_page)
            if key not in seen_entries:
                toc_entries.append([level, text, str(target_page)])
                seen_entries.add(key)

        # Step 2: Look for non-linked bold or large-font text (section headers)
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                if not spans:
                    continue

                line_text = " ".join([span["text"] for span in spans]).strip()
                if not line_text or line_text.isspace():
                    continue

                font_sizes = [round(span["size"]) for span in spans]
                max_font = max(font_sizes)

                # Heuristics for level-1 headings
                if (
                    max_font > 10 and                         # likely heading
                    len(line_text.split()) <= 6 and          # not a paragraph
                    not any(line_text.lower() in e[1].lower() and str(page_no + 1) == e[2] for e in toc_entries)
                ):
                    toc_entries.append([1, line_text, str(page_no + 1)])
                    seen_entries.add((line_text.lower(), page_no + 1))

    return toc_entries
