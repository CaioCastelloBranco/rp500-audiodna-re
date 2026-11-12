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
import hashlib

SH=_FW
v20=open(SH+r"\GSPUpdaterV20.exe",'rb').read()
fw63=open(SH+r"\gsp1101_fw.bin",'rb').read()

# vC63: first header at 0x19F8, stride 0x10008, payload = header+8
BASE63=0x19F8
BANK=0x10008
b63=[fw63[BASE63+k*BANK+8:BASE63+(k+1)*BANK] for k in range(16)]
print("vC63 bank0  first16:",b63[0][:16].hex(' '))
print("vC63 bank15 first16:",b63[15][:16].hex(' '))
print("vC63 bank0  sha1:",hashlib.sha1(b63[0]).hexdigest()[:16], "len",len(b63[0]))

for k in (0,15):
    sig=b63[k][:24]
    hits=[];i=0
    while True:
        j=v20.find(sig,i)
        if j<0: break
        hits.append(j); i=j+1
    print("bank%d sig %s -> V20 hits %s"%(k,sig.hex(' '),['0x%X'%h for h in hits[:8]]))

# derive base from bank0 hit
sig=b63[0][:24]
h0=v20.find(sig)
print()
print("bank0 payload candidate at 0x%X"%h0)
print("  header-8 @0x%X: %s"%(h0-8, v20[h0-8:h0].hex(' ')))
# verify 16 banks
ok=all(v20[h0+k*BANK:h0+k*BANK+24]==b63[k][:24] for k in range(16)) if h0>=0 else False
print("  all 16 bank starts match vC63 start bytes:",ok)

if ok:
    b20=[v20[h0+k*BANK:h0+k*BANK+0x10000] for k in range(16)]
    print()
    print("=== per-bank compare vC63 vs V20 ===")
    for k in range(16):
        same=b20[k]==b63[k]
        print("  bank%2d  same=%s  sha_v20=%s  sha_v63=%s"%(
            k,same,hashlib.sha1(b20[k]).hexdigest()[:12],hashlib.sha1(b63[k]).hexdigest()[:12]))
    open(SH+r"\v20_fw.bin",'wb').write(b''.join(b20))
    print("  wrote v20_fw.bin")

print()
print("=== header bytes at each V20 bank start-8 ===")
for k in range(16):
    o=h0+k*BANK
    print("  bank%2d header @0x%X: %s"%(k,o-8,v20[o-8:o].hex(' ')))
