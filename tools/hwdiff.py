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

def strings(data, minlen=4):
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

for name, data in [("GSP", GSPF), ("RP", RP)]:
    print("=== %s 'DNA' occurrences with context ===" % name)
    for m in re.finditer(rb'DNA', data):
        ctx = data[max(0,m.start()-48):m.start()+64]
        print("0x%06X %r" % (m.start(), ctx))
    print("=== %s version/copyright ===" % name)
    for m in re.finditer(rb'(?i)(version|v\d+\.\d+|copyright|\(c\)|20\d\d)', data):
        s = data[max(0,m.start()-16):m.start()+64]
        print("0x%06X %r" % (m.start(), s))
    print()

print("=== RP bank 15 strings ===")
for off,s in strings(RP[15*0x10000:16*0x10000], 4):
    print("0x%04X %r" % (off, s[:100]))

print("=== RP 'CAB' / 'SPKR' / 'USER' occurrences ===")
for off,s in strings(RP,4):
    low=s.lower()
    if "cab" in low or "spkr" in low or "user" in low or "impulse" in low:
        print("0x%06X %r" % (off, s[:100]))

print("=== GSP 'SPKR' / 'DIRECT' / 'DXRV' ===")
for off,s in strings(GSPF,4):
    low=s.lower()
    if "spkr" in low or "direct" in low or "dxrv" in low or "4x12" in low or "1x12" in low or "2x12" in low:
        print("0x%06X %r" % (off, s[:100]))
