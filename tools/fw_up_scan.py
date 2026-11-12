# --- portable path resolution (added 2026-11-10) ---------------------------
import os as _os

_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_SW = _os.path.dirname(_os.path.abspath(__file__))


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


import struct, zlib

up = open(_P("JUpdater Gsp1101vC63.exe"),'rb').read()
print("updater len:", hex(len(up)))

# 1) vector-table scan over whole file
hits = []
for off in range(0, len(up) - 32, 4):
    w = struct.unpack_from('<I', up, off)[0]
    if (w & 0xFF000000) == 0xEA000000:
        run = 1
        for k in range(1, 7):
            wk = struct.unpack_from('<I', up, off + 4*k)[0]
            if (wk & 0xFF000000) == 0xEA000000: run += 1
            else: break
        if run >= 5: hits.append((off, run))
print("vector-table runs (>=5 B-words) in updater:", [(hex(o), r) for o, r in hits], "total", len(hits))

# 2) zlib streams: try 0x78 0x9c / 0x78 0x01 / 0x78 0xda and decompress
n_ok = 0
for off in range(0, len(up) - 2):
    if up[off] == 0x78 and up[off+1] in (0x01, 0x9c, 0xda, 0x5e):
        try:
            d = zlib.decompress(up[off:off+0x200000])
            if len(d) > 1024:
                print("zlib at 0x%X -> len %d (0x%X) first32: %s" % (off, len(d), len(d), d[:32].hex(' ')))
                open(_P("zl_%X.bin") % off, 'wb').write(d)
                n_ok += 1
        except Exception:
            pass
print("zlib streams decompressed:", n_ok)

# 3) zlib presence in .rsrc/tail
tail = up[0x1C3800:]
print("overlay size:", hex(len(tail)), "first64:", tail[:64].hex(' ') if tail else "-")

# 4) entropy map of whole updater per 16KB to spot a big blob
from collections import Counter
import math
def ent(d):
    c = Counter(d); n = len(d)
    return -sum((v/n)*math.log2(v/n) for v in c.values()) if n else 0.0
print("=== updater entropy per 64KB ===")
for off in range(0, len(up), 0x10000):
    print("0x%06X ent=%.2f" % (off, ent(up[off:off+0x10000])))
