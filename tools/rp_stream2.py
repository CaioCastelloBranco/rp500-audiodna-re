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

dump(14,0x9A12,0x9B80,"loader body after C1")
dump(14,0xA132,0xA1C0,"LCALL 0xA132 target")
dump(14,0x99A0,0x99F2,"loader entry (before 99F0)")

# who references 0x2DC2 as DPTR?
print("=== MOV DPTR,#0x2DC2 (90 2D C2) occurrences ===")
pat=bytes([0x90,0x2D,0xC2]); i=0; hits=[]
while True:
    j=RP.find(pat,i)
    if j<0: break
    hits.append(j); i=j+1
print([('b%d:%04X'%(h>>16,h&0xFFFF)) for h in hits])

print()
print("=== byte makeup of bank14 0x2C00-0x3100, 16 bytes/row ===")
d=BANKS[14]
for a in range(0x2C00,0x3100,16):
    c=d[a:a+16]
    print("  %04X: %-47s %s"%(a,c.hex(' '),''.join(chr(x) if 32<=x<127 else '.' for x in c)))
