import re, fitz

WORD_RE = re.compile(r"[A-Za-z]{2,}")  # keep as a cheap English proxy

def needs_ocr(
    page,
    min_letters=30,
    min_words=5,
    img_area_ratio=0.60,
    include_drawings=True,          # treat vector drawings as “image”
    min_block_area_ratio=0.02,      # ignore tiny image/drawing blocks (<2% page)
) -> bool:
    # 1) quick linguistic signal
    txt = page.get_text("text") or ""
    letters = sum(ch.isalpha() for ch in txt)
    words = len(WORD_RE.findall(txt))

    if letters >= min_letters and words >= min_words:
        return False  # good text → no OCR

    # 2) structural signal from layout
    info = page.get_text("rawdict") or {}
    page_area = float(page.rect.get_area()) or 1.0
    img_area = 0.0

    for blk in info.get("blocks", []):
        t = blk.get("type")
        if t == 1 or (include_drawings and t == 2):
            area = fitz.Rect(blk["bbox"]).get_area()
            if (area / page_area) >= min_block_area_ratio:  # skip icons / stamps
                img_area += area

    if (img_area / page_area) >= img_area_ratio:
        return True  # mostly an image/vector → OCR

    # 3) fallback: junky text (non-linguistic)
    if not txt:
        return True

    non_space_len = sum(not ch.isspace() for ch in txt) or 1
    alpha_ratio = letters / non_space_len
    printable_ratio = sum(ch.isprintable() for ch in txt) / len(txt)

    # add avg word length as a weak extra signal (numbers/symbol soup → low)
    avg_word_len = (letters / max(words, 1)) if words else 0.0

    return (
        alpha_ratio < 0.25
        or printable_ratio < 0.5
        or avg_word_len < 3.0  # many short tokens → likely noise
    )



def get_page_blocks(page):
    if needs_ocr(page):
        tp = page.get_textpage_ocr(flags=0, language="eng", dpi=300, full=False)
        return tp.extractBLOCKS()
    else:
        return page.get_text("blocks")
