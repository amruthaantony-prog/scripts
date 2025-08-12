CREDIT_SOURCES = [
    "moody", "moody's", "moodys",
    "s&p", "s & p", "standard & poor's", "standard and poor's", "sandp", "snp",
    "s&p global ratings", "s&p global"
]

def canonicalize_credit_label(name: str) -> str:
    n = re.sub(r"[^a-z0-9]+", "", name.lower())
    if n.startswith("moody"):    return "Moody’s"
    if n.startswith("sp") or n.startswith("sandp") or n.startswith("standardandpoors"): 
        return "S&P"
    return name.strip().title()
def normalize_section_name(name):
    lowered = name.lower()

    # …your other rules…

    # If it's a generic credit heading, map to Credit Reports.
    # If it's a specific source (Moody’s / S&P), leave it to be grouped later.
    if "credit" in lowered and "report" in lowered:
        if any(k in lowered for k in ["moody", "s&p", "standard & poor", "standard and poor"]):
            return canonicalize_credit_label(name)   # keep source
        return "Credit Reports"

    return lowered.strip().title()


def is_source(label: str, keywords) -> bool:
    nn = re.sub(r"[^a-z0-9]+", "", label.lower())
    for k in keywords:
        nk = re.sub(r"[^a-z0-9]+", "", k.lower())
        if nn == nk or nn.startswith(nk) or nk.startswith(nn):
            return True
    return False

def merge_credit_reports_sections(toc, credit_keywords=None):
    if credit_keywords is None:
        credit_keywords = CREDIT_SOURCES

    credit_sections = []
    non_credit = []

    for entry in toc:  # [level, label, start, end]
        if is_source(entry[1], credit_keywords):
            credit_sections.append(entry)
        else:
            non_credit.append(entry)

    if not credit_sections:
        return toc

    # keep page order
    credit_sections.sort(key=lambda x: x[2])
    start_page = min(x[2] for x in credit_sections)
    end_page   = max(x[3] for x in credit_sections)

    # level 1 container
    grouped = [1, "Credit Reports", start_page, end_page]

    # level 2 children (canonicalized names)
    children = [[2, canonicalize_credit_label(c[1]), c[2], c[3]] for c in credit_sections]

    # reinsert in order before first section that starts after the block
    final = []
    inserted = False
    for section in non_credit:
        if not inserted and section[2] > start_page:
            final.append(grouped)
            final.extend(children)
            inserted = True
        final.append(section)
    if not inserted:
        final.append(grouped)
        final.extend(children)

    # ensure global order
    final.sort(key=lambda x: x[2])
    return final
