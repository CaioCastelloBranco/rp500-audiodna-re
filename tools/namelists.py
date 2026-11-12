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

def cstr(bank, off, maxn=20):
    out=[]
    for i in range(off, min(off+maxn, len(bank))):
        if bank[i]==0: break
        out.append(chr(bank[i]) if 32<=bank[i]<127 else '?')
    return ''.join(out)

print("=== RP bank4: runs of 16-bit words stepping by +9 (fixed 9-byte name lists) ===")
b=RPB[4]
runs=[]
for i in range(0,0x10000-2-2*18,2):
    # try to start a run here
    vals=[b[i+2*j] | (b[i+2*j+1]<<8) for j in range(18)]
    n=1
    while n<18 and vals[n]==vals[n-1]+9: n+=1
    if n>=5:
        runs.append((i,vals[:n]))
# dedupe overlapping
kept=[]
for i,vals in runs:
    if any(abs(i-j)<18 for j,_ in kept): 
        # keep longer
        for idx,(j,v) in enumerate(kept):
            if abs(i-j)<18 and len(vals)>len(v):
                kept[idx]=(i,vals)
        continue
    kept.append((i,vals))
for i,vals in kept:
    names=[cstr(b,v) for v in vals]
    print("run@0x%04X n=%d: %s" % (i,len(vals),names))

print()
print("=== RP bank4: all 16-bit values equal to 0x344A/0x3453/0x345C/0x3465/0x3486 ===")
for target in (0x344A,0x3453,0x345C,0x3465,0x3486,0x355E):
    hits=[i for i in range(0,0x10000-1) if (b[i]|(b[i+1]<<8))==target]
    print(hex(target), [hex(h) for h in hits[:12]], "count",len(hits))

print()
print("=== GSP bank11: runs of 16-bit words pointing to NUL-terminated names that step forward ===")
g=GSPB[11]
runs=[]
for i in range(0,0x10000-2,2):
    vals=[g[i+2*j] | (g[i+2*j+1]<<8) for j in range(16)]
    if not all(0xD800<=v<0xDC00 for v in vals): continue
    # next value must be > prev and <= prev+20
    n=1
    while n<16 and 0<vals[n]-vals[n-1]<=20: n+=1
    if n>=5:
        runs.append((i,vals[:n]))
kept=[]
for i,vals in runs:
    if any(abs(i-j)<16 for j,_ in kept): continue
    kept.append((i,vals))
for i,vals in kept:
    print("run@0x%04X n=%d: %s" % (i,len(vals),[cstr(g,v,20) for v in vals]))
