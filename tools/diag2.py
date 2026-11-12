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
S = _FW
c63 = open(S+r'\c63_fw.bin','rb').read()
c48 = open(S+r'\c48_fw.bin','rb').read()
v20 = open(S+r'\v20_res_51E18.bin','rb').read()
rp  = open(S+r'\rp500_fw.bin','rb').read()

print('=== chunk boundary anatomy (C63, 16x0x10008) ===')
for k in range(4):
    o = k*0x10008
    print(' chunk%d first8 %s   last8 %s' % (k, c63[o:o+8].hex(' '), c63[o+0x10000:o+0x10008].hex(' ')))
print(' C63 last8 of chunk15:', c63[15*0x10008+0x10000:15*0x10008+0x10008].hex(' '))
print(' C48 chunk0 first8 %s last8 %s' % (c48[:8].hex(' '), c48[0x10000:0x10008].hex(' ')))
print()
print('=== does the 8-byte value appear at chunk END? ===')
for nm, d in (('c63',c63),('c48',c48)):
    for k in range(16):
        o = k*0x10008
        if d[o+0x10000:o+0x10008] == d[o:o+8]:
            print(' ', nm, 'chunk', k, 'end == start')
print()
print('=== v20 1MB: is it 16x64K bodies? check bank starts ===')
for b in range(4):
    o = b*0x10000
    print(' v20 bank%-2d @%05X: %s' % (b, o, v20[o:o+16].hex(' ')))
print()
print('=== v20: does it contain the per-bank 8-byte prefix anywhere? ===')
for k in range(16):
    o = k*0x10008
    if v20[o:o+8] == bytes.fromhex('ea8068022ec55391'):
        print('  found V20 prefix at', hex(o))
print()
print('=== rp500: last two bytes ===')
print(' rp[-2:] =', rp[-2:].hex(' '))
print(' c63[-2:] =', c63[-2:].hex(' '))
print(' c48[-2:] =', c48[-2:].hex(' '))
print(' v20[-2:] =', v20[-2:].hex(' '))
print()
print('=== rp500 bank15 vs c63 bank15 shared prefix ===')
print(' rp  bank15 first 32:', rp[15*0x10000:15*0x10000+32].hex(' '))
print(' c63 bank15 first 32:', c63[15*0x10008+8:15*0x10008+8+32].hex(' '))
print(' c63 bank15 chunk first 32:', c63[15*0x10008:15*0x10008+32].hex(' '))
