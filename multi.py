# parallel_tables.py
import io, os, multiprocessing as mp
import pdfplumber

def _process_page(args):
    pdf_bytes, page_no = args
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        page = pdf.pages[page_no]
        tables = page.extract_tables()
        out = []
        for ti, tbl in enumerate(tables or []):
            # rows → list of dicts (simple header zip; adjust to your needs)
            if tbl and tbl[0]:
                header = tbl[0]
                data = [dict(zip(header, row)) for row in tbl[1:] if len(row) == len(header)]
            else:
                data = tbl
            out.append({
                "page_number": page_no + 1,
                "table_index": ti,
                "title": f"Table_Page_{page_no+1}_{ti}",
                "data": data,
                "coordinates": page.bbox,  # page box; replace with a table bbox if you have one
            })
        return out

def extract_tables_parallel(file_path, pages=None, processes=None, chunksize=8):
    # read once → pass bytes to workers (avoids file-handle contention)
    with open(file_path, "rb") as f:
        pdf_bytes = f.read()

    # default: all pages; otherwise pass a list/range of indices (0-based)
    if pages is None:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            pages = list(range(len(pdf.pages)))
    else:
        pages = list(pages)

    procs = processes or min(os.cpu_count() or 1, 8)

    # Prepare (bytes, page_no) tuples
    jobs = [(pdf_bytes, p) for p in pages]

    # Use processes (not threads) because pdfplumber is CPU-bound
    with mp.get_context("spawn").Pool(processes=procs) as pool:
        # imap → streaming results; set a sensible chunksize (5–10 pages)
        results = pool.imap(_process_page, jobs, chunksize=chunksize)
        all_tables = []
        for page_tables in results:
            all_tables.extend(page_tables)
    return all_tables

if __name__ == "__main__":  # required on Windows/macOS
    tables = extract_tables_parallel("your.pdf", processes=None, chunksize=8)
    print(len(tables))
