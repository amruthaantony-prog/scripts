import re, string, fitz

WORD_RE = re.compile(r"[A-Za-z]{2,}")  # cheap English proxy

def _text_quality_signals(txt: str):
    if not txt:
        return {
            "empty": True, "letters": 0, "words": 0,
            "ascii_ratio": 0.0, "printable_ratio": 0.0,
            "space_ratio": 0.0, "avg_word_len": 0.0
        }
    letters = sum(ch.isalpha() for ch in txt)
    words = len(WORD_RE.findall(txt))
    printable = sum(ch.isprintable() for ch in txt)
    ascii_chars = sum((ch in string.printable) for ch in txt)
    spaces = sum(ch.isspace() for ch in txt)
    nonspace_len = max(1, len(txt))
    return {
        "empty": False,
        "letters": letters,
        "words": words,
        "ascii_ratio": ascii_chars / nonspace_len,        # high on real text
        "printable_ratio": printable / nonspace_len,      # low on binary junk
        "space_ratio": spaces / nonspace_len,             # near 0 if no word gaps
        "avg_word_len": (letters / max(1, words))         # ~4–6 on real English
    }

def needs_ocr(
    page,
    min_letters=30,
    min_words=5,
    img_area_ratio=0.60,
    include_drawings=True,          # count vector drawings as “image”
    min_block_area_ratio=0.02       # ignore tiny logos/stamps (<2% page)
) -> bool:
    # --- 1) Linguistic signal (stronger junk guard) ---
    txt = page.get_text("text") or ""
    sig = _text_quality_signals(txt)

    if sig["empty"]:
        linguistic_ok = False
    else:
        # “Good text” requires ALL of these to be believable:
        linguistic_ok = (
            sig["letters"] >= min_letters and
            sig["words"]   >= min_words and
            sig["ascii_ratio"]     >= 0.78 and     # binary-looking blobs fail here
            sig["printable_ratio"] >= 0.90 and
            sig["space_ratio"]     >= 0.08 and     # must have spaces between words
            sig["avg_word_len"]    >= 3.0
        )

    if linguistic_ok:
        return False  # looks like real text → no OCR

    # --- 2) Layout signal: images/drawings coverage ---
    info = page.get_text("rawdict") or {}
    page_area = float(page.rect.get_area()) or 1.0
    img_area = 0.0

    for blk in info.get("blocks", []):
        t = blk.get("type")
        if t == 1 or (include_drawings and t == 2):  # 1=image, 2=vector drawing
            area = fitz.Rect(blk["bbox"]).get_area()
            if (area / page_area) >= min_block_area_ratio:
                img_area += area

    if (img_area / page_area) >= img_area_ratio:
        return True   # mostly image/vector → OCR

    # --- 3) If text was junky but page isn't image-heavy, still OCR ---
    return True
