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

def find(pat):
    out=[]; idx=0
    while True:
        i=RP.find(pat,idx)
        if i<0: break
        out.append(i); idx=i+1
    return out

print("=== MOV DPTR,#imm16 (90 hi lo) refs to descriptor addresses ===")
for v in (0x4224,0x4336,0x4355,0x4697,0x46B6,0x478C,0x40F6,0x3C8F):
    pat=bytes([0x90,(v>>8)&0xFF,v&0xFF])
    hits=find(pat)
    print("DPTR=#%04X  pat %s  n=%d  %s"%(v,pat.hex(),len(hits),
        [('b%d:%04X'%(h>>16,h&0xFFFF)) for h in hits[:20]]))

print()
print("=== little-endian 16-bit refs to descriptor addrs ===")
for v in (0x4224,0x4336,0x4355,0x4697,0x46B6,0x478C,0x40F6):
    pat=bytes([v&0xFF,(v>>8)&0xFF])
    hits=find(pat)
    print("LE %04X n=%d %s"%(v,len(hits),[('b%d:%04X'%(h>>16,h&0xFFFF)) for h in hits[:12]]))

print()
print("=== bank4 0x4800-0x5000 raw ===")
b=BANKS[4]
for a in range(0x4800,0x5000,16):
    c=b[a:a+16]
    print("0x%04X  %-47s  %s"%(a,c.hex(' '),''.join(chr(x) if 32<=x<127 else '.' for x in c)))

print()
print("=== bank0 0x0400-0x0500 raw (possible name ptr targets) ===")
b0=BANKS[0]
for a in range(0x0400,0x0500,16):
    c=b0[a:a+16]
    print("0x%04X  %-47s  %s"%(a,c.hex(' '),''.join(chr(x) if 32<=x<127 else '.' for x in c)))
