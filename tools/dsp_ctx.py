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

print("=== GSP bank13 0x3000-0x3400 (SDRAM/DNA diagnostics) ===")
dump(GSPB[13], 0x3000, 0x400, "GSP b13")
print("=== GSP bank13 0x2E00-0x3000 ===")
dump(GSPB[13], 0x2E00, 0x200, "GSP b13")
print("=== RP bank4 0x3D00-0x3F00 (DSP ON/DSPBYP/DSP 3/DSP 4) ===")
dump(RPB[4], 0x3D00, 0x200, "RP b4")
print("=== GSP bank4 0x5000-0x5200 (same string area) ===")
# GSP DSP ON flat 0x0550D4 = bank5 0x50D4
dump(GSPB[5], 0x5000, 0x200, "GSP b5")

print()
print("=== RP: XDATA writes via MOVX @DPTR,A (F0) right after 'MOV DPTR,#imm' in bank4/bank6/bank0 ===")
for k in (0,4,6,7):
    b=RPB[k]
    hits=[]
    for i in range(0,0x10000-4):
        if b[i]==0x90:
            ptr=b[i+1]|(b[i+2]<<8)
            # look ahead 8 bytes for F0 (MOVX @DPTR,A) or E0 (MOVX A,@DPTR)
            for j in range(i+3,min(i+12,0x10000)):
                if b[j] in (0xF0,0xE0):
                    hits.append((i,ptr,b[j]))
                    break
    print("RP bank %d: %d MOV DPTR + MOVX pairs" % (k,len(hits)))
    from collections import Counter
    c=Counter(ptr for _,ptr,_ in hits)
    print("  top DPTR targets:", [(hex(v),n) for v,n in c.most_common(15)])
