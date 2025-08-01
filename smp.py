matched_info = []
    for lst in page_map:
        start = lst[0]
        end = lst[-3] if isinstance(lst[-3], int) else lst[0]  # In case second last item isn't numeric
        if start <= item['page_no'] <= end:
            info = f"{lst[0]}, {lst[-2]}, {lst[-1]}"
            matched_info.append(info)
