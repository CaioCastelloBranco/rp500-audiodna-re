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
fwfile=open(SH+r"\gsp1101_fw.bin",'rb').read()
vc63exe=open(SH+r"\JUpdater Gsp1101vC63.exe",'rb').read()

def find_all(img,pat):
    out=[];i=0
    while True:
        j=img.find(pat,i)
        if j<0: break
        out.append(j); i=j+1
    return out

print("=== all vC63 bank headers in exe (ea 80 68 02 30 7a 53 91) ===")
h=find_all(vc63exe,bytes.fromhex("ea806802307a5391"))
print("  n=%d"%len(h))
print("  %s" % ['0x%X'%x for x in h[:20]])
if len(h)>1:
    print("  spacing:",[h[i+1]-h[i] for i in range(min(16,len(h)-1))])
B63=h[0]
print("  first bank payload @0x%X: %s"%(B63+8, vc63exe[B63+8:B63+30].hex(' ')))

ST=0x10008
b63=[vc63exe[B63+k*ST+8:B63+(k+1)*ST] for k in range(16)]

print()
print("=== does gsp1101_fw.bin == vC63.exe firmware? ===")
a=fwfile[0x19F8:0x19F8+16*ST]
b=vc63exe[B63:B63+16*ST]
print("  equal:",a==b," lenA",len(a),"lenB",len(b))
print("  sha A",hashlib.sha1(a).hexdigest()[:16]," sha B",hashlib.sha1(b).hexdigest()[:16])

# V20 banks (1MB, header+0xFFF8)
b20=[v20fw[k*0x10000+8:(k+1)*0x10000] for k in range(16)]
print()
print("=== per-bank equality V20 vs vC63 ===")
tot_same=tot=0
for k in range(16):
    n=min(len(b20[k]),len(b63[k]))
    same=sum(1 for i in range(n) if b20[k][i]==b63[k][i])
    tot_same+=same; tot+=n
    print("  bank%2d  %5.1f%%"%(k,100*same/n))
print("  TOTAL %.1f%%"%(100*tot_same/tot))

img20=b''.join(b20); img63=b''.join(b63)

print()
print("=== cab-name table search ===")
names=[b'CHAMP1X8',b'DLUX1X12',b'DIGISPKR',b'DREAD AC',b'JUMBO AC',b'TWIN',b'BRIT',b'4X12',b'DIRECT',b'BLACKFACE',b'ACOUSTIC']
for k in names:
    def loc(img):
        r=[];i=0
        while True:
            j=img.find(k,i)
            if j<0: break
            r.append(j); i=j+1
        return r
    h20=loc(img20); h63=loc(img63)
    def fmt(h):
        return [('b%d:%04X'%(x>>16,x&0xFFFF)) for x in h[:8]]
    print("  %-10s V20 %s   vC63 %s"%(k.decode('latin1'),fmt(h20),fmt(h63)))

print()
print("=== dump around V20 first 'CHAMP' / 'DREAD AC' ===")
for needle in (b'CHAMP',b'DREAD AC'):
    off=img20.find(needle)
    if off<0: 
        print("  %s not found"%needle); continue
    s=max(0,off-64); e=off+256
    print("  --- %s @ b%d:%04X ---"%(needle,off>>16,off&0xFFFF))
    for a in range(s,e,16):
        c=img20[a:a+16]
        print("   %04X  %-47s %s"%(a,c.hex(' '),''.join(chr(x) if 32<=x<127 else '.' for x in c)))

print()
print("=== dump around vC63 CHAMP1X8 ===")
off=img63.find(b'CHAMP1X8')
s=max(0,off-64); e=off+512
for a in range(s,e,16):
    c=img63[a:a+16]
    print("   %04X  %-47s %s"%(a,c.hex(' '),''.join(chr(x) if 32<=x<127 else '.' for x in c)))
