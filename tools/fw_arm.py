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

def find_arm_vectors(tag, data):
    # ARM exception vector: word & 0xFF000000 == 0xEA000000 (B)
    hits = []
    for off in range(0, len(data)-64, 4):
        w0 = struct.unpack_from('<I', data, off)[0]
        if (w0 & 0xFF000000) == 0xEA000000:
            w1 = struct.unpack_from('<I', data, off+4)[0]
            if (w1 & 0xFF000000) == 0xEA000000:
                hits.append(off)
    print(tag, "ARM vector-like pairs:", [hex(h) for h in hits[:15]], "total", len(hits))

find_arm_vectors("gsp1101_fw.bin", fw)
find_arm_vectors("JUpdater.exe", up)

# where does .data start in the exe file? look for fw[0:64] -> known 0xBF600.
# dump what precedes it (up to 0x200 bytes) to see context
print("updater bytes before fw:", up[0xBF600-64:0xBF600].hex(' '))
print("fw first 64:", fw[:64].hex(' '))

# gsp1101 load-base guess: pointers 0x004A5118 etc. If base = 0x00000000 -> no.
# count distinct high pointers in first 4KB
ptrs = struct.unpack_from('<1024I', fw, 0)
vals = [p for p in ptrs if 0x00400000 <= p < 0x00500000]
print("ptrs in 0x4xxxxx in first 4KB:", len(vals), [hex(v) for v in vals[:10]])
