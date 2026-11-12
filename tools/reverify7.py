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
import re
S = _FW
v20=[open(S+r'\v20_res_51E18.bin','rb').read()[k*0x10000:(k+1)*0x10000] for k in range(16)]
def bodies(img): return [img[k*0x10000+k*8:(k+1)*0x10000+k*8] for k in range(16)]
c63=bodies(open(S+r'\c63_fw.bin','rb').read())
c48=bodies(open(S+r'\c48_fw.bin','rb').read())
rp=[open(S+r'\rp500_fw.bin','rb').read()[k*0x10000:(k+1)*0x10000] for k in range(16)]

print('=== RP500 vs C63 per-bank byte identity ===')
tot=0
for k in range(16):
    e=sum(1 for x,y in zip(rp[k],c63[k]) if x==y); tot+=e
    print('  bank%-2d %5.1f%%'%(k,100*e/0x10000))
print('  overall %.1f%%'%(100*tot/(16*0x10000)))

print()
print('=== FIR-like 512B block scan (correct bodies) ===')
def scan(banks):
    import struct
    blocks=[]
    for k,b in enumerate(banks):
        for off in range(0, len(b)-512+1, 512):
            blk=b[off:off+512]
            vals=struct.unpack('>128i', blk)
            nz=sum(1 for v in vals if v!=0)
            small=sum(1 for v in vals if -0x80000000 <= v < 0x80000000)
            e=[v*v for v in vals]
            front=sum(e[:32]); back=sum(e[-32:])
            if nz>=120 and small>=120 and front > 2.5*(back+1):
                blocks.append((k,off))
    return blocks
for nm,bs in (('c48',c48),('c63',c63),('rp',rp),('v20',v20)):
    bl=scan(bs)
    # runs of consecutive blocks
    runs=[]
    for k,o in bl:
        if runs and runs[-1][0]==k and o-runs[-1][1]==512: runs[-1][1]=o
        else: runs.append([k,o])
    print('  %-4s blocks=%d  max_run=%d' % (nm, len(bl), max([ (r[1]-r[0])//512+1 for r in runs] or [0])))
