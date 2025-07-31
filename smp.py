import fitz

def extract_clean_toc(pdf_path):
    doc = fitz.open(pdf_path)
    page = doc[0]
    indent_threshold = 100

    blocks = page.get_text("dict")["blocks"]
    lines = []

    # Step 1: Extract raw lines
    for block in blocks:
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            if not spans:
                continue
            text = " ".join(span["text"] for span in spans).strip()
            if not text or text.lower() in ["table of contents", "march 18, 2025"]:
                continue
            x0 = spans[0]["bbox"][0]
            y0 = spans[0]["bbox"][1]
            lines.append({
                "text": text,
                "x0": x0,
                "y0": y0,
                "linked": False,
                "target_page": None
            })

    # Step 2: Match links to lines
    links = page.get_links()
    for link in links:
        if "page" not in link or not link.get("from"):
            continue
        rect = link["from"]
        text = page.get_text("text", clip=rect)
        if not text:
            continue
        text = text.strip()
        for line in lines:
            if line["text"] == text:
                line["linked"] = True
                line["target_page"] = str(link["page"])

    # Step 3: Sort lines top-to-bottom
    lines = sorted(lines, key=lambda l: l["y0"])

    # Step 4: Final pass to build TOC
    toc = []
    i = 0
    while i < len(lines):
        line = lines[i]
        text = line["text"]
        x0 = line["x0"]
        linked = line["linked"]
        page_num = line["target_page"]

        if x0 <= indent_threshold:
            # Level 1
            if not linked:
                # Look ahead for next Level 2's page number
                for j in range(i + 1, len(lines)):
                    next_line = lines[j]
                    if next_line["linked"] and next_line["x0"] > indent_threshold:
                        page_num = next_line["target_page"]
                        break
            toc.append([1, text, page_num or "0"])

        elif linked and x0 > indent_threshold:
            # Level 2
            toc.append([2, text, page_num])

        i += 1

    return toc
