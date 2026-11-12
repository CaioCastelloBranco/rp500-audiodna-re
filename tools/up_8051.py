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


import struct, collections, re

up = open(_P("JUpdater Gsp1101vC63.exe"),'rb').read()
data_start = 0xBF600
data_end = data_start + 0x103800

print("=== exact header searches ===")
patterns = {
    "rp500 header": bytes.fromhex("ea0002006b5391df3200ff02234e011f"),
    "NMLp": b"NMLp",
    "75 90 FF (mov p1)": bytes.fromhex("7590ff"),
    "02 00 6B (ljmp 6b)": bytes.fromhex("02006b"),
}
for name, pat in patterns.items():
    hits = [m.start() for m in re.finditer(re.escape(pat), up)]
    print(name, "count", len(hits), [hex(h) for h in hits[:20]])

# 8051 opcode-likeness per 4KB window over whole exe
ops = [0x02,0x12,0x90,0x75,0xE5,0xF0,0xE0,0x74,0x24,0x25,0x33,0x93,0xA3,0x70,0x60,0x50,0x40,0x80,0xD5,0xD8,0xC2,0xD2,0xB2,0xA2,0x30,0x20,0x10,0x00]
opset = set(ops)
print("=== top 4KB windows by 8051-opcode score ===")
scores = []
for off in range(0, len(up)-0x1000, 0x1000):
    w = up[off:off+0x1000]
    s = sum(1 for b in w if b in opset)/len(w)
    scores.append((s, off))
for s, off in sorted(scores, reverse=True)[:30]:
    print("0x%06X score=%.3f" % (off, s))

# score in .data only, 4KB
print("=== .data 4KB windows with score > 0.33 ===")
for off in range(data_start, data_end-0x1000, 0x1000):
    w = up[off:off+0x1000]
    s = sum(1 for b in w if b in opset)/len(w)
    if s > 0.33:
        print("0x%06X (.data +0x%X) score=%.3f first=%s" % (off, off-data_start, s, w[:32].hex(' ')))

# inspect the two decompressed zlib blobs
import zlib
for off in [0xAA226, 0xAABC6]:
    try:
        d = zlib.decompress(up[off:off+0x200000])
        print("zlib 0x%X -> %d bytes" % (off, len(d)))
        print("  first 128:", d[:128].hex(' '))
        print("  ascii:", ''.join(chr(b) if 32<=b<127 else '.' for b in d[:128]))
        open(_P("zl_%X.bin") % off, 'wb').write(d)
    except Exception as e:
        print("zlib fail", e)
