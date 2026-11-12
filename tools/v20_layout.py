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
v20fw=open(SH+r"\v20_res_51E18.bin",'rb').read()
fw63 =open(SH+r"\gsp1101_fw.bin",'rb').read()
print("v20 BINFILE size",len(v20fw),hex(len(v20fw)))

HDR20=bytes.fromhex("ea8068022ec55391")
HDR63=bytes.fromhex("ea806802307a5391")
TRAM =bytes.fromhex("df3200c086758600")

def find_all(img,pat):
    out=[];i=0
    while True:
        j=img.find(pat,i)
        if j<0: break
        out.append(j); i=j+1
    return out

for nm,pat in (("HDR20",HDR20),("HDR63",HDR63),("TRAM",TRAM)):
    h=find_all(v20fw,pat)
    print("%s n=%d  %s"%(nm,len(h),['0x%X'%x for x in h[:20]]))
    if len(h)>1:
        print("   spacing:",[h[i+1]-h[i] for i in range(min(18,len(h)-1))])

print()
print("=== tail bytes around bank boundaries (to see header-at-end vs start) ===")
for o in (0xFFF8,0x10000,0x1FFF8,0x20000,0xFFFF8):
    print("  0x%06X: %s"%(o,v20fw[o:o+16].hex(' ')))

# vC63 bank payloads
B63=0x19F8; ST=0x10008
b63=[fw63[B63+k*ST+8:B63+(k+1)*ST] for k in range(16)]
print()
print("vC63 bank lengths:",set(len(x) for x in b63))

# Hypothesis A: V20 = 16 x (8-byte hdr + 0xFFF8 payload) at 0x10000 spacing
print()
print("=== hypothesis A: 16 banks @0x10000, hdr + 0xFFF8 payload ===")
h=find_all(v20fw,HDR20)
print("header count:",len(h))
if h:
    b20=[]
    for k in range(16):
        o=k*0x10000
        b20.append(v20fw[o+8:o+0x10000])
    for k in range(16):
        a=b63[k]; b=b20[k]
        # compare with 8-byte shift both ways
        same_shift0 = a[:len(b)]==b
        same_shift8 = a[8:8+len(b)]==b
        print("  bank%2d lenA=%d lenB=%d eq(A,B)=%s eq(A[8:],B)=%s"%(
            k,len(a),len(b),same_shift0,same_shift8))
