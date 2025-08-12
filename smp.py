import re, unicodedata

_APOS_MAP = str.maketrans({
    "\u2019": "'",  # right single curly
    "\u2018": "'",  # left single curly
    "\u2032": "'",  # prime
    "\u02BC": "'",  # modifier letter apostrophe
})

_ALIAS_PATTERNS = [
    (re.compile(r"\bs\s*&\s*p\b", re.I), "sandp"),
    (re.compile(r"\bstandard\s*(?:&|and)\s*poors?\b", re.I), "sandp"),
    (re.compile(r"\bj\.?\s*p\.?\s*morgan\b", re.I), "jpmorgan"),
    (re.compile(r"\bubs\s*[~\-–]\s*\b", re.I), "ubs"),
    (re.compile(r"\bmoody\s*['’`]\s*s\b", re.I), "moodys"),
]

def normalize(text: str) -> str:
    if not text:
        return ""
    # unify apostrophes then NFKD -> ASCII
    t = text.translate(_APOS_MAP)
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode("ascii")
    t = t.lower()

    # alias rewrites (run BEFORE stripping non-alnum)
    for pat, repl in _ALIAS_PATTERNS:
        t = pat.sub(repl, t)

    # collapse punctuation/space and strip
    t = re.sub(r"[^a-z0-9]+", "", t)
    return t
