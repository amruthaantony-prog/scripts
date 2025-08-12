import re
from typing import List, Tuple, Dict, Iterable

# ----------------------------
# Canonicalization helpers
# ----------------------------

# Lightweight ASCII un-curly for quotes/apostrophes and dashes
_ASCII_MAP = str.maketrans({
    "\u2019": "'",  # right single quote
    "\u2018": "'",  # left single quote
    "\u2032": "'",  # prime
    "\u02BC": "'",  # modifier letter apostrophe
    "\u2013": "-",  # en dash
    "\u2014": "-",  # em dash
})

# Regex aliases -> canonical form (lowercase)
_ALIAS_RULES: List[Tuple[re.Pattern, str]] = [
    # JP Morgan variants
    (re.compile(r"\bJ\.?\s*P\.?\s*Morgan\b", re.I), "jpmorgan"),
    (re.compile(r"\bJPM\s*Morgan\b", re.I), "jpmorgan"),
    # UBS quirks
    (re.compile(r"\bUBS\s*[~\-–]\s*", re.I), "ubs "),
    # BofA variants
    (re.compile(r"\bB(?:ank\s*of\s*America|ofA)\b", re.I), "bofa"),
    # S&P variants
    (re.compile(r"\bS\s*&\s*P\b", re.I), "s&p"),
    (re.compile(r"\bStandard\s*&?\s*Poor['’]s?\b", re.I), "s&p"),
    (re.compile(r"\bS\s*and\s*P\b", re.I), "s&p"),
    # Moody's variants
    (re.compile(r"\bMoody['’]?\s*s\b", re.I), "moody's"),
    (re.compile(r"\bMoodys\b", re.I), "moody's"),
    # Deutsche/Scotia/RBC abbreviations (kept readable; helps overlap)
    (re.compile(r"\bDeutsche\s*Bank\b", re.I), "deutsche bank"),
    (re.compile(r"\bScotia\s*bank\b", re.I), "scotiabank"),
    (re.compile(r"\bRBC\s*Capital\s*Markets\b", re.I), "rbc capital markets"),
]

# Words to ignore as *solo* matches (common false positives)
_BAD_SOLO = {"bofa", "securities", "research", "report", "reports", "recent", "materials", "presentation"}

# Names that can legitimately be single-token brokers/credit sources
_ALLOWED_SOLO = {
    # brokers
    "jefferies", "nomura", "barclays", "ubs", "scotiabank", "deutsche", "deutsche bank",
    "william blair", "evercore", "oppenheimer", "citigroup", "goldman sachs", "jpmorgan",
    "rbc", "rbc capital markets", "hsbc", "bnp paribas",
    # credit sources
    "moody's", "s&p", "fitch"
}

def _canon(s: str) -> str:
    """Light canonicalization: un-curly, apply alias rules, collapse spaces."""
    s2 = (s or "").translate(_ASCII_MAP)
    for pat, rep in _ALIAS_RULES:
        s2 = pat.sub(rep, s2)
    # collapse odd punctuation around '&' (already handled for S&P above)
    s2 = re.sub(r"[^\w&]+", " ", s2.lower()).strip()
    s2 = re.sub(r"\s+", " ", s2)
    return s2

def _normalize_key(s: str) -> str:
    """Aggressive normalization used for comparisons (keep a–z0–9 & spaces)."""
    s2 = _canon(s)
    s2 = re.sub(r"[^a-z0-9 ]+", "", s2)  # drop leftover punctuation incl. ampersands
    s2 = re.sub(r"\s+", " ", s2).strip()
    return s2

def _tokens(s: str) -> List[str]:
    return [t for t in _normalize_key(s).split() if t]

def _has_keyword(text: str, keywords: Iterable[str]) -> bool:
    t = _normalize_key(text)
    return any(k in t for k in keywords)

# ----------------------------
# Matching
# ----------------------------

def match_lines_to_links(
    toc_text: List[str],
    toc_links: List[Dict],
    BROKER_KEYWORDS: Iterable[str] = (),
    CREDIT_KEYWORDS: Iterable[str] = (),
) -> List[Tuple[str, int]]:
    """
    Robust matching between OCR TOC lines and PDF link rectangles.
    - Cleans both sides with clean_toc_line (your existing function) + light canonicalization
    - Uses alias-aware normalization and token overlap scoring
    - Allows 1-word matches only for known broker/credit names; blocks common false-positives
    """
    matched: List[Tuple[str, int]] = []

    # Clean both sides with your cleaner, then canonicalize
    cleaned_toc_text: List[str] = []
    for line in toc_text:
        cleaned = clean_toc_line(line)
        if cleaned:
            cleaned_toc_text.append(cleaned)

    cleaned_toc_links: List[Dict] = []
    for link in toc_links:
        cl = clean_toc_line(link.get("text", ""))
        if not cl:
            continue
        cleaned_toc_links.append({
            "text": cl,
            "page": link["page"],
            "original_text": link.get("text", cl),
        })

    # Precompute normalized keys/tokens for links once
    link_cache = []
    for link in cleaned_toc_links:
        lk = _normalize_key(link["text"])
        link_cache.append({
            "norm": lk,
            "tokens": set(lk.split()),
            "page": link["page"],
            "text": link["text"],
        })

    broker_norms = {_normalize_key(b) for b in (BROKER_KEYWORDS or [])}
    credit_norms = {_normalize_key(c) for c in (CREDIT_KEYWORDS or [])}
    allowed_solo = _ALLOWED_SOLO | broker_norms | credit_norms

    # Helper to decide if a toc line describes a broker/credit child
    def is_broker_or_credit(t: str) -> bool:
        nk = _normalize_key(t)
        return any(k in nk for k in broker_norms | credit_norms)

    # Avoid “one link per page” restriction — but do avoid exact duplicates
    seen_pairs = set()  # {(norm_text, page)}

    for toc_line in cleaned_toc_text:
        best = None
        best_score = -1

        t_norm = _normalize_key(toc_line)
        t_tokens = set(t_norm.split())

        # Skip empty after normalization
        if not t_norm:
            continue

        # forbid bad solo words
        if len(t_tokens) == 1:
            solo = next(iter(t_tokens))
            if solo in _BAD_SOLO and solo not in allowed_solo:
                continue

        for link in link_cache:
            pair_key = (t_norm, link["page"])
            if pair_key in seen_pairs:
                continue

            # Hard exact equality first
            if t_norm == link["norm"]:
                best = (toc_line, link["page"])
                best_score = 999
                break

            # Containment helps with extra qualifiers (dates, “initiating coverage”, etc.)
            if t_norm in link["norm"] or link["norm"] in t_norm:
                score = 500 + min(len(t_norm), len(link["norm"]))
                if score > best_score:
                    best = (toc_line, link["page"])
                    best_score = score
                continue

            # Token overlap scoring (Jaccard-ish)
            common = t_tokens & link["tokens"]
            # Thresholds
            need = 1 if (is_broker_or_credit(toc_line) or any(tok in allowed_solo for tok in t_tokens)) else 2
            if len(common) >= need:
                # normalize by length to avoid short wins
                denom = max(len(t_tokens), len(link["tokens"])) or 1
                score = int(100 * len(common) / denom)
                if score > best_score:
                    best = (toc_line, link["page"])
                    best_score = score

        if best:
            matched.append(best)
            seen_pairs.add((_normalize_key(best[0]), best[1]))

    return matched
