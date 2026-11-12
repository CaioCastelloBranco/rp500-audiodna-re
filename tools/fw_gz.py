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


import gzip, io, sys

data = open(_P("gsp1101_fw.bin"),'rb').read()
offs = [0x7aa54, 0xb61c1, 0xc8b32, 0xcf395, 0xd61bc]
for off in offs:
    print("=== gzip at 0x%X ===" % off)
    try:
        d = gzip.decompress(data[off:off+0x200000])
        print("  decompressed len:", len(d), hex(len(d)))
        print("  first64:", d[:64].hex(' '))
        open(_P("gz_%X.bin") % off, 'wb').write(d)
    except Exception as e:
        print("  fail:", e)
