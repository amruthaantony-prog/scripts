import io
import pdfplumber

def process_page_batch(pdf_bytes: bytes, page_indices: list):
    out = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for p in page_indices:
            page = pdf.pages[p]
            tables = page.extract_tables() or []
            for ti, tbl in enumerate(tables):
                out.append({
                    "page_number": p + 1,
                    "table_index": ti,
                    "title": f"Table_Page_{p+1}_{ti}",
                    "data": tbl,
                    "coordinates": page.bbox
                })
    return out
import os, io, math, multiprocessing as mp, pdfplumber
from table_worker import process_page_batch

def chunk_list(lst, n):
    """Split lst into n nearly equal parts."""
    k, m = divmod(len(lst), n)
    return [lst[i*k + min(i, m):(i+1)*k + min(i+1, m)] for i in range(n)]

def extract_tables_parallel(file_path, processes=None):
    with open(file_path, "rb") as f:
        pdf_bytes = f.read()

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        pages = list(range(len(pdf.pages)))

    procs = processes or min(os.cpu_count(), 8)  # try 8 first
    batches = chunk_list(pages, procs)

    with mp.get_context("spawn").Pool(processes=procs) as pool:
        results = pool.starmap(process_page_batch, [(pdf_bytes, b) for b in batches])

    return [t for batch in results for t in batch]

# Run
file_path = os.path.join(os.getcwd(), "Amer.pdf")
tables = extract_tables_parallel(file_path, processes=8)
print(len(tables))
