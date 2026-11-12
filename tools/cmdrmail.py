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

D = {
    'C48': payload16(open(_P("c48_fw.bin"),'rb').read()),
    'C63': payload16(open(_P("c63_fw.bin"),'rb').read()),
}

def show(name, bank, start, end):
    d = D[name][bank*0x10000:(bank+1)*0x10000]
    print('='*84)
    print(f'{name} bank{bank} {start:04X}..{end:04X}')
    for a, raw, txt in disasm(d, 0, start, end):
        print(f'{a:04X}: {raw:<12} {txt}')

show('C48', 14, 0xB240, 0xB3C0)
show('C63', 14, 0xB2E0, 0xB460)
