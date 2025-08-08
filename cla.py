def clean_toc_line(line: str):
    if not line:
        return None
    stripped = line.strip()

    # Remove numbering/bullet like i., 1., ii., etc.
    stripped = re.sub(r'^[ivxlc\d]+\.\s*', '', stripped, flags=re.IGNORECASE)

    # Remove line breaks
    stripped = stripped.replace('\n', ' ')

    # Remove dates like "2024.06.04", "2024-04-23", etc.
    stripped = re.sub(r'\d{4}[./-]\d{2}[./-]\d{2}', '', stripped)

    # Remove bracketed items like "(June 2024)" or "(2024)"
    stripped = re.sub(r'\(([^)]*)\)', '', stripped)

    # Remove extra spaces
    stripped = re.sub(r'\s+', ' ', stripped).strip()

    return stripped if stripped else None
def match_lines_to_links(toc_text, toc_links):
    matched = []
    
    # Clean both sides
    cleaned_toc_text = []
    for line in toc_text:
        cleaned = clean_toc_line(line)
        if cleaned:
            cleaned_toc_text.append(cleaned)
    
    cleaned_toc_links = []
    for link in toc_links:
        cleaned_link_text = clean_toc_line(link['text'])
        if cleaned_link_text:
            cleaned_toc_links.append({
                'text': cleaned_link_text,
                'page': link['page'],
                'original_text': link['text']
            })
    
    # Match with stricter criteria
    for toc_line in cleaned_toc_text:
        best_match = None
        best_score = 0
        
        for link in cleaned_toc_links:
            # Skip if already matched
            if any(link['page'] == m[1] for m in matched):
                continue
                
            toc_lower = toc_line.lower().strip()
            link_lower = link['text'].lower().strip()
            
            # Exact match gets highest priority
            if toc_lower == link_lower:
                best_match = (toc_line, link['page'])
                best_score = 100
                break
            
            # Avoid partial matches with just "bofa", "securities", etc.
            # Only allow partial matches if substantial overlap
            toc_words = set(toc_lower.split())
            link_words = set(link_lower.split())
            
            # Skip single word matches for these problematic terms
            if len(toc_words) == 1 and toc_lower in ['bofa', 'securities', 'ubs']:
                continue
                
            # Calculate word overlap
            common_words = toc_words.intersection(link_words)
            if len(common_words) >= 2:  # At least 2 words in common
                score = len(common_words) / max(len(toc_words), len(link_words))
                if score > best_score:
                    best_match = (toc_line, link['page'])
                    best_score = score
        
        if best_match:
            matched.append(best_match)
            print(f"MATCH: '{best_match[0]}' -> page {best_match[1]}")
    
    return matched

import re

def clean_toc_line(line):
    if not line or len(line.strip()) < 4:
        return None

    stripped = line.strip()

    # Remove common date patterns
    stripped = re.sub(r"\b(20\d{2}[.\-/]\d{2}[.\-/]?\d{0,2})\b", "", stripped)      # 2024.04.23, 2024-04-23, 2024/04/23
    stripped = re.sub(r"\b(Q[1-4]\s*20\d{2})\b", "", stripped, flags=re.IGNORECASE) # Q1 2024
    stripped = re.sub(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\b", "", stripped, flags=re.IGNORECASE)  # Jan 2024
    stripped = re.sub(r"\b(20\d{2})\b", "", stripped)                                # 2025
    stripped = re.sub(r"\(\s*[^)]*\s*\)", "", stripped)                              # Remove anything in brackets like (12.31.2024)
    stripped = re.sub(r"\[\s*[^]]*\s*\]", "", stripped)                              # Remove anything in square brackets

    # Remove extra spaces and punctuation-only lines
    stripped = re.sub(r"\s+", " ", stripped).strip()
    if len(stripped) < 4 or re.match(r"^[^\w]*$", stripped):
        return None

    return stripped
import fitz
import numpy as np
import re

# BROKER list for Equity Research grouping

BROKER_NAMES = [
“jpmorgan”, “morgan stanley”, “nomura”, “bnp paribas”,
“bofa global research”, “goldman sachs”, “ubs”, “barclays”, “hsbc”, “jefferies”,
“credit suisse”, “citigroup”, “rbc”, “evercore”, “wells fargo”, “oppenheimer”,
“scotiabank”, “william blair”, “deutsche bank”
]

def find_toc_page(doc):
for page_num in range(min(3, len(doc))):
page = doc.load_page(page_num)
links = page.get_links()
if len(links) > 5:
return page_num
return 0

def extract_toc_links(doc, toc_page):
toc_links = []
page = doc.load_page(toc_page)
for link in page.get_links():
if “page” in link:
text = page.get_textbox(link.get(“from”)) or “”
toc_links.append({
“text”: text.strip(),
“page”: int(link[“page”])
})
return toc_links

def extract_toc_text(doc, toc_page):
page = doc.load_page(toc_page)
pix = page.get_pixmap(dpi=500)
image_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
lines = reader.readtext(image_array, detail=0)
return lines

def strip_dates(text):
return re.sub(r’(?\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[^)]*)?’, ‘’, text).strip()

def match_lines_to_links(toc_text, toc_links):
matched = []
for line in toc_text:
stripped_line = line.strip()
if not stripped_line or len(stripped_line) < 4:
continue
if re.match(r”^[A-Da-d]?$”, stripped_line):
continue
cleaned_line = strip_dates(stripped_line.lower())
for link in toc_links:
link_text = strip_dates(link[‘text’].lower())
if cleaned_line in link_text:
matched.append((stripped_line, link[“page”]))
break
return matched

def normalize_section_name(name):
lowered = name.lower()

```
if "investor" in lowered:
    return "Investor Presentation"
if "transcript" in lowered or "call" in lowered:
    return "Earnings Transcript"
if "press" in lowered or "presentation" in lowered:
    return "Earnings Release"
if "news" in lowered:
    return "Recent News"
if "equity" in lowered:
    return "Equity Research"
if "form" in lowered:  # Preserve Forms section naming
    return name.strip()
return name.title()
```

def build_final_toc(matched, total_pages):
result = []
for i, (name, start_page) in enumerate(matched):
end_page = matched[i + 1][1] - 1 if i + 1 < len(matched) else total_pages - 1
if end_page < start_page:
end_page = start_page  # Fix invalid range
label = normalize_section_name(name)
result.append([1, label, start_page, end_page])
return result

def clean_broker_name(name):
“””
Clean broker names by removing dates and normalizing format.
“””
# Remove dates in parentheses
name = re.sub(r’\s*([^)]*)’, ‘’, name)

```
# Normalize common broker names
name_lower = name.lower().strip()

if "jp morgan" in name_lower or "jpmorgan" in name_lower:
    return "JP Morgan"
elif "morgan stanley" in name_lower:
    return "Morgan Stanley"
elif "bofa" in name_lower or "bank of america" in name_lower:
    return "BofA Global Research"
elif "deutsche bank" in name_lower:
    return "Deutsche Bank"
elif "william blair" in name_lower:
    return "William Blair"
elif "oppenheimer" in name_lower:
    return "Oppenheimer & Co"
elif "scotiabank" in name_lower:
    return "Scotiabank"
elif "rbc" in name_lower:
    return "RBC Capital Markets"
elif "wells fargo" in name_lower:
    return "Wells Fargo"
elif "barclays" in name_lower:
    return "Barclays"
elif "nomura" in name_lower:
    return "Nomura"
elif "bnp paribas" in name_lower:
    return "BNP Paribas"
elif "goldman sachs" in name_lower:
    return "Goldman Sachs"
elif "ubs" in name_lower:
    return "UBS"
elif "hsbc" in name_lower:
    return "HSBC"
elif "jefferies" in name_lower:
    return "Jefferies"
elif "credit suisse" in name_lower:
    return "Credit Suisse"
elif "citigroup" in name_lower or "citi" in name_lower:
    return "Citigroup"
elif "evercore" in name_lower:
    return "Evercore"
else:
    return name.strip().title()
```

def group_equity_research_hierarchically(toc_list):
“””
Group equity research sections hierarchically instead of merging them.
Main “Equity Research” becomes level 1, individual brokers become level 2.
“””
result = []
i = 0

```
while i < len(toc_list):
    current_item = toc_list[i]
    label = current_item[1].lower()
    
    if label == "equity research":
        # Add the main Equity Research section as level 1
        result.append(current_item)
        i += 1
        
        # Process following broker sections as level 2
        while i < len(toc_list) and any(broker in toc_list[i][1].lower() for broker in BROKER_NAMES):
            broker_item = toc_list[i].copy()
            broker_item[0] = 2  # Set level to 2 for broker subsections
            # Clean up broker name - remove dates
            broker_item[1] = clean_broker_name(broker_item[1])
            result.append(broker_item)
            i += 1
    else:
        result.append(current_item)
        i += 1

return result
```

def merge_consecutive_items(items):
“””
Merge consecutive items with same level and name.

```
Args:
    items: List of lists where each inner list is [level, name, start_page, end_page]

Returns:
    List of merged items
"""
if not items:
    return items

merged = []
current_item = items[0][:]  # Make a copy of the first item

for i in range(1, len(items)):
    item = items[i]
    
    # Check if current item should be merged with the previous one
    if (current_item[0] == item[0] and  # Same level
        current_item[1] == item[1]):     # Same name
        
        # Merge by extending the page range
        # Keep the start page from current_item, update end page to item's end page
        current_item[3] = item[3]
    else:
        # Different item, so add the current_item to merged list and start new one
        merged.append(current_item)
        current_item = item[:]  # Make a copy of the new item

# Don't forget to add the last item
merged.append(current_item)

return merged
```

def merge_adjacent_same_labels(toc_list):
“””
Legacy function - now handled by merge_consecutive_items
“””
return merge_consecutive_items(toc_list)

def process_pdf(pdf_path):
with fitz.open(pdf_path) as doc:
total_pages = len(doc)
toc_page = find_toc_page(doc)
toc_links = extract_toc_links(doc, toc_page)
toc_text = extract_toc_text(doc, toc_page)
matched = match_lines_to_links(toc_text, toc_links)
final = build_final_toc(matched, total_pages)

```
    # Use the new hierarchical grouping instead of merging
    final = group_equity_research_hierarchically(final)
    final = merge_consecutive_items(final)
    
    return final
```

# Example usage:

# pdf_path = “wm.pdf”

# toc_output = process_pdf(pdf_path)

# print(“Table of Contents:”)

# for item in toc_output:

# indent = “  “ * (item[0] - 1)

# print(f”{indent}[{item[0]}] {item[1]}: pages {item[2]}-{item[3]}”)