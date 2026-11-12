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

D = {
    'C48': payload16(open(_P("c48_fw.bin"),'rb').read()),
    'C63': payload16(open(_P("c63_fw.bin"),'rb').read()),
    'RP':  open(_P("rp500_fw.bin"),'rb').read(),
}

def xref_dptr(d, target_off, target_bank):
    """Search whole image for MOV DPTR,#target_off, but require the site to be in
    the same bank as target_bank (flash is banked 64K)."""
    pat = bytes([0x90, target_off >> 8, target_off & 0xFF])
    out = []
    base = target_bank * 0x10000
    bank = d[base:base + 0x10000]
    for m in re.finditer(re.escape(pat), bank):
        out.append(m.start())
    return out

print('='*78)
print('C63 USER_CAB %D string at flat 0xF3407 -> bank15 off 0x3407')
d = D['C63']
for o in xref_dptr(d, 0x3407, 15):
    print(f'  ref at bank15 {o:04X} ctx {d[15*0x10000+o-12:15*0x10000+o+24].hex(" ")}')

print()
print('C48 USER_CAB %D string at flat 0xF3396 -> bank15 off 0x3396')
d = D['C48']
for o in xref_dptr(d, 0x3396, 15):
    print(f'  ref at bank15 {o:04X} ctx {d[15*0x10000+o-12:15*0x10000+o+24].hex(" ")}')

print()
print('C63 "USER %d" at flat 0xBFF4 -> bank0 off 0xBFF4')
d = D['C63']
for o in xref_dptr(d, 0xBFF4, 0):
    print(f'  ref at bank0 {o:04X} ctx {d[o-12:o+24].hex(" ")}')

print()
print('C63 USER 1 string table at bank11 0xD9D8')
d = D['C63']
for o in xref_dptr(d, 0xD9D8, 11):
    print(f'  ref at bank11 {o:04X} ctx {d[11*0x10000+o-12:11*0x10000+o+24].hex(" ")}')

print()
print('C48 cab table (CHAMP1X8) at bank10 0x7618')
d = D['C48']
for o in xref_dptr(d, 0x7618, 10):
    print(f'  ref at bank10 {o:04X} ctx {d[10*0x10000+o-12:10*0x10000+o+24].hex(" ")}')
print('C63 cab table (CHAMP1X8) at bank11 0xD8EE')
d = D['C63']
for o in xref_dptr(d, 0xD8EE, 11):
    print(f'  ref at bank11 {o:04X} ctx {d[11*0x10000+o-12:11*0x10000+o+24].hex(" ")}')
print('RP cab table at bank4 0x3486')
d = D['RP']
for o in xref_dptr(d, 0x3486, 4):
    print(f'  ref at bank4 {o:04X} ctx {d[4*0x10000+o-12:4*0x10000+o+24].hex(" ")}')
