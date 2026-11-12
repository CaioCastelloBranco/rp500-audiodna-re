# --- portable path resolution (added 2026-11-10) ---------------------------
import os as _os

_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_SW = _os.path.dirname(_os.path.abspath(__file__))

_FW = _os.path.join(_ROOT, "01_source_firmware")


def _OUT(name):
    """Route derived/output artifacts to the script directory."""
    return _os.path.join(_SW, name)


def _P(name):
    """Resolve an analysis artifact inside this archive (no absolute paths)."""
    _ALIAS = {"gsp_fw.bin": "gsp1101_fw.bin", "rp_fw.bin": "rp500_fw.bin"}
    name = _ALIAS.get(name, name)
    if name.endswith(".exe"):
        _dir = _os.path.join(_ROOT, "02_source_binaries")
    elif name.endswith(".pdf"):
        _dir = _os.path.join(_ROOT, "03_docs")
    else:
        _dir = _os.path.join(_ROOT, "01_source_firmware")
    p = _os.path.join(_dir, name)
    if _os.path.exists(p):
        return p
    q = _os.path.join(_SW, name)
    if _os.path.exists(q) or "%" in name or name.endswith(".txt"):
        return q
    return p

# ---------------------------------------------------------------------------
import re

up = open(_P("JUpdater Gsp1101vC63.exe"),'rb').read()

def strings(data, minlen=4):
    out=[]; cur=bytearray(); start=0
    for i,c in enumerate(data):
        if 32 <= c <= 126:
            if not cur: start=i
            cur.append(c)
        else:
            if len(cur)>=minlen: out.append((start,cur.decode('ascii')))
            cur=bytearray()
    if len(cur)>=minlen: out.append((start,cur.decode('ascii')))
    return out

allstr = strings(up, 4)
print("=== URLs / hosts ===")
for off,s in allstr:
    low = s.lower()
    if any(k in low for k in ["http", "www.", ".com", ".net", "ftp", "digitech", "harman", "update", "version", "download"]):
        print("0x%06X %s" % (off, s[:200]))

print("=== version-ish ===")
for off,s in allstr:
    if re.search(r'\b\d+\.\d+(\.\d+)?\b', s) and len(s) < 80:
        print("0x%06X %s" % (off, s))

print("=== URL-ish byte patterns ===")
for m in re.finditer(rb'https?://[^\x00-\x20\x7f]{4,200}', up):
    print(hex(m.start()), m.group().decode('ascii','replace'))
for m in re.finditer(rb'[A-Za-z0-9.-]+\.(?:com|net|org)[/A-Za-z0-9._~-]*', up):
    print(hex(m.start()), m.group().decode('ascii','replace'))
