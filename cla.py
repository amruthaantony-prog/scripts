import ghostscript
import sys

input_pdf = "american.pdf"
output_pdf = "american_fixed.pdf"

args = [
    "ps2pdf",   # program name, not used
    "-dNOPAUSE",
    "-dBATCH",
    "-sDEVICE=pdfwrite",
    "-dPDFSETTINGS=/prepress",
    f"-sOutputFile={output_pdf}",
    input_pdf
]

# ghostscript expects arguments as bytes
ghostscript.Ghostscript(*map(str.encode, args))

print(f"Fixed PDF saved as {output_pdf}")
