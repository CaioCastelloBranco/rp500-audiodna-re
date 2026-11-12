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

data = open(_P("gsp1101_fw.bin"),'rb').read()

def dump(off, n=128):
    print("--- 0x%X ---" % off)
    for i in range(0, n, 16):
        chunk = data[off+i:off+i+16]
        words = ' '.join('%08X' % struct.unpack_from('<I', chunk, j)[0] for j in range(0, 16, 4) if j + 4 <= len(chunk))
        print("0x%06X  %-47s  %s" % (off+i, chunk.hex(' '), words))

# Scan for ARM vector-table-like runs: >=5 consecutive 0xEA...... words (B cond=AL)
hits = []
for off in range(0, len(data) - 32, 4):
    w = struct.unpack_from('<I', data, off)[0]
    if (w & 0xFF000000) == 0xEA000000:
        run = 1
        for k in range(1, 8):
            wk = struct.unpack_from('<I', data, off + 4*k)[0]
            if (wk & 0xFF000000) == 0xEA000000: run += 1
            else: break
        if run >= 5: hits.append((off, run))
print("vector-table-like runs (>=5 B-words):", [(hex(o), r) for o, r in hits[:30]], "total", len(hits))

# ARM SVC / BL density scan: count 0xEBxxxxxx (BL) per 4KB
print("=== BL density per 64KB (words 0xEB......) ===")
for off in range(0, len(data), 0x10000):
    cnt = 0
    for i in range(off, min(off+0x10000, len(data)-3), 4):
        if (struct.unpack_from('<I', data, i)[0] & 0xFF000000) == 0xEB000000: cnt += 1
    print("0x%06X BL=%d" % (off, cnt))

dump(0xA7680); dump(0xCD1A8)
