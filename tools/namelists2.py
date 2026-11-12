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

def runs(bank, pred, maxn=24):
    res=[]
    for start in (0,1):
        for i in range(start, len(bank)-2*maxn, 2):
            vals=[bank[i+2*j] | (bank[i+2*j+1]<<8) for j in range(maxn)]
            if not pred(vals): continue
            n=1
            while n<maxn and 0 < vals[n]-vals[n-1] <= 20: n+=1
            if n>=5: res.append((i,vals[:n]))
    # dedupe by overlap keep longest
    res.sort(key=lambda t:-len(t[1]))
    kept=[]
    for i,vals in res:
        if any(abs(i-j)<2*len(vals) for j,_ in kept): continue
        kept.append((i,vals))
    return kept

print("=== RP bank4 candidate name-pointer tables (values inside 0x3300-0x3600) ===")
for i,vals in runs(RPB[4], lambda v: all(0x3300<=x<0x3600 for x in v)):
    names=[cstr(RPB[4],v) for v in vals]
    print("table@0x%04X n=%d span=0x%X->0x%X" % (i,len(vals),vals[0],vals[-1]))
    for k,nm in enumerate(names): print("   %2d %s" % (k,nm))

print()
print("=== GSP bank11 candidate name-pointer tables (values inside 0xD800-0xDAA0) ===")
for i,vals in runs(GSPB[11], lambda v: all(0xD800<=x<0xDAA0 for x in v)):
    names=[cstr(GSPB[11],v) for v in vals]
    print("table@0x%04X n=%d span=0x%X->0x%X" % (i,len(vals),vals[0],vals[-1]))
    for k,nm in enumerate(names): print("   %2d %s" % (k,nm))

print()
print("=== RP fixed 9-byte strings 0x3440-0x3570 with offsets ===")
off=0x3440
while off<0x3575:
    s=cstr(RPB[4],off,12)
    nxt=off+len(s)+1
    print("0x%04X  %-10r len %d" % (off,s,len(s)))
    off=nxt
print()
print("=== GSP fixed/variable strings 0xD8A0-0xDA20 with offsets ===")
off=0xD8A0
while off<0xDA20:
    s=cstr(GSPB[11],off,24)
    print("0x%04X  %-24r len %d" % (off,s,len(s)))
    off=off+len(s)+1
