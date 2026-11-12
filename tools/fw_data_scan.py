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
import struct

fw = open(_P("gsp1101_fw.bin"),'rb').read()
up = open(_P("JUpdater Gsp1101vC63.exe"),'rb').read()

def entropy(data):
    from collections import Counter
    import math
    if not data: return 0.0
    c = Counter(data); n = len(data)
    return -sum((v/n)*math.log2(v/n) for v in c.values())

# .data section raw bytes (find in updater at 0xBF600, length 0x103800)
data_sec = up[0xBF600:0xBF600+0x103800]
print("data_sec == fw:", data_sec == fw)

# Find large non-FF constant-ish / high-entropy blocks inside .data
# Scan 4KB blocks, print entropy + dominant bytes
print("=== data sector entropy scan (4KB) ===")
for off in range(0, len(data_sec), 0x1000):
    blk = data_sec[off:off+0x1000]
    e = entropy(blk)
    # also print first word
    w = struct.unpack_from('<I', blk, 0)[0]
    flag = ""
    if e > 7.9: flag = " <== HIGH"
    elif e < 1.0: flag = " <== LOW"
    print("0x%06X ent=%.2f first32=%s%s" % (off, e, blk[:16].hex(' '), flag))

# Search for zlib/gzip magics
import re
for name, pat in [("zlib-78", b'\x78'), ("gzip", b'\x1f\x8b'), ("zip", b'PK\x03\x04'), ("elf", b'\x7fELF'), ("mz2", b'MZ')]:
    idxs = [m.start() for m in re.finditer(re.escape(pat), data_sec)]
    print(name, [hex(i) for i in idxs[:20]])
