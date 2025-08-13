def _find_target_range(toc):
    ranges = []
    for lvl, name, start, end in toc:
        if _is_target(name):
            ranges.append((int(start), int(end)))
    return ranges  # can be multiple ranges

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
