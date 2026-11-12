# --- portable path resolution (added 2026-11-10) ---------------------------
import os as _os

_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_SW = _os.path.dirname(_os.path.abspath(__file__))

_FW = _os.path.join(_ROOT, "01_source_firmware")


def _OUT(name):
    """Route derived/output artifacts to the script directory."""
    return _os.path.join(_SW, name)



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
SH=_FW
rp=open(SH+r"\rp500_fw.bin",'rb').read()
def dump(img,lin,start,end,label):
    print("=== %s  linear 0x%X (b%d:%04X) ==="%(label,lin+(start&~0xFFFF) if False else lin, lin>>16, lin&0xFFFF))
    base=lin
    for a in range(start,end,16):
        c=img[base+a:base+a+16]
        print("   %04X  %-47s %s"%(a,c.hex(' '),''.join(chr(q) if 32<=q<127 else '.' for q in c)))

print("=== RP500 bank4 around cab name list 0x478E ===")
dump(rp,4*0x10000,0x4700,0x4900,"b4 cab list")
print()
print("=== RP500 bank4 0x4900-0x4D00 (after cab list) ===")
dump(rp,4*0x10000,0x4900,0x4D00,"b4 after")
print()
print("=== RP500 bank12 0x0000-0x0400 (shared high-entropy region) ===")
dump(rp,12*0x10000,0x0000,0x0400,"b12 head")
print()
print("=== RP500: look for 128-entry 16-bit tables (256B) repeating; scan for byte patterns 0x00,0x00 often ===")
# count runs of 256-byte blocks with plausible 16-bit coefficient stats
import struct
cands=[]
for off in range(0,len(rp)-256,256):
    blk=rp[off:off+256]
    vals=struct.unpack('<128h',blk)
    # coefficient-ish: small magnitudes, no huge values
    if max(abs(v) for v in vals)<20000 and sum(1 for v in vals if v!=0)>100:
        cands.append(off)
print("  plausible 128x16-bit blocks:",len(cands))
print("  first:",['b%d:%04X'%(o>>16,o&0xFFFF) for o in cands[:20]])
