for item in rs2:
    # Find all matching entries
    matched_info = [
        f"page_start:{start}, page_end:{end}, title:{title}"
        for start, end, title in page_map
        if start <= item['page_no'] <= end
    ]
    
    # Join if multiple matches
    extra_ref = " | ".join(matched_info) if matched_info else ""
