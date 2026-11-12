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


import re, sys
sys.path.insert(0, _FW)
from d51 import disasm
S = _FW
def bodies(img):
    return [img[k*0x10000 + k*8 : (k+1)*0x10000 + k*8] for k in range(16)]
c63 = bodies(open(S+r'\c63_fw.bin','rb').read())
c48 = bodies(open(S+r'\c48_fw.bin','rb').read())
v20 = [open(S+r'\v20_res_51E18.bin','rb').read()[k*0x10000:(k+1)*0x10000] for k in range(16)]
rp  = [open(S+r'\rp500_fw.bin','rb').read()[k*0x10000:(k+1)*0x10000] for k in range(16)]

def find(banks, s, bank=None):
    out=[]
    for k,b in enumerate(banks):
        if bank is not None and k != bank: continue
        for m in re.finditer(re.escape(s), b):
            out.append((k, m.start()))
    return out

print('=== §2.3 service strings: true offsets ===')
for s in (b'SEND BLOCK', b'SEND PRESET', b'SEND AMP', b'BULK DUMP', b'Receiving a Bulk Dump',
          b'from X-Edit', b'BLOCK: %D', b'PROGRAM: %D', b'GLOBAL: %D', b'USER AMP %D',
          b'USER_CAB %D', b'FLASH ERASE ERROR', b'FLASH WRITE ERROR',
          b'FLASH INIT SECTOR ERROR', b'PRE DSP', b'POST DSP', b'PRE SAMPLE', b'FLASH_DATA: %D'):
    r = find(c63, s, bank=15)
    print('  %-26s %s' % (s.decode(), ['0x%04X'%o for _,o in r[:3]]))
print('  V20 USER_CAB %D:', ['bank%d 0x%04X'%(k,o) for k,o in find(v20, b'USER_CAB %D')])

print()
print('=== §9.4/§12 code sites ===')
# command writer: find MOV DPTR,#E200 sites and their bank/off
for nm, banks in (('c48',c48),('c63',c63)):
    for k,b in enumerate(banks):
        for m in re.finditer(rb'\x90\xe2\x00', b):
            print('  %s E200 site bank%d 0x%04X' % (nm,k,m.start()))
# MOV DPTR,#0800 (90 08 00)
for nm, banks in (('c48',c48),('c63',c63)):
    for k,b in enumerate(banks):
        for m in re.finditer(rb'\x90\x08\x00', b):
            print('  %s DPTR#0800 bank%d 0x%04X' % (nm,k,m.start()))
print()
print('=== RP500 sites (flat, no offset issue) ===')
for s in (b'RP 500', b'UPDATE', b'UPLOAD', b'GL PARAM', b'BULKERR1'):
    print('  %-10s %s' % (s.decode(), ['bank%d 0x%04X'%(k,o) for k,o in find(rp,s)[:4]]))
for pat, nm2 in ((rb'\x90\xd0\x70','DPTR#D070'),):
    for k,b in enumerate(rp):
        for m in re.finditer(pat,b):
            print('  RP %s bank%d 0x%04X' % (nm2,k,m.start()))
for addr in (0xF4D3,0xF4AE,0xF4FA,0xF431,0xFDFC,0xE600,0xD06E,0xD05B,0xD06D,0xD06F):
    hits=[]
    for k,b in enumerate(rp):
        for m in re.finditer(re.escape(bytes([0x90, addr>>8, addr&0xFF])), b):
            hits.append((k,m.start()))
    print('  RP DPTR#%04X refs=%d %s' % (addr, len(hits), ['b%d 0x%04X'%(k,o) for k,o in hits[:6]]))
# RP bulk loop source 0x2E3B and cap 0x7FF8
print('  RP bank15 0xBE97 region:', rp[15][0xBE97:0xBE97+24].hex(' '))
print('  RP bank15 0xDBB3 region:', rp[15][0xDBB3:0xDBB3+24].hex(' '))
print('  RP bank14 0x99F0 region:', rp[14][0x99F0:0x99F0+16].hex(' '))
print('  RP bank14 0x9A12 region:', rp[14][0x9A12:0x9A12+16].hex(' '))
print('  RP bank15 0xBDE7 region:', rp[15][0xBDE7:0xBDE7+16].hex(' '))
