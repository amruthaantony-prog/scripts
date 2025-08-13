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
