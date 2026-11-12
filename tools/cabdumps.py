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
def payload16(img):
    return b''.join(img[k*0x10008+8:k*0x10008+0x10008] for k in range(16))

D = {
    'RP':  (open(_P("rp500_fw.bin"),'rb').read(), 0x43400),
    'C48': (payload16(open(_P("c48_fw.bin"),'rb').read()), 0xa75a0),
    'C63': (payload16(open(_P("c63_fw.bin"),'rb').read()), 0xbd880),
}
import re
for name, (d, lo) in D.items():
    print('='*78)
    print(name)
    hi = lo + 0x1A0
    for a in range(lo & ~0xF, hi, 16):
        row = d[a:a+16]
        txt = ''.join(chr(b) if 32 <= b < 127 else '.' for b in row)
        print(f'{a:06X}: {row.hex(" "):<48} {txt}')
