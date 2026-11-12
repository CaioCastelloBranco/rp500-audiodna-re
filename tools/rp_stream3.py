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
import mcs51

RP=open(_P("rp_fw.bin"),'rb').read()
BANKS=[RP[k*0x10000:(k+1)*0x10000] for k in range(16)]

def dump(bank,a,b,label):
    d=BANKS[bank]
    print("===== %s bank%d:0x%04X-0x%04X ====="%(label,bank,a,b))
    for addr,raw,text in mcs51.disasm(d,0,a,b):
        print("  %04X: %-9s %s"%(addr,raw,text))
    print()

dump(15,0xBDE0,0xBEC0,"loader variant b15")
print()
print("=== b14 tail of 32KB block: 0xADC2-0xAE40 ===")
for a in range(0xADC2,0xAE40,16):
    c=BANKS[14][a:a+16]
    print("  %04X: %-47s %s"%(a,c.hex(' '),''.join(chr(x) if 32<=x<127 else '.' for x in c)))
print()
print("=== b15 0x2DC2-0x2E80 ===")
for a in range(0x2DC2,0x2E80,16):
    c=BANKS[15][a:a+16]
    print("  %04X: %-47s %s"%(a,c.hex(' '),''.join(chr(x) if 32<=x<127 else '.' for x in c)))
print()
print("=== callers: LCALL to 0x99F0 / 0x9A12 / 0xBDE0 / 0xBE0A ===")
for tgt in (0x99F0,0x9A12,0xBDE0,0xBE0A):
    pat=bytes([0x12,(tgt>>8)&0xFF,tgt&0xFF]); i=0; hits=[]
    while True:
        j=RP.find(pat,i)
        if j<0: break
        hits.append(j); i=j+1
    print("  LCALL %04X n=%d %s"%(tgt,len(hits),[('b%d:%04X'%(h>>16,h&0xFFFF)) for h in hits[:20]]))
print()
print("=== AJMP/LCALL entry points referencing b14 0x9900-0x9B00 ===")
for tgt in (0x9900,0x9920,0x9940,0x9960,0x9980,0x99A0,0x99C0):
    pat=bytes([0x12,(tgt>>8)&0xFF,tgt&0xFF]); i=0; hits=[]
    while True:
        j=RP.find(pat,i)
        if j<0: break
        hits.append(j); i=j+1
    if hits:
        print("  LCALL %04X n=%d %s"%(tgt,len(hits),[('b%d:%04X'%(h>>16,h&0xFFFF)) for h in hits[:20]]))
