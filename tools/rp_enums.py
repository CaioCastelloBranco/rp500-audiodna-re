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
B=RP[4*0x10000:5*0x10000]

def cstr(bank,off,maxn=24):
    out=[]
    for i in range(off,min(off+maxn,len(bank))):
        if bank[i]==0: break
        out.append(chr(bank[i]) if 32<=bank[i]<127 else '?')
    return ''.join(out)

print("=== all 2d ac enum lists in bank4 (pointers into string area) ===")
i=0x4000
found=[]
while i<0x4900:
    if B[i]==0x2D and B[i+1]==0xAC:
        vals=[]; j=i+2
        while j+1<len(B):
            v=(B[j]<<8)|B[j+1]
            if 0x2C00<=v<0x3600:
                s=cstr(B,v)
                if s and all(32<=ord(c)<127 for c in s):
                    vals.append((v,s)); j+=2; continue
            break
        if len(vals)>=2:
            found.append((i,vals,j))
            # avoid overlapping starts
            i=j
            continue
    i+=1

for i,vals,j in found:
    print("\nlist@0x%04X n=%d end=0x%04X" % (i,len(vals),j))
    print("   " + " | ".join("%s(0x%X)"%(s,v) for v,s in vals))
    print("   after: %s" % B[j:j+16].hex(' '))

print()
print("=== short strings in bank4 0x2C00-0x3300 with offsets ===")
off=0x2C00
while off<0x3300:
    s=cstr(B,off,24)
    if s:
        print("0x%04X %r" % (off,s))
        off+=len(s)+1
    else:
        off+=1
