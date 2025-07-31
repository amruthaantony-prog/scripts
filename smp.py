import fitz  # PyMuPDF

def extract_clean_toc(pdf_path):
    doc = fitz.open(pdf_path)
    toc_entries = []
    indent_threshold = 100  # px
    seen_entries = set()

    page = doc[0]  # 🔒 Only first page

    # Step 1: Extract all clickable TOC links
    links = page.get_links()
    for link in links:
        if "page" not in link or not link.get("from"):
            continue

        target_page = link["page"]  # ✅ keep as-is (0-based)
        rect = link["from"]
        text = page.get_text("text", clip=rect)
        if not text or text.isspace():
            continue

        text = text.strip()
        level = 2 if rect.x0 > indent_threshold else 1
        key = (text.lower(), target_page)
        if key not in seen_entries:
            toc_entries.append([level, text, str(target_page)])
            seen_entries.add(key)

    # Step 2: Add bold/large section headers (non-linked)
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

            # Heuristic: bold section headers (limit to short lines)
            if (
                max_font > 10 and
                len(line_text.split()) <= 6 and
                not any(line_text.lower() == e[1].lower() and e[2] == "0" for e in toc_entries)
            ):
                toc_entries.append([1, line_text, "0"])  # first page = "0"
                seen_entries.add((line_text.lower(), 0))

    return toc_entries
