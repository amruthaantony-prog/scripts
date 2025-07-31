from pymupdf4llm import PyMuPDFLoader

def extract_toc_from_layout(pdf_path):
    loader = PyMuPDFLoader(pdf_path)
    elements = loader.load()  # All pages

    # Focus only on page 0
    page_elements = [el for el in elements if el.metadata['page_number'] == 1]

    toc = []
    for el in page_elements:
        text = el.text.strip()
        if not text or text.lower() in ["table of contents", "march 18, 2025"]:
            continue

        if el.type == "Title":
            toc.append([1, text, "0"])
        elif el.type == "ListItem":
            # Try to split last number from text
            parts = text.rsplit(" ", 1)
            if len(parts) == 2 and parts[1].isdigit():
                toc.append([2, parts[0].strip(), parts[1]])
            else:
                toc.append([2, text, "0"])  # fallback

    return toc
