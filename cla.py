import fitz  # PyMuPDF

pdf_path = "american_fixed.pdf"
doc = fitz.open(pdf_path)

for i, page in enumerate(doc):
    try:
        text = page.get_text("text")
    except Exception as e:
        print(f"Page {i} failed with: {e}")
