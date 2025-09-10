%%writefile two_gpu_easyocr_dynamic.py
import os, time, multiprocessing as mp
from typing import List, Dict, Tuple
import fitz  # PyMuPDF
import numpy as np
import easyocr

def _warmup_reader(reader):
    # Tiny warm-up to initialize CUDA kernels
    dummy = np.zeros((32, 32, 3), dtype=np.uint8)
    try:
        reader.readtext(dummy, detail=0, paragraph=False)
    except Exception:
        pass

def _worker(gpu_id: int, task_q: mp.queues.Queue, res_q: mp.queues.Queue, opts: dict):
    # Bind this process to a single GPU BEFORE creating the Reader
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
    _warmup_reader(reader)

    processed = 0
    while True:
        item = task_q.get()
        if item is None:
            # sentinel => done
            break
        page_no, img = item
        txt = reader.readtext(img, detail=0, paragraph=False)
        res_q.put((page_no, txt, gpu_id))
        processed += 1

    elapsed = time.perf_counter() - start
    res_q.put(("__worker_done__", gpu_id, processed, elapsed))

def _render_pages(pdf_path: str, page_numbers: List[int], dpi: int) -> Dict[int, np.ndarray]:
    # Render only requested pages once in parent; return {page_no: np.ndarray(H,W,3)}
    doc = fitz.open(pdf_path)
    out = {}
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    for pno in page_numbers:
        page = doc.load_page(pno)
        pix = page.get_pixmap(matrix=mat, alpha=False)  # RGB
        arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
        out[pno] = arr
    doc.close()
    return out

def run_dynamic_two_gpus(
    pdf_path: str,
    page_numbers: List[int],
    opts: dict = None,
    devices: List[int] = None
) -> Tuple[List[Tuple[int, list]], dict]:
    """
    pdf_path: str
    page_numbers: list[int] (0-based)
    opts: {
      "langs": ["en"], "model_storage_directory": "...", "download_enabled": False,
      "verbose": False, "quantize": False, "dpi": 200
    }
    devices: list[int] GPU IDs to use, default [0,1]. Example: [0,2]

    Returns:
      results_sorted: list of (page_no, text_list)
      timings: {
        "total": float, "per_gpu": {gpu_id: elapsed_seconds}, "pages_per_gpu": {gpu_id: count}
      }
    """
    if opts is None: opts = {}
    if devices is None: devices = [0, 1]
    if not page_numbers:
        return [], {"total": 0.0, "per_gpu": {}, "pages_per_gpu": {}}

    # Pre-render once
    dpi = int(opts.get("dpi", 200))
    t0 = time.perf_counter()
    page_numbers = sorted(page_numbers)
    images = _render_pages(pdf_path, page_numbers, dpi)

    # Queues & workers
    ctx = mp.get_context("spawn")
    task_q = ctx.Queue(maxsize=len(page_numbers))  # bounded is fine
    res_q  = ctx.Queue()

    # Enqueue tasks (dynamic; workers pull next available)
    for pno in page_numbers:
        task_q.put((pno, images[pno]))
    # Add one sentinel per worker
    for _ in devices:
        task_q.put(None)

    procs = []
    for gpu_id in devices:
        p = ctx.Process(target=_worker, args=(gpu_id, task_q, res_q, opts), daemon=True)
        p.start()
        procs.append(p)

    # Collect results
    results = []
    per_gpu_time = {g: 0.0 for g in devices}
    pages_per_gpu = {g: 0 for g in devices}
    workers_done = 0
    expected_done = len(devices)

    # We expect len(page_numbers) result tuples + expected_done done messages
    expected_msgs = len(page_numbers) + expected_done
    for _ in range(expected_msgs):
        msg = res_q.get()
        if isinstance(msg, tuple) and msg and msg[0] == "__worker_done__":
            _, g, count, elapsed = msg
            per_gpu_time[g] = elapsed
            pages_per_gpu[g] = count
            workers_done += 1
        else:
            # (page_no, text, gpu_id)
            pno, txt, g = msg
            results.append((pno, txt))

    for p in procs:
        p.join()

    total_elapsed = time.perf_counter() - t0
    results.sort(key=lambda x: x[0])
    timings = {"total": total_elapsed, "per_gpu": per_gpu_time, "pages_per_gpu": pages_per_gpu}
    return results, timings




from two_gpu_easyocr_dynamic import run_dynamic_two_gpus

pdf_path = "pib1.pdf"
pages_to_ocr = list(range(0, 40))  # 0-based page indices

opts = {
    "langs": ["en"],
    "model_storage_directory": "../easyocr/",
    "download_enabled": False,
    "verbose": False,
    "dpi": 220,          # 200–240 is usually the sweet spot
    # "quantize": True,  # optional, small accuracy trade-off
}

# Choose GPUs. Example uses GPU0 and GPU2:
devices = [0, 2]

results, timings = run_dynamic_two_gpus(pdf_path, pages_to_ocr, opts, devices=devices)

print(f"Pages OCRed: {len(results)}")
print(f"Total wall time: {timings['total']:.2f}s")
for g in devices:
    print(f"GPU{g}: {timings['pages_per_gpu'].get(g,0)} pages, {timings['per_gpu'].get(g,0.0):.2f}s")

# Access result per page
# results is [(page_no, text_list), ...] sorted by page_no
# Example preview
for pno, lines in results[:3]:
    print(f"\nPage {pno}:")
    print(lines[:5])
