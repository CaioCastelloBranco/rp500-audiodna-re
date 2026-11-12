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
import struct, re, math, collections

SH=_FW
d=open(SH+r"\X-Edit.exe",'rb').read()
print("size",len(d),hex(len(d)))
print("PE end ~0x41000; overlay bytes:",len(d)-0x41000)
print("overlay first 64:",d[0x41000:0x41040].hex(' '))
print("overlay ascii   :",''.join(chr(b) if 32<=b<127 else '.' for b in d[0x41000:0x41040]))

# signatures
sigs={b'PK\x03\x04':'zip',b'MSCF':'cab',b'7z\xbc\xaf\x27\x1c':'7z',b'Rar!':'rar',
      b'\x1f\x8b\x08':'gzip',b'MZ':'PE',b'\x00\x00\x00\x00':'zeros'}
for s,name in sigs.items():
    hits=[];i=0
    while True:
        j=d.find(s,i)
        if j<0: break
        hits.append(j); i=j+1
    print("  %-6s n=%d first=%s"%(name,len(hits),['0x%X'%h for h in hits[:8]]))

# entropy in 64k windows over overlay
def ent(b):
    if not b: return 0
    c=collections.Counter(b); n=len(b)
    return -sum((v/n)*math.log2(v/n) for v in c.values())
print("\noverlay 64k entropy:")
for off in range(0x41000,len(d),0x10000):
    chunk=d[off:off+0x10000]
    print("  0x%06X ent=%.2f  head=%s"%(off,ent(chunk),chunk[:16].hex(' ')))

# try to detect .NET metadata
for pat in (b'mscoree.dll',b'_CorExeMain',b'BSJB',b'.NET Framework'):
    print("  %-14s %s"%(pat, d.find(pat)))
