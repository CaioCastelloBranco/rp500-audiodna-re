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
RP = open(_P("rp_fw.bin"),'rb').read()
GSP = open(_P("gsp_fw.bin"),'rb').read()
RPB=[RP[k*0x10000:(k+1)*0x10000] for k in range(16)]
GSPB=[GSP[k*0x10000:(k+1)*0x10000] for k in range(16)]

def cstr(bank, off, maxn=24):
    out=[]
    for i in range(off, min(off+maxn, len(bank))):
        if bank[i]==0: break
        out.append(chr(bank[i]) if 32<=bank[i]<127 else '?')
    return ''.join(out)

print("RP cabinet pointer table at 0x478E (big-endian 16-bit, 25 entries expected):")
ptrs=[]
for i in range(0x478E, 0x478E+2*32, 2):
    v=(RPB[4][i]<<8)|RPB[4][i+1]
    ptrs.append(v)
    print("  %2d 0x%04X %r" % ((i-0x478E)//2, v, cstr(RPB[4], v) if 0x3300<=v<0x3600 else '<out>'))
    if v>0x3600: break

print()
print("RP amp pointer table at 0x46D2 (big-endian):")
for i in range(0x46D2, 0x46D2+2*32, 2):
    v=(RPB[4][i]<<8)|RPB[4][i+1]
    if not (0x3300<=v<0x3600): break
    print("  %2d 0x%04X %r" % ((i-0x46D2)//2, v, cstr(RPB[4], v)))

print()
print("GSP cabinet list 0xD8C0..0xD9D7 (count until USER):")
off=0xD8C0; n=0
while off<0xDA20:
    s=cstr(GSPB[11],off)
    if s.startswith('USER'): break
    print("  %2d 0x%04X %r" % (n,off,s)); n+=1
    off=off+len(s)+1
print("factory cab count =",n)

print()
print("RP: any 'CAB_TYPE' near code that moves/compares 25 or 30? list CJNE/SUBB #0x19/#0x1A/#0x1D/#0x1E in bank6")
b=RPB[6]
for pat,desc in [(bytes([0xB4,0x19]),'CJNE A,#25'),(bytes([0xB4,0x1A]),'CJNE A,#26'),
                 (bytes([0x94,0x19]),'SUBB A,#25'),(bytes([0x94,0x1A]),'SUBB A,#26'),
                 (bytes([0xB4,0x1D]),'CJNE A,#29'),(bytes([0x94,0x1D]),'SUBB A,#29'),
                 (bytes([0xB4,0x1E]),'CJNE A,#30'),(bytes([0x94,0x1E]),'SUBB A,#30')]:
    idx=0;hits=[]
    while True:
        i=b.find(pat,idx)
        if i<0: break
        hits.append(i); idx=i+1
    print(desc, [hex(x) for x in hits], "count", len(hits))
