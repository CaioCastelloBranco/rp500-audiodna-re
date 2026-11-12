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


RP=open(_P("rp_fw.bin"),'rb').read()
BANKS=[RP[k*0x10000:(k+1)*0x10000] for k in range(16)]

def dump(bank,a,b,label):
    d=BANKS[bank]
    print("===== %s bank%d:0x%04X-0x%04X ====="%(label,bank,a,b))
    for i in range(a,b,16):
        c=d[i:i+16]
        print("  %04X: %-47s %s"%(i,c.hex(' '),''.join(chr(x) if 32<=x<127 else '.' for x in c)))
    print()

dump(14,0x2D80,0x3100,"stream source table? bank14")
print("=== which banks have identical 256 bytes at 0x2DC2? ===")
ref=BANKS[14][0x2DC2:0x2DC2+256]
for k in range(16):
    same=BANKS[k][0x2DC2:0x2DC2+256]==ref
    print("bank%2d same=%s first16=%s"%(k,same,BANKS[k][0x2DC2:0x2DC2+16].hex(' ')))

print()
print("=== entropy / byte makeup per bank ===")
import math
for k in range(16):
    d=BANKS[k]
    from collections import Counter
    c=Counter(d)
    ent=-sum((n/len(d))*math.log2(n/len(d)) for n in c.values())
    print("bank%2d entropy=%.3f  00=%.1f%% ff=%.1f%%  asciiish=%.1f%%"%(
        k,ent,100*c[0]/len(d),100*c[0xFF]/len(d),
        100*sum(c[x] for x in range(32,127))/len(d)))
