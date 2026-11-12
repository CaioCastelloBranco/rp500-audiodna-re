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


import difflib, struct

GSPF = open(_P("gsp_fw.bin"),'rb').read()
RP   = open(_P("rp_fw.bin"),'rb').read()
GSP=[GSPF[k*0x10000:(k+1)*0x10000] for k in range(16)]
RPB=[RP[k*0x10000:(k+1)*0x10000] for k in range(16)]

def dump(bank, off, n, tag):
    print("--- %s 0x%04X ---" % (tag, off))
    for i in range(off, off+n, 16):
        c=bank[i:i+16]
        print("0x%04X  %-47s  %s" % (i, c.hex(' '), ''.join(chr(x) if 32<=x<127 else '.' for x in c)))

print("=== GSP vs RP bank11 around cab name table 0xD8C0-0xDC00 ===")
a=GSP[11]; b=RPB[11]
for off in range(0xD8C0, 0xDC00, 64):
    same = a[off:off+64]==b[off:off+64]
    print("0x%04X same=%s" % (off, same))
    if not same:
        # count equal
        eq=sum(x==y for x,y in zip(a[off:off+64],b[off:off+64]))
        print("   eq=%d/64" % eq)

print("=== GSP bank11 0xD8C0-0xDC00 ===")
dump(a, 0xD8C0, 0x340, "GSP b11")
print("=== RP bank11 0xD8C0-0xDC00 ===")
dump(b, 0xD8C0, 0x340, "RP b11")

print("=== GSP vs RP bank5 0x42E0-0x4800 ===")
a5=GSP[5]; b5=RPB[5]
for off in range(0x42E0, 0x4800, 64):
    if a5[off:off+64]!=b5[off:off+64]:
        eq=sum(x==y for x,y in zip(a5[off:off+64],b5[off:off+64]))
        print("0x%04X eq=%d/64" % (off,eq))

print("=== longest common substrings between GSP and RP (sampled) ===")
# find long identical runs at same offset between GSP bank and RP bank
for k in range(16):
    a=GSP[k]; b=RPB[k]
    runs=[]; s=None
    for i in range(0x10000):
        if a[i]==b[i]:
            if s is None: s=i
        else:
            if s is not None:
                if i-s>=64: runs.append((s,i-s))
                s=None
    if s is not None and 0x10000-s>=64: runs.append((s,0x10000-s))
    runs.sort(key=lambda t:-t[1])
    print("bank %2d top same-offset runs:" % k, [(hex(o),hex(l)) for o,l in runs[:6]])
