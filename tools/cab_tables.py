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

def dump(bank, off, n, tag):
    print("--- %s 0x%04X ---" % (tag, off))
    for i in range(off, off+n, 16):
        c=bank[i:i+16]
        print("0x%04X  %-47s  %s" % (i, c.hex(' '), ''.join(chr(x) if 32<=x<127 else '.' for x in c)))

print("=== RP bank6 0xC600-0xC820 (CAB_TYPE at 0xC725) ===")
dump(RPB[6], 0xC600, 0x220, "RP b6")

print("=== GSP bank8 0xDF20-0xE0C0 (CAB_TYPE at 0xDFA9) ===")
dump(GSPB[8], 0xDF20, 0x1A0, "GSP b8")

print("=== search: 30 consecutive strictly-increasing 16-bit values (possible data-offset table) ===")
for name, data in [("RP",RP),("GSP",GSP)]:
    found=[]
    for i in range(0, len(data)-64, 2):
        vals=[struct.unpack_from('<H', data, i+2*j)[0] for j in range(30)]
        if all(vals[j] < vals[j+1] for j in range(29)):
            span = vals[-1]-vals[0]
            if 0x100 <= span <= 0x20000 and all(0x1000 <= v for v in vals):
                found.append((i, vals[0], vals[-1], span))
    print(name, "candidates:", [(hex(i),hex(a),hex(b),hex(s)) for i,a,b,s in found[:10]], "total", len(found))

print("=== search: 30 consecutive 16-bit values all < 64 (model index table) ===")
for name, data in [("RP",RP),("GSP",GSP)]:
    found=[]
    for i in range(0, len(data)-64, 2):
        vals=[struct.unpack_from('<H', data, i+2*j)[0] for j in range(30)]
        if all(v < 64 for v in vals):
            if len(set(vals)) >= 10:
                found.append((i, vals[:10]))
    print(name, "candidates:", [(hex(i),v) for i,v in found[:12]], "total", len(found))

print("=== RP bank6: find code referencing 0xC725-ish (bank-local 0xC725) ===")
for k in range(16):
    hits=[]
    b=RPB[k]
    for i in range(0, 0x10000-2):
        if b[i]==0x90:
            v=b[i+1] | (b[i+2]<<8)
            if 0xC600 <= v < 0xC800:
                hits.append((i,v))
    if hits: print("bank %d:"%k, [(hex(i),hex(v)) for i,v in hits[:20]])

print("=== RP: search for CJNE/SUBB with #29 (0x1D) or #30 (0x1E) near bank6 cab code ===")
b=RPB[6]
for pat,desc in [(bytes([0xB4,0x1D]),'CJNE A,#29'),(bytes([0xB4,0x1E]),'CJNE A,#30'),(bytes([0x94,0x1D]),'SUBB A,#29'),(bytes([0x94,0x1E]),'SUBB A,#30'),(bytes([0xB4,0x27]),'CJNE A,#39'),(bytes([0x94,0x27]),'SUBB A,#39')]:
    idx=0;hits=[]
    while True:
        i=b.find(pat,idx)
        if i<0:break
        hits.append(i);idx=i+1
    print(desc,[hex(h) for h in hits[:20]],"count",len(hits))
