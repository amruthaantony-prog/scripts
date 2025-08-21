import fitz  # PyMuPDF

def check_pdf_render_errors(pdf_path, dpi=100):
    doc = fitz.open(pdf_path)
    for i, page in enumerate(doc):
        try:
            # force rasterization (this is where grey/color errors appear)
            pix = page.get_pixmap(dpi=dpi)
        except Exception as e:
            print(f"Page {i+1} render failed: {e}")
            return False
    return True

ok = check_pdf_render_errors("american_fixed.pdf")
print("Render test passed" if ok else "Render test failed")
