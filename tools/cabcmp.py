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


import re

GSPF = open(_P("gsp_fw.bin"),'rb').read()
RP   = open(_P("rp_fw.bin"),'rb').read()

GSP_B11 = GSPF[11*0x10000:12*0x10000]
print("=== GSP bank11 cab short-name table 0xD8C0-0xDA20 (NUL separated) ===")
seg = GSP_B11[0xD8C0:0xDA20]
for s in seg.split(b'\x00'):
    if s and all(32<=c<127 for c in s):
        print(repr(s.decode()))

names = [s.decode() for s in seg.split(b'\x00') if s and all(32<=c<127 for c in s)]
print("count", len(names))

print("=== locate each name in RP ===")
for n in names:
    idx = RP.find(n.encode())
    print("%-12s -> %s" % (n, hex(idx) if idx>=0 else "MISSING"))

print("=== RP strings in 0x43000-0x43600 ===")
def strings(data, minlen=3):
    out=[]; cur=bytearray(); start=0
    for i,c in enumerate(data):
        if 32 <= c <= 126:
            if not cur: start=i
            cur.append(c)
        else:
            if len(cur)>=minlen: out.append((start,cur.decode('ascii')))
            cur=bytearray()
    if len(cur)>=minlen: out.append((start,cur.decode('ascii')))
    return out
for off,s in strings(RP,3):
    if 0x43000 <= off < 0x43600:
        print("0x%06X %r" % (off,s))

print("=== RP 'USER' exact ===")
for m in re.finditer(rb'USER', RP):
    print("0x%06X %r" % (m.start(), RP[m.start()-16:m.start()+40]))
