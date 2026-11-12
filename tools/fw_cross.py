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
fw = open(_P("gsp1101_fw.bin"),'rb').read()
up = open(_P("JUpdater Gsp1101vC63.exe"),'rb').read()
rp = open(_P("rp500_fw.bin"),'rb').read()

def longest_common(desc, a, b):
    best = (0, -1, -1)
    for step in (4096, 1024, 256):
        n = len(a)
        for off in range(0, n, step):
            chunk = a[off:off+step]
            if len(chunk) < 128: continue
            idx = b.find(chunk)
            if idx >= 0:
                end = off + step
                while end < n and idx + (end - off) < len(b) and a[end] == b[idx + (end - off)]:
                    end += 1
                if end - off > best[0]:
                    best = (end - off, off, idx)
    print(desc, "longest len =", best[0], "a_off =", hex(best[1]), "b_off =", hex(best[2]))

longest_common("gsp1101 vs JUpdater", fw, up)
longest_common("gsp1101 vs rp500", fw, rp)
longest_common("rp500 vs gsp1101", rp, fw)

hits = 0
for off in range(0, len(fw), 4096):
    if up.find(fw[off:off+4096]) >= 0: hits += 1
print("gsp1101 4KB chunks found in updater:", hits, "/", len(fw)//4096 + 1)

from collections import Counter
import math
def ent(d):
    c = Counter(d); n = len(d)
    return -sum((v/n)*math.log2(v/n) for v in c.values()) if n else 0.0
print("=== gsp1101 entropy per 16KB ===")
for off in range(0, len(fw), 0x4000):
    w = fw[off:off+0x4000]
    print("0x%06X ent=%.2f ff=%d" % (off, ent(w), w.count(0xFF)))
