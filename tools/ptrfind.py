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

def ptrs(d, val, banks=range(16)):
    pat = bytes([val >> 8, val & 0xFF])
    out = []
    for b in banks:
        bank = d[b*0x10000:(b+1)*0x10000]
        for m in re.finditer(re.escape(pat), bank):
            out.append((b, m.start()))
    return out

print('C63: pointer 0x3407 (USER_CAB string)')
for b, o in ptrs(D['C63'], 0x3407):
    print(f'  bank{b} {o:04X} ctx {D["C63"][b*0x10000+o-16:b*0x10000+o+16].hex(" ")}')
print('C48: pointer 0x3396 (USER_CAB string)')
for b, o in ptrs(D['C48'], 0x3396):
    print(f'  bank{b} {o:04X} ctx {D["C48"][b*0x10000+o-16:b*0x10000+o+16].hex(" ")}')

print()
print('C63: pointer 0xBFF4 (USER %d)')
for b, o in ptrs(D['C63'], 0xBFF4):
    print(f'  bank{b} {o:04X} ctx {D["C63"][b*0x10000+o-16:b*0x10000+o+16].hex(" ")}')

print()
print('C63: pointer 0xD9D8 (USER 1)')
for b, o in ptrs(D['C63'], 0xD9D8):
    print(f'  bank{b} {o:04X} ctx {D["C63"][b*0x10000+o-16:b*0x10000+o+16].hex(" ")}')

print()
print('C48: pointer 0x7618 (CHAMP1X8)')
for b, o in ptrs(D['C48'], 0x7618):
    print(f'  bank{b} {o:04X} ctx {D["C48"][b*0x10000+o-16:b*0x10000+o+16].hex(" ")}')
print('C63: pointer 0xD8EE (CHAMP1X8)')
for b, o in ptrs(D['C63'], 0xD8EE):
    print(f'  bank{b} {o:04X} ctx {D["C63"][b*0x10000+o-16:b*0x10000+o+16].hex(" ")}')
print('RP: pointer 0x3486 (CHAMP1X8)')
for b, o in ptrs(D['RP'], 0x3486):
    print(f'  bank{b} {o:04X} ctx {D["RP"][b*0x10000+o-16:b*0x10000+o+16].hex(" ")}')
