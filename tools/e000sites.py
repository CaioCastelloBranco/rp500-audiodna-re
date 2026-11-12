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


import sys, re
sys.path.insert(0, _FW)
from d51 import disasm

def payload16(img):
    return b''.join(img[k*0x10008+8:k*0x10008+0x10008] for k in range(16))

D = {
    'C48': payload16(open(_P("c48_fw.bin"),'rb').read()),
    'C63': payload16(open(_P("c63_fw.bin"),'rb').read()),
    'RP':  open(_P("rp500_fw.bin"),'rb').read(),
}

print('='*78)
print('RP500: all MOV DPTR,#E000 sites (bank, off)')
d = D['RP']
for b in range(16):
    bank = d[b*0x10000:(b+1)*0x10000]
    for m in re.finditer(rb'\x90\xe0\x00', bank):
        o = m.start()
        print(f'  b{b}:{o:04X}  {bank[max(0,o-14):o+18].hex(" ")}')

print()
print('='*78)
print('C48: E000 sites by bank (contexts)')
d = D['C48']
for b in (0, 14, 15):
    bank = d[b*0x10000:(b+1)*0x10000]
    for m in re.finditer(rb'\x90\xe0\x00', bank):
        o = m.start()
        print(f'  b{b}:{o:04X}  {bank[max(0,o-14):o+18].hex(" ")}')
