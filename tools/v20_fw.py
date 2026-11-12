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
import zlib, gzip, io, struct

SH=_FW
v20=open(SH+r"\GSPUpdaterV20.exe",'rb').read()

def dump(a,b):
    for i in range(a,b,16):
        c=v20[i:i+16]
        print("  0x%06X  %-47s  %s"%(i,c.hex(' '),''.join(chr(x) if 32<=x<127 else '.' for x in c)))

print("=== around protocol strings 0x144F00-0x145500 ===")
dump(0x144F00,0x145500)

print()
print("=== try zlib/gzip decompression at candidate offsets ===")
cands=set()
for sig in (b'\x78\x01',b'\x78\x9c',b'\x78\xda',b'\x1f\x8b\x08'):
    i=0
    while True:
        j=v20.find(sig,i)
        if j<0: break
        cands.add(j); i=j+1
# also scan every offset in .rsrc start region for a valid zlib header
for off in sorted(cands):
    for wbits in (15,-15,31):
        try:
            d=zlib.decompressobj(wbits)
            out=d.decompress(v20[off:off+4_000_000])
            out+=d.flush()
            if len(out)>=0x10000:
                print("  off=0x%X wbits=%d -> %d bytes  first=%s"%(off,wbits,len(out),out[:16].hex(' ')))
                # save candidates
                open(SH+r"\v20_dec_%X.bin"%off,'wb').write(out)
        except Exception:
            pass

print()
print("=== look for repeated 8-byte magic at 0x10008 / 0x10000 spacing (uncompressed bank format) ===")
# check a sample of offsets in first 0x20000
found=[]
for base in range(0, 0x20000):
    if base+16*0x10008 > len(v20): break
    m=v20[base:base+8]
    if m==b'\x00'*8 or m==b'\xff'*8: continue
    ok=True
    for k in range(1,16):
        if v20[base+k*0x10008:base+k*0x10008+8]!=m:
            ok=False; break
    if ok:
        found.append((base,m.hex()))
print("  0x10008-spacing candidates:",found[:20])
found2=[]
for base in range(0, 0x20000):
    if base+16*0x10000 > len(v20): break
    m=v20[base:base+8]
    if m==b'\x00'*8 or m==b'\xff'*8: continue
    ok=True
    for k in range(1,16):
        if v20[base+k*0x10000:base+k*0x10000+8]!=m:
            ok=False; break
    if ok:
        found2.append((base,m.hex()))
print("  0x10000-spacing candidates:",found2[:20])
