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


import collections, math, struct

RP = open(_P("rp_fw.bin"),'rb').read()
GSP = open(_P("gsp_fw.bin"),'rb').read()
RPB=[RP[k*0x10000:(k+1)*0x10000] for k in range(16)]

def ent(d):
    c=collections.Counter(d); n=len(d)
    return -sum((v/n)*math.log2(v/n) for v in c.values()) if n else 0

for k in [3,5,7,9,11,12,14]:
    b=RPB[k]
    print("=== RP bank %d ent=%.2f ===" % (k,ent(b)))
    for off in [0x0000,0x2000,0x4000,0x6000,0x8000,0xA000,0xC000,0xE000]:
        w=b[off:off+64]
        print(" 0x%04X %-47s %s" % (off, w.hex(' '), ''.join(chr(x) if 32<=x<127 else '.' for x in w)))
    # 32-bit top words
    ws=[struct.unpack_from('<I',b,i)[0] for i in range(0,0x10000-3,4)]
    c=collections.Counter(ws)
    print("  top 32-bit:", [(hex(v),n) for v,n in c.most_common(8)])
    # 16-bit top
    hs=[struct.unpack_from('<H',b,i)[0] for i in range(0,0x10000-1,2)]
    ch=collections.Counter(hs)
    print("  top 16-bit:", [(hex(v),n) for v,n in ch.most_common(8)])
    # 0x93 MOVC count, 0x90 count, 0x02/0x12 counts
    print("  0x93=%d 0x90=%d 0x02=%d 0x12=%d 0xE0=%d 0xF0=%d"%(b.count(0x93),b.count(0x90),b.count(0x02),b.count(0x12),b.count(0xE0),b.count(0xF0)))
