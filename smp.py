# two_gpu_half_split_easyocr.py
import os
import multiprocessing as mp

def _worker(gpu_id, pages_subset, global_indices, opts, out_q):
    # Bind before importing EasyOCR
    os.environ["CUDA_VISIBLE_DEVICES"] = str(gpu_id)
    import easyocr

    reader = easyocr.Reader(
        opts.get("langs", ["en"]),
        gpu=True,
        model_storage_directory=opts.get("model_storage_directory"),
        download_enabled=opts.get("download_enabled", False),
        quantize=opts.get("quantize", False),
        verbose=opts.get("verbose", False),
    )

    results = []
    for gi, page in zip(global_indices, pages_subset):
        txt = reader.readtext(page, detail=0, paragraph=False)
        results.append((gi, txt))
    out_q.put(results)

def run_two_readers_half_split(pages, opts=None):
    """
    Always launches two readers: GPU0 and GPU1.
    Splits `pages` into first half (GPU0) and second half (GPU1).
    Returns OCR results aligned to the original order: list[list[str]] per page.
    """
    opts = opts or {}
    n = len(pages)
    mid = n // 2  # first half size
    part0 = pages[:mid]
    part1 = pages[mid:]

    ctx = mp.get_context("spawn")
    q = ctx.Queue()

    p0 = ctx.Process(target=_worker,
                     args=(0, part0, list(range(0, mid)), opts, q),
                     daemon=True)
    p1 = ctx.Process(target=_worker,
                     args=(1, part1, list(range(mid, n)), opts, q),
                     daemon=True)

    p0.start(); p1.start()

    collected = []
    # Expect two payloads (one per worker). If a half is empty, that worker returns nothing.
    for _ in range(2):
        try:
            collected.extend(q.get(timeout=1_000))  # generous timeout
        except Exception:
            pass

    p0.join(); p1.join()

    collected.sort(key=lambda t: t[0])                # sort by global index
    ordered = [r for _, r in collected]               # strip indices
    # If any pages were empty (e.g., odd cases), pad to length n
    if len(ordered) < n:
        # create an index->result map, then rebuild
        m = {i: r for i, r in collected}
        ordered = [m.get(i, []) for i in range(n)]
    return ordered

if __name__ == "__main__":
    # Fill this with your page images (paths or numpy arrays)
    pages = []  # e.g., ["p1.png","p2.png", ...] or arrays

    easyocr_model_storage_dir = "../easyocr/"
    opts = {
        "langs": ["en"],
        "model_storage_directory": easyocr_model_storage_dir,
        "download_enabled": False,
        "verbose": False,
        # "quantize": True,  # optional VRAM saver
    }

    results = run_two_readers_half_split(pages, opts)
    print(f"OCR pages: {len(results)}")
