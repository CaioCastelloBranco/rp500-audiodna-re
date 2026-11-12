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


import re, struct

RP = open(_P("rp_fw.bin"),'rb').read()
GSP = open(_P("gsp_fw.bin"),'rb').read()
RPB=[RP[k*0x10000:(k+1)*0x10000] for k in range(16)]
GSPB=[GSP[k*0x10000:(k+1)*0x10000] for k in range(16)]

def dump(bank, off, n, tag):
    print("--- %s 0x%04X ---" % (tag, off))
    for i in range(off, off+n, 16):
        c=bank[i:i+16]
        print("0x%04X  %-47s  %s" % (i, c.hex(' '), ''.join(chr(x) if 32<=x<127 else '.' for x in c)))

print("=== RP bank4 0x3300-0x3A00 (cab name table at 0x3486) ===")
dump(RPB[4], 0x3300, 0x700, "RP b4")

print("=== RP: MOV DPTR,#imm16 references to cab-name base 0x3486 and nearby ===")
for k in range(16):
    hits=[]
    for i in range(0, 0x10000-2):
        if RPB[k][i]==0x90:
            v=RPB[k][i+1] | (RPB[k][i+2]<<8)
            if 0x3400 <= v < 0x3A00:
                hits.append((i,v))
    if hits:
        print("bank %d:" % k, [(hex(i),hex(v)) for i,v in hits[:20]])

print("=== GSP: MOV DPTR,#imm16 references to cab-name bases 0xD8C0 / 0x42FB ===")
for k in range(16):
    hits=[]
    for i in range(0, 0x10000-2):
        if GSPB[k][i]==0x90:
            v=GSPB[k][i+1] | (GSPB[k][i+2]<<8)
            if 0xD800 <= v < 0xDA40 or 0x4200 <= v < 0x4400:
                hits.append((i,v))
    if hits:
        print("bank %d:" % k, [(hex(i),hex(v)) for i,v in hits[:20]])

print("=== RP bank4: 16-bit values in 0x3400-0x3A00 (potential pointer table) ===")
for off in range(0, 0x10000-1, 2):
    v=struct.unpack_from('<H', RPB[4], off)[0]
    if 0x3400 <= v < 0x3A00:
        pass
# group
hits=[]
for off in range(0, 0x10000-1, 2):
    v=struct.unpack_from('<H', RPB[4], off)[0]
    if 0x3400 <= v < 0x3A00:
        hits.append((off,v))
groups=[];cur=[];last=None
for off,v in hits:
    if last is not None and off==last+2: cur.append((off,v))
    else:
        if len(cur)>=4: groups.append(cur)
        cur=[(off,v)]
    last=off
if len(cur)>=4: groups.append(cur)
for g in groups[:20]:
    print("table at 0x%04X (%d):" % (g[0][0],len(g)), [hex(v) for _,v in g])

print("=== RP 'CAB_TYPE' region 0x6C6F0-0x6C760 ===")
dump(RPB[6], 0x6C6F0, 0x80, "RP b6")
