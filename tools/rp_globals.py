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

print("=== records flagged by 2d ac, 32-byte stride, with string pointers ===")
hits=[]
i=0x4200
while i<0x4800:
    if B[i]==0x2D and B[i+1]==0xAC:
        p1=(B[i+2]<<8)|B[i+3]
        p2=(B[i+4]<<8)|B[i+5]
        if 0x2C00<=p1<0x3600 and 0x2C00<=p2<0x3600:
            hits.append((i,p1,p2))
            print("0x%04X  p1=0x%04X %-14r p2=0x%04X %-14r  rec=%s" % (
                i,p1,cstr(B,p1),p2,cstr(B,p2),B[i:i+32].hex(' ')))
    i+=1
print("count",len(hits))
print("strides:", [hits[j+1][0]-hits[j][0] for j in range(len(hits)-1)])

print()
print("=== table region 0x4200-0x4336, annotated 32-byte rows ===")
for i in range(0x4200,0x4340,16):
    c=B[i:i+16]
    print("0x%04X  %-47s  %s" % (i,c.hex(' '),''.join(chr(x) if 32<=x<127 else '.' for x in c)))

print()
print("=== enumerate big-endian pointers in 0x4600-0x4800 that point to strings ===")
for i in range(0x4600,0x4800,2):
    v=(B[i]<<8)|B[i+1]
    if 0x2C00<=v<0x3600:
        s=cstr(B,v)
        if all(32<=c<127 for c in s) and len(s)>=2:
            print("0x%04X -> 0x%04X %r" % (i,v,s))
