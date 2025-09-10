%%writefile two_gpu_easyocr_stream.py
import os, time, multiprocessing as mp
import fitz  # PyMuPDF
import numpy as np
import easyocr

def _warmup_reader(reader):
    dummy = np.zeros((32, 32, 3), dtype=np.uint8)
    try:
        reader.readtext(dummy, detail=0, paragraph=False)
    except Exception:
        pass

def _worker(gpu_id, pdf_path, task_q, res_q, opts):
    # Pin to GPU before creating the Reader
    os.environ["CUDA_VISIBLE_DEVICES"] = str(gpu_id)

    reader = easyocr.Reader(
        opts.get("langs", ["en"]),
        gpu=True,
        model_storage_directory=opts.get("model_storage_directory"),
        download_enabled=opts.get("download_enabled", False),
        quantize=opts.get("quantize", False),
        verbose=opts.get("verbose", False),
    )
    _warmup_reader(reader)

    # Open PDF once per worker
    doc = fitz.open(pdf_path)
    dpi = int(opts.get("dpi", 200))
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)

    start = time.perf_counter()
    processed = 0

    while True:
        item = task_q.get()
        if item is None:
            break
        pno = int(item)
        page = doc.load_page(pno)
        pix = page.get_pixmap(matrix=mat, alpha=False)  # RGB
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)

        txt = reader.readtext(img, detail=0, paragraph=False)
        res_q.put((pno, txt, gpu_id))
        processed += 1

    doc.close()
    elapsed = time.perf_counter() - start
    res_q.put(("__worker_done__", gpu_id, processed, elapsed))

def run_dynamic_two_gpus_stream(pdf_path, page_numbers, opts=None, devices=None, msg_timeout=120):
    """
    pdf_path: str
    page_numbers: list[int] (0-based)
    opts: {"langs": ["en"], "model_storage_directory": "...", "download_enabled": False,
           "verbose": False, "quantize": False, "dpi": 200}
    devices: GPUs to use, e.g., [0,1] or [0,2]; set to [0] to force single-GPU.

    Returns:
      results_sorted: [(page_no, text_list), ...]
      timings: {"total": float, "per_gpu": {gpu_id: secs}, "pages_per_gpu": {gpu_id: count}}
    """
    if opts is None: opts = {}
    if devices is None: devices = [0, 1]
    nums = sorted(set(int(n) for n in page_numbers))
    if not nums:
        return [], {"total": 0.0, "per_gpu": {}, "pages_per_gpu": {}}

    mp.set_start_method("spawn", force=True)
    ctx = mp.get_context("spawn")
    task_q = ctx.Queue()
    res_q = ctx.Queue()

    # Enqueue tasks + sentinels
    for n in nums:
        task_q.put(n)
    for _ in devices:
        task_q.put(None)

    # Spin workers
    procs = []
    for g in devices:
        p = ctx.Process(target=_worker, args=(g, pdf_path, task_q, res_q, opts), daemon=True)
        p.start()
        procs.append(p)

    # Collect results with timeout (prevents infinite hang)
    t0 = time.perf_counter()
    results = []
    per_gpu_time = {g: 0.0 for g in devices}
    pages_per_gpu = {g: 0 for g in devices}
    expected_msgs = len(nums) + len(devices)
    received = 0

    while received < expected_msgs:
        try:
            msg = res_q.get(timeout=msg_timeout)
            received += 1
            if isinstance(msg, tuple) and msg and msg[0] == "__worker_done__":
                _, g, count, elapsed = msg
                per_gpu_time[g] = elapsed
                pages_per_gpu[g] = count
            else:
                pno, txt, g = msg
                results.append((pno, txt))
        except Exception:
            # Timed out waiting—break to clean up
            break

    # Best-effort drain (non-blocking)
    try:
        while True:
            msg = res_q.get_nowait()
            if isinstance(msg, tuple) and msg and msg[0] == "__worker_done__":
                _, g, count, elapsed = msg
                per_gpu_time[g] = elapsed
                pages_per_gpu[g] = count
            else:
                pno, txt, g = msg
                results.append((pno, txt))
    except Exception:
        pass

    # Join/terminate
    for p in procs:
        p.join(timeout=10)
    for p in procs:
        if p.is_alive():
            p.terminate()

    total_elapsed = time.perf_counter() - t0
    results.sort(key=lambda x: x[0])
    timings = {"total": total_elapsed, "per_gpu": per_gpu_time, "pages_per_gpu": pages_per_gpu}
    return results, timings
