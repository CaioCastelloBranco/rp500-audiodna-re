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
_FW = _os.path.join(_ROOT, "01_source_firmware")


def _OUT(name):
    """Derived/output artifacts go to the script directory."""
    return _os.path.join(_SW, name)


import sys
sys.path.insert(0, _FW)
from d51 import disasm

def payload16(img):
    return b''.join(img[k*0x10008+8:k*0x10008+0x10008] for k in range(16))

c48 = payload16(open(_P("c48_fw.bin"),'rb').read())
c63 = payload16(open(_P("c63_fw.bin"),'rb').read())

def show(title, img, bank, start, end):
    print('='*78)
    print(title, f'bank{bank} {start:04X}..{end:04X}')
    d = img[bank*0x10000:(bank+1)*0x10000]
    for a, raw, txt in disasm(d, 0, start, end):
        print(f'{a:04X}: {raw:<9} {txt}')

show('C48', c48, 14, 0xDA60, 0xDB40)
show('C63', c63, 14, 0xDAB0, 0xDB90)
