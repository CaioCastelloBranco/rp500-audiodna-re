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
from collections import Counter

def payload16(img):
    return b''.join(img[k*0x10008+8:k*0x10008+0x10008] for k in range(16))

D = {
    'C48': payload16(open(_P("c48_fw.bin"),'rb').read()),
    'C63': payload16(open(_P("c63_fw.bin"),'rb').read()),
    'RP':  open(_P("rp500_fw.bin"),'rb').read(),
}

print('='*80)
print('RP500 serial sender LCALL D20A (bank15)')
d = D['RP'][15*0x10000:16*0x10000]
for a, raw, txt in disasm(d, 0, 0xD20A, 0xD20A+0xC0):
    print(f'{a:04X}: {raw:<10} {txt}')

print()
print('='*80)
print('GSP call targets reached by R5=data,R7=cmd blocks')
for name in ('C48', 'C63'):
    d = D[name]
    tg = Counter()
    for b in range(16):
        bank = d[b*0x10000:(b+1)*0x10000]
        for i in range(len(bank)-6):
            if bank[i] == 0x7D and bank[i+2] == 0x7F and bank[i+4] == 0x12:
                tgt = (bank[i+5] << 8) | bank[i+6]
                tg[tgt] += 1
    print(f'{name}: top targets', [(hex(t), n) for t, n in tg.most_common(12)])

print()
print('='*80)
print('C48 code around MOV DPTR,#0800 hit at bank6 0xA85A')
d = D['C48'][6*0x10000:7*0x10000]
for a, raw, txt in disasm(d, 0, 0xA820, 0xA8A0):
    print(f'{a:04X}: {raw:<10} {txt}')

print()
print('='*80)
print('C63 code around MOV DPTR,#0800 hit at bank6 0xA86A')
d = D['C63'][6*0x10000:7*0x10000]
for a, raw, txt in disasm(d, 0, 0xA830, 0xA8B0):
    print(f'{a:04X}: {raw:<10} {txt}')
