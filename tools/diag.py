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
    """Route derived/output artifacts to the script directory."""
    return _os.path.join(_SW, name)


import re, struct
S = _FW
v20 = open(S+r'\v20_res_51E18.bin','rb').read()
rp  = open(S+r'\rp500_fw.bin','rb').read()
c48 = open(S+r'\c48_fw.bin','rb').read()
c63 = open(S+r'\c63_fw.bin','rb').read()

def payload16(img):
    return b''.join(img[k*0x10008+8:k*0x10008+0x10008] for k in range(16))

print('=== A. rp500_fw.bin format ===')
print('size', hex(len(rp)))
print('first 16', rp[:16].hex(' '))
print('v20[0:16]  ', v20[:16].hex(' '))
print('v20[8:24]  ', v20[8:24].hex(' '))
print('DigBin magic at 0?', rp[:12].hex(' '))
# look for DigBin header anywhere
for pat,name in [(b'\x00\x5c\x00\x05','magic'), (b'\x00\x01\x00\x00','desc')]:
    idx = [m.start() for m in re.finditer(re.escape(pat), rp)]
    print(name, 'occurrences', len(idx), idx[:6])
# bank starts in rp
for b in range(16):
    o = b*0x10000
    print('  rp bank%-2d @%05X: %s' % (b, o, rp[o:o+8].hex(' ')))

print()
print('=== B. v20 vs rp: is rp the flat payload of v20 DigBin? ===')
# Compare rp banks to v20 payload banks
same = 0
for b in range(16):
    a = v20[b*0x10008+8:b*0x10008+0x10008]
    c = rp[b*0x10000:(b+1)*0x10000]
    eq = a == c
    same += eq
    print('  bank%-2d payload-equal=%s  %s' % (b, eq, a[:6].hex(' ')+' / '+c[:6].hex(' ')))
print('banks equal:', same)

print()
print('=== C. locate C63 strings in flat payload ===')
P63 = payload16(c63)
for s in (b'USER 1', b'USER %d', b'CAB_EN_XLR_LPF', b'USER_CAB %D'):
    idx = [m.start() for m in re.finditer(re.escape(s), P63)]
    print(' ', s, [(hex(i), 'bank%d off %04X' % (i//0x10000, i%0x10000)) for i in idx[:8]])
P48 = payload16(c48)
print(' C48 USER_CAB %D', [(hex(m.start()), 'bank%d off %04X'%(m.start()//0x10000, m.start()%0x10000)) for m in re.finditer(re.escape(b'USER_CAB %D'), P48)])

print()
print('=== D. RP pointer table ===')
# find 0x3486 pointer and nearby BE pointers
for target in (0x3486, 0x3453):
    pat = bytes([target>>8, target&0xFF])
    idx = [m.start() for m in re.finditer(re.escape(pat), rp)]
    print(' ptr %04X occurrences:' % target, [(hex(i), 'bank%d off %04X'%(i//0x10000,i%0x10000)) for i in idx[:8]])
# dump around 0x478E
o = 4*0x10000+0x478E
print(' rp @ bank4 0x478E:', rp[o:o+80].hex(' '))
print(' rp @ bank4 0x3486:', rp[4*0x10000+0x3486:4*0x10000+0x3486+40])

print()
print('=== E. D066 sites in v20/c48/c63/rp ===')
import sys
sys.path.insert(0, _FW)
from d51 import disasm
for nm, d in (('v20',v20),('c48',c48),('c63',c63),('rp',rp)):
    print(' ', nm)
    for b in range(16):
        base = b*0x10008 if nm in ('v20','c48','c63') else b*0x10000
        bank = d[base:base+0x10000] if nm in ('v20','c48','c63') else d[base:base+0x10000]
        for m in re.finditer(rb'\x90\xd0\x66', bank):
            a = m.start()
            # disassemble a few instrs after
            try:
                ins = list(disasm(bank, 0, a, a+24))
            except Exception:
                ins = []
            txt = ' | '.join(t for _,_,t in ins[:4])
            print('    b%-2d %04X  %s' % (b, a, txt))
