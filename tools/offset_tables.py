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


import struct, collections, math
RP = open(_P("rp_fw.bin"),'rb').read()
GSP = open(_P("gsp_fw.bin"),'rb').read()

def ent(d):
    c=collections.Counter(d); n=len(d)
    return -sum((v/n)*math.log2(v/n) for v in c.values()) if n else 0

def scan(name, data, stride):
    print("==== %s: 30-entry non-decreasing offset tables (stride %d) ====" % (name,stride))
    out=[]
    lim=len(data)-stride*30
    for i in range(0, lim, 2):
        if stride==2:
            vals=[struct.unpack_from('<H',data,i+2*j)[0] for j in range(30)]
        else:
            vals=[struct.unpack_from('<I',data,i+4*j)[0] for j in range(30)]
        if vals[0] < 0x800: continue
        if any(vals[j] > vals[j+1] for j in range(29)): continue
        if len(set(vals)) < 24: continue
        span=vals[-1]-vals[0]
        if not (0x800 <= span <= 0x100000): continue
        out.append((i,vals))
    # merge overlapping hits, keep first
    kept=[]
    last=-999
    for i,vals in out:
        if i-last < 16: continue
        kept.append((i,vals)); last=i
    print("count",len(kept))
    for i,vals in kept[:40]:
        span=vals[-1]-vals[0]
        tgt=data[vals[0]:vals[0]+64] if vals[0]<len(data) else b''
        print("  table@0x%06X first=0x%X last=0x%X span=0x%X tgt_ent=%.2f tgt=%s" % (i,vals[0],vals[-1],span,ent(data[vals[0]:vals[0]+512]), tgt[:24].hex(' ')))

scan("RP",RP,2)
scan("GSP",GSP,2)
scan("RP",RP,4)
scan("GSP",GSP,4)

print()
print("==== RP bank9 0xA900-0xBC00 sample (highest-entropy region) ====")
b=RP[9*0x10000:10*0x10000]
for off in range(0xA900,0xA900+0x300,16):
    c=b[off:off+16]
    print("0x%04X %-47s %s" % (off,c.hex(' '),''.join(chr(x) if 32<=x<127 else '.' for x in c)))
print()
print("==== RP bank9 0xB800-0xBC00 ====")
for off in range(0xB800,0xBC00,16):
    c=b[off:off+16]
    print("0x%04X %-47s %s" % (off,c.hex(' '),''.join(chr(x) if 32<=x<127 else '.' for x in c)))
