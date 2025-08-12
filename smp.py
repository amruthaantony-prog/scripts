def extract_toc_links(doc, toc_page):
    page = doc.load_page(toc_page)
    toc_links = []

    # Pre-read all lines on the page so we can use them if get_textbox() is empty
    words = page.get_text("words")
    words.sort(key=lambda w: (w[1], w[0]))  # sort by y0, then x0
    lines = []
    cur = []
    cur_y = None
    for w in words:
        x0, y0, x1, y1, txt, *_ = w
        yc = (y0 + y1) / 2
        if cur and abs(yc - cur_y) > 2.0:  # new line
            lines.append({"text": " ".join(t[4] for t in cur), "y": cur_y})
            cur = []
        cur.append(w)
        cur_y = yc
    if cur:
        lines.append({"text": " ".join(t[4] for t in cur), "y": cur_y})

    # Go through all links
    for link in page.get_links():
        if "page" not in link:
            continue

        # Try normal way first
        text = page.get_textbox(link.get("from")) or ""

        if not text.strip():
            # Fallback: find nearest line vertically
            rect = link.get("from")
            link_y = (rect.y0 + rect.y1) / 2
            nearest = min(lines, key=lambda l: abs(l["y"] - link_y))
            text = nearest["text"]

        toc_links.append({
            "text": text.strip(),
            "page": int(link["page"])
        })

    return toc_links
