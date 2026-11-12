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


import struct
RP=open(_P("rp_fw.bin"),'rb').read()
BANKS=[RP[k*0x10000:(k+1)*0x10000] for k in range(16)]

def cstr(bank,off,maxn=28):
    out=[]
    for i in range(off,min(off+maxn,len(bank))):
        if bank[i]==0: break
        out.append(chr(bank[i]) if 32<=bank[i]<127 else '?')
    return ''.join(out)

# 1) find runs of BE16 pointers into 0x2200..0x4A00 in bank4
print("=== bank4: runs of BE16 pointers into 0x2200-0x4A00 ===")
i=0
while i<0x10000-4:
    v=(BANKS[4][i]<<8)|BANKS[4][i+1]
    if 0x2200<=v<0x4A00:
        start=i; ptrs=[]
        while i<0x10000-1:
            v=(BANKS[4][i]<<8)|BANKS[4][i+1]
            if not (0x2200<=v<0x4A00): break
            ptrs.append(v); i+=2
        if len(ptrs)>=2:
            print("run @0x%04X n=%d: %s"%(start,len(ptrs),
                " ".join("%04X"%p for p in ptrs[:40])))
            # annotate strings if any
            ann=[]
            for p in ptrs[:40]:
                s=cstr(BANKS[4],p,16)
                ann.append(s if s else "?")
            print("     "+" | ".join(ann))
        continue
    i+=1

# 2) find big table in bank4 0x3800-0x4220 that may hold parameter descriptors
print()
print("=== bank4 0x3C00-0x4220 raw ===")
b=BANKS[4]
for a in range(0x3C00,0x4220,16):
    c=b[a:a+16]
    print("0x%04X  %-47s  %s"%(a,c.hex(' '),''.join(chr(x) if 32<=x<127 else '.' for x in c)))
