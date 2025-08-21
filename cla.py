import subprocess

input_pdf = "american.pdf"
output_pdf = "american_fixed.pdf"

cmd = [
    "gs",
    "-o", output_pdf,
    "-sDEVICE=pdfwrite",
    "-dPDFSETTINGS=/prepress",
    input_pdf
]

# Run the command
subprocess.run(cmd, check=True)

print(f"Fixed PDF saved as {output_pdf}")
