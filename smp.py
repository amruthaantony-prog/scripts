%%writefile two_gpu_easyocr_helper.py
import os, time, multiprocessing as mp
import easyocr, fitz  # PyMuPDF

def _render_page(pdf_path, page_no, dpi):
    doc = fitz.open(pdf_path)
    page = doc.load_page(page_no)
    mat = fitz.Matrix(dpi/72.0, dpi/72.0)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = memoryview(pix.samples)  # zero-copy buffer
    import numpy as np
    arr = np.frombuffer(img, dtype='uint8').reshape(pix.height, pix.width, 3)
    return arr

def _worker(gpu_id, pdf_path, tasks, opts, out_q):
    """
    tasks: list[int] page numbers to OCR
    Returns: dict with 'gpu', 'elapsed', 'results' where results = [(page_no, text_list), ...]
    """
    os.environ["CUDA_VISIBLE_DEVICES"] = str(gpu_id)
    start = time.perf_counter()

    reader = easyocr.Reader(
        opts.get("langs", ["en"]),
        gpu=True,
        model_storage_directory=opts.get("model_storage_directory"),
        download_enabled=opts.get("download_enabled", False),
        quantize=opts.get("quantize", False),
        verbose=opts.get("verbose", False),
    )

    dpi = int(opts.get("dpi", 200))
    results = []
    for pno in tasks:
        img = _render_page(pdf_path, pno, dpi)
        txt = reader.readtext(img, detail=0, paragraph=False)
        results.append((pno, txt))

    elapsed = time.perf_counter() - start
    out_q.put({"gpu": gpu_id, "elapsed": elapsed, "results": results})

def run_two_readers_pdf_pages(pdf_path, page_numbers, opts=None):
    """
    pdf_path: str
    page_numbers: list[int] (0-based)
    Splits list into halves -> GPU0 / GPU1, runs in parallel.
    Returns: (results_sorted, timings) where
      results_sorted = [(page_no, text_list), ...] sorted by page_no
      timings = {'total': float, 'gpu0': float, 'gpu1': float}
    """
    opts = opts or {}
    mp.set_start_method("spawn", force=True)

    nums = sorted(page_numbers)
    n = len(nums)
    mid = n // 2
    part0, part1 = nums[:mid], nums[mid:]  # GPU0 first half, GPU1 second half

    ctx = mp.get_context("spawn")
    q = ctx.Queue()

    t0 = time.perf_counter()
    p0 = ctx.Process(target=_worker, args=(0, pdf_path, part0, opts, q), daemon=True)
    p1 = ctx.Process(target=_worker, args=(1, pdf_path, part1, opts, q), daemon=True)
    p0.start(); p1.start()

    payloads = []
    for _ in range(2):
        payloads.append(q.get())

    p0.join(); p1.join()
    total_elapsed = time.perf_counter() - t0

    # Collect
    gpu_times = {pl["gpu"]: pl["elapsed"] for pl in payloads}
    results = []
    for pl in payloads:
        results.extend(pl["results"])
    results.sort(key=lambda t: t[0])

    timings = {
        "total": total_elapsed,
        "gpu0": gpu_times.get(0, 0.0),
        "gpu1": gpu_times.get(1, 0.0),
    }
    return results, timings
from two_gpu_easyocr_helper import run_two_readers_pdf_pages

pdf_path = "pib1.pdf"  # your PDF
pages_to_ocr = [0,1,2,3,4,5,6,7,8,9,10]  # 0-based page numbers (any order)

opts = {
    "langs": ["en"],
    "model_storage_directory": "../easyocr/",
    "download_enabled": False,
    "verbose": False,
    "dpi": 220,          # adjust if needed (200–300 is typical)
    # "quantize": True,  # optional VRAM saver
}

results, timings = run_two_readers_pdf_pages(pdf_path, pages_to_ocr, opts)

print(f"Pages OCRed: {len(results)}")
print(f"Total time: {timings['total']:.2f}s | GPU0: {timings['gpu0']:.2f}s | GPU1: {timings['gpu1']:.2f}s")

# Example: show first few
for pno, text in results[:3]:
    print(f"\nPage {pno}:")
    print(text[:5])  # first few lines
