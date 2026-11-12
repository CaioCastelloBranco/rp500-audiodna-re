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

print("=== RP bank4 0x4700-0x47C0 (pointer table with 0x3486) ===")
dump(RPB[4], 0x4700, 0xC0, "RP b4")
print("as 16-bit LE words:")
for i in range(0x4700,0x47C0,16):
    vals=[RPB[4][i+2*j]|(RPB[4][i+2*j+1]<<8) for j in range(8)]
    print("0x%04X  %s" % (i, ' '.join('%04X'%v for v in vals)))

print("=== GSP bank11 0xC100-0xC500 (contains 0xD8C0 const) ===")
dump(GSPB[11], 0xC100, 0x400, "GSP b11")
print("as 16-bit LE words:")
for i in range(0xC100,0xC500,16):
    vals=[GSPB[11][i+2*j]|(GSPB[11][i+2*j+1]<<8) for j in range(8)]
    print("0x%04X  %s" % (i, ' '.join('%04X'%v for v in vals)))

print("=== RP bank6 0xCB40-0xCC00 (after 86-name table ending 0xCB5D) ===")
dump(RPB[6], 0xCB40, 0xC0, "RP b6")

print("=== RP bank6 0xC500-0xC551 (before name table) ===")
dump(RPB[6], 0xC500, 0x60, "RP b6")
