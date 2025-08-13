import re 

def _norm(s):  # normalize names
    return re.sub(r'[^a-z0-9]+', '', s.lower())

def _is_target(name):
    n = _norm(name)
    return ('10k' in n) or ('equityresearch' in n)

def _pages_from_toc(toc):
    pages = set()
    for lvl, name, start, end in toc:
        if _is_target(name):
            pages.update(range(int(start), int(end) + 1))
    return pages

# build page sets
all_table_pages = {t.get('page_number') for t in tables if 'page_number' in t}
target_pages = _pages_from_toc(tocs)
filtered_pages = sorted(all_table_pages & target_pages)

if filtered_pages:
    # run LLM only on 10-K / Equity Research pages
    tables_subset = [t for t in tables if t.get('page_number') in filtered_pages]
    llm_results = refine_plumber_tables_with_llm(file_name, tables_subset, hf_llm, rs1, tocs)
else:
    # no 10-K in TOC → run lines 517–529 fallback for all tables
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
