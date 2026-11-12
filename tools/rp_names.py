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
SH=_FW
rp=open(SH+r"\rp500_fw.bin",'rb').read()
o=4*0x10000
print("dump b4:0x3460-0x3560")
for a in range(0x3460,0x3560,16):
    c=rp[o+a:o+a+16]
    print("  %04X  %-47s %s"%(a,c.hex(' '),''.join(chr(q) if 32<=q<127 else '.' for q in c)))
print()
print("printable strings in b4:0x3200-0x3580")
i=0x3200
res=[]
while i<0x3580:
    if 32<=rp[o+i]<127:
        s=i
        while i<0x3580 and 32<=rp[o+i]<127: i+=1
        if i-s>=3: res.append((s,rp[o+s:o+i].decode('latin1')))
    else:
        i+=1
for s,t in res: print("  %04X  %r"%(s,t))
print()
print("NUL-terminated names starting 0x3486:")
i=0x3486;names=[];addr=[]
while i<0x3560:
    j=rp.find(b'\x00',o+i)
    if j<0: break
    names.append((i,rp[o+i:o+j].decode('latin1')))
    i=j+1
for s,t in names: print("  %04X  %r"%(s,t))
