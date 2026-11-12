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

rp = open(_P("rp500_fw.bin"),'rb').read()

# ARM sanity: first word B -> target
w0 = struct.unpack_from('<I', rp, 0)[0]
imm = w0 & 0x00FFFFFF
if imm & 0x00800000: imm -= 0x01000000
target = 8 + imm*4
print("reset B target: 0x%X" % target)
print("bytes at target:", rp[target:target+64].hex(' '))

# Common ARM prologues at 0x808?
def dump(off, n=96):
    print("--- 0x%X ---" % off)
    for i in range(0, n, 16):
        c = rp[off+i:off+i+16]
        ws = ' '.join('%08X' % struct.unpack_from('<I', c, j)[0] for j in range(0, 16, 4) if j+4 <= len(c))
        print("0x%06X  %-47s  %s" % (off+i, c.hex(' '), ws))
dump(0); dump(target); dump(0x400)

# Is there a second B-table later? find clusters of words with bits 27-24 == 0xA (B) or 0xB (BL)
from collections import Counter
print("=== B/BL density per 16KB (fraction of words) ===")
for off in range(0, len(rp), 0x4000):
    cnt = 0; tot = 0
    for i in range(off, min(off+0x4000, len(rp)-3), 4):
        w = struct.unpack_from('<I', rp, i)[0]
        if (w >> 24) in (0xEA, 0xEB): cnt += 1
        tot += 1
    print("0x%06X %.3f" % (off, cnt/tot))
