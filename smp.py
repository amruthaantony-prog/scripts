import fitz
import re

def extract_structured_toc_fitz(pdf_path):
    doc = fitz.open(pdf_path)
    page = doc[0]  # only page 0

    blocks = page.get_text("dict")["blocks"]

    lines = []
    for block in blocks:
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            if not spans:
                continue
            text = " ".join(span["text"] for span in spans).strip()
            if not text:
                continue
            x0 = spans[0]["bbox"][0]
            y0 = spans[0]["bbox"][1]
            lines.append({
                "text": text,
                "x0": x0,
                "y0": y0,
                "font_size": spans[0]["size"]
            })

    # clean and sort
    lines = sorted(lines, key=lambda l: l["y0"])
    lines = [l for l in lines if l["text"].lower() not in ["table of contents", "march 18, 2025"]]

    toc = []
    current_section = None
    page_number_pattern = re.compile(r'.+?\s+(\d{1,4})$')

    for line in lines:
        text = line["text"]
        match = page_number_pattern.match(text)

        if match and line["x0"] > 100:  # indented and ends with page number
            title = text.rsplit(" ", 1)[0].strip()
            page_no = match.group(1)
            if current_section:
                toc.append([2, title, page_no])
        else:
            # heading (likely level 1)
            current_section = text
            toc.append([1, text, "0"])

    return toc
