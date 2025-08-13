import re

_WORD = re.compile(r"[A-Za-z]{2,}")
_UESC = re.compile(r"\\u[0-9a-fA-F]{4}")              # \uXXXX runs
_HEX_PAREN_RUN = re.compile(r"(?:\([0-9A-Fa-f:]{2,}\)){8,}")  # (…) repeated many times

def looks_like_garbage(s: str) -> bool:
    if not s:
        return True
    n = len(s)
    ascii_letters = sum(ch.isalpha() and ord(ch) < 128 for ch in s)
    words = len(_WORD.findall(s))
    non_ascii = sum(ord(ch) >= 128 for ch in s)
    punct_ratio = sum(ch in "{}[]():;|\\/" for ch in s) / n
    unique_ratio = len(set(s)) / n
    uesc_hits = len(_UESC.findall(s))
    hexparen = bool(_HEX_PAREN_RUN.search(s))

    # triggers
    if words < 5 and ascii_letters < 30:            # almost no linguistic content
        return True
    if non_ascii / n > 0.50:                        # mostly non-ASCII
        return True
    if punct_ratio > 0.25 and ascii_letters / n < 0.05:
        return True
    if uesc_hits > 50 or hexparen:                  # long \uXXXX or (..) hex runs
        return True
    if unique_ratio < 0.05:                         # same chars over and over
        return True
    return False





import re
def _norm(s): return re.sub(r'[^a-z0-9]+', '', str(s).lower())
def _is_target(name):   # adjust as needed
    n = _norm(name)
    return '10k' in n or '10q' in n or 'equityresearch' in n

def _find_target_ranges(tocs):
    ranges = []
    for i, item in enumerate(tocs):
        # accept only list/tuple with at least 4 fields: [level, name, start, end]
        if not isinstance(item, (list, tuple)) or len(item) < 4:
            # skip dicts/short rows quietly (or log if you want)
            continue
        _, name, start, end = item[:4]
        try:
            if _is_target(name):
                ranges.append((int(start), int(end)))
        except Exception:
            continue
    return ranges

target_ranges = _find_target_range(tocs)

if target_ranges:
    page_list = sorted(
        {t['page_number'] for t in tables
         if 'page_number' in t and any(start <= t['page_number'] <= end for start, end in target_ranges)}
    )
    llm_results = refine_plumber_tables_with_llm(file_name, tables_subset, hf_llm, rs1, tocs)
else:
    # fallback: run 517–529 code for all tables
    for table in tables:
        if 'page_number' not in table:
            print(f"Skipping table due to missing 'page_number': {table}")
            continue
        flattened_text = pdf_toc.flatten_table_to_text(table['data'])
        rs1.append({
            'title': table.get('title', ''),
            'page_no': table['page_number'],
            'block_no_from': 0,
            'block_no_to': 0,
            'coordinates': str(table.get('coordinates', 'Rect(0, 0, 0, 0)')),
            'text': flattened_text,
        })
