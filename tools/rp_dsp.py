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
import sys

d = open(_P("rp500_fw.bin"), 'rb').read()
b15 = d[0xF0000:0x100000]
b14 = d[0xE0000:0xF0000]

for a in (0x8AB3, 0xCC03, 0xCC13):
    print('--- call site', hex(a), '---')
    print(b15[a - 24:a + 24].hex(' '))
    print('addr bytes:', b15[a:a + 3].hex(' '))

print('region around BDE7')
print(b15[0xBDC0:0xBE40].hex(' '))
print('b14 region around 99E0')
print(b14[0x99D0:0x9A30].hex(' '))
