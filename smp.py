%%writefile two_gpu_easyocr_helper.py
import os
import multiprocessing as mp
import easyocr

def _worker(gpu_id, pages_subset, global_indices, opts, out_q):
    # Bind this process to one GPU (must be set before Reader is created)
    os.environ["CUDA_VISIBLE_DEVICES"] = str(gpu_id)

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
        txt = reader.readtext(page, detail=0, paragraph=False)  # tweak kwargs as you like
        results.append((gi, txt))
    out_q.put(results)

def run_two_readers_half_split(pages, opts=None):
    """
    Always launches two Readers: GPU0 and GPU1.
    Splits `pages` list into first half -> GPU0, second half -> GPU1.
    Returns results aligned to original order (list per page).
    """
    opts = opts or {}
    n = len(pages)
    if n == 0:
        return []

    # Use spawn for safety across platforms
    mp.set_start_method("spawn", force=True)
    mid = n // 2
    part0, part1 = pages[:mid], pages[mid:]

    ctx = mp.get_context("spawn")
    q = ctx.Queue()

    procs = [
        ctx.Process(target=_worker, args=(0, part0, list(range(0, mid)), opts, q), daemon=True),
        ctx.Process(target=_worker, args=(1, part1, list(range(mid, n)), opts, q), daemon=True),
    ]

    for p in procs: p.start()

    collected = []
    for _ in procs:
        try:
            collected.extend(q.get())  # one payload per worker
        except Exception:
            pass

    for p in procs: p.join()

    collected.sort(key=lambda t: t[0])
    ordered = [r for _, r in collected]

    # Pad if something returned nothing (rare)
    if len(ordered) < n:
        m = {i: r for i, r in collected}
        ordered = [m.get(i, []) for i in range(n)]
    return ordered


from two_gpu_easyocr_helper import run_two_readers_half_split

easyocr_model_storage_dir = "../easyocr/"  # your path
opts = {
    "langs": ["en"],
    "model_storage_directory": easyocr_model_storage_dir,
    "download_enabled": False,
    "verbose": False,
    # "quantize": True,  # optional VRAM saver
}

# pages = [...]  # list of image file paths OR numpy arrays for each page
results = run_two_readers_half_split(pages, opts)
print(f"OCR pages: {len(results)}")
