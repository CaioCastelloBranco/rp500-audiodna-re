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
import re

def payload16(img):
    return b''.join(img[k*0x10008+8:k*0x10008+0x10008] for k in range(16))

imgs = {
    'V20': open(_P("v20_res_51E18.bin"),'rb').read(),
    'C48': payload16(open(_P("c48_fw.bin"),'rb').read()),
    'C63': payload16(open(_P("c63_fw.bin"),'rb').read()),
}

for name, img in imgs.items():
    print('='*60, name)
    for val in (0x0800, 0x07E7, 0x07FE, 0x07FD, 0x07FF):
        pat = bytes([0x90, val >> 8, val & 0xFF])
        offs = [i for i in range(len(img)-2) if img[i:i+3] == pat]
        banks = {}
        for o in offs:
            banks.setdefault(o // 0x10000, []).append(o % 0x10000)
        print(f'MOV DPTR,#{val:04X}', len(offs), {k: [hex(x) for x in v[:10]] for k, v in banks.items()})
    # immediate 16-bit loads via MOV r,#imm pairs is hard; instead look for MOV dir,#imm (75 aa bb)
    # look for 0x0800 anywhere as BE pair in code region
    print('  bytes pattern 08 00 count', img.count(b'\x08\x00'))
