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

GSPF = open(_P("gsp_fw.bin"),'rb').read()
GSP = [GSPF[k*0x10000:(k+1)*0x10000] for k in range(16)]
b = GSP[15]

print("=== 16-bit values in bank15 pointing into 0x3200-0x3A00 (possible pointer table) ===")
hits=[]
for off in range(0, 0x10000-1, 2):
    v = struct.unpack_from('<H', b, off)[0]
    if 0x3200 <= v < 0x3A00:
        hits.append((off, v))
# group consecutive
groups=[]; cur=[]
last=None
for off,v in hits:
    if last is not None and off==last+2:
        cur.append((off,v))
    else:
        if len(cur)>=3: groups.append(cur)
        cur=[(off,v)]
    last=off
if len(cur)>=3: groups.append(cur)
for g in groups[:20]:
    print("table at 0x%04X (%d entries):" % (g[0][0], len(g)), [hex(v) for _,v in g])

print("=== 16-bit values pointing into 0x3200-0x3A00 anywhere in whole firmware ===")
for k in range(16):
    hh=[]
    for off in range(0, 0x10000-1, 2):
        v = struct.unpack_from('<H', GSP[k], off)[0]
        if 0x3200 <= v < 0x3A00:
            hh.append((off,v))
    if hh:
        # group
        groups=[]; cur=[]; last=None
        for off,v in hh:
            if last is not None and off==last+2: cur.append((off,v))
            else:
                if len(cur)>=4: groups.append(cur)
                cur=[(off,v)]
            last=off
        if len(cur)>=4: groups.append(cur)
        if groups:
            print("bank %d:" % k, [("0x%04X"%g[0][0], len(g)) for g in groups[:6]])

print("=== dump bank15 0x2C00-0x3240 ===")
for i in range(0x2C00, 0x3240, 16):
    c=b[i:i+16]
    print("0x%04X  %-47s  %s" % (i, c.hex(' '), ''.join(chr(x) if 32<=x<127 else '.' for x in c)))
