import re

_CID = re.compile(r"\(\s*cid\s*:\s*[0-9A-Fa-f]+\s*\)", re.I)
_CID_RUN = re.compile(r"(?:\(\s*cid\s*:\s*[0-9A-Fa-f]+\s*\)){8,}", re.I)  # long runs

def is_cid_garbage(s: str) -> bool:
    if not s: 
        return True
    n = len(s)
    cid_cnt = len(_CID.findall(s))
    if cid_cnt >= 10:
        return True
    if _CID_RUN.search(s):
        return True
    # if >20% of chars belong to cid tokens → garbage
    approx_cid_chars = cid_cnt * 8  # "(cid:123)" ~ 8–10 chars
    return approx_cid_chars / max(n,1) > 0.20

def strip_cid(s: str) -> str:
    return _CID.sub("", s)
