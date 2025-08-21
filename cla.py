import fitz  # PyMuPDF

def check_pdf_render_errors(pdf_path, dpi=100):
    """
    Try to render every page of a PDF to detect invalid float/grey color issues.
    Returns a dict: {page_number: "ok" | error_message}
    """
    doc = fitz.open(pdf_path)
    results = {}

    for i, page in enumerate(doc):
        pno = i + 1  # 1-based page numbers
        try:
            # Force rasterization: this is where the original grey color issue appeared
            _ = page.get_pixmap(dpi=dpi)
            results[pno] = "ok"
        except Exception as e:
            results[pno] = str(e)

    return results


# Example usage
pdf_path = "american_fixed.pdf"
results = check_pdf_render_errors(pdf_path)

for pno, status in results.items():
    print(f"Page {pno}: {status}")
