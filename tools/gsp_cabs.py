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
v20fw=open(SH+r"\v20_res_51E18.bin",'rb').read()
fwfile=open(SH+r"\gsp1101_fw.bin",'rb').read()

B63=0xC0FF8; ST=0x10008
def find_all(img,pat):
    out=[];i=0
    while True:
        j=img.find(pat,i)
        if j<0: break
        out.append(j); i=j+1
    return out
vc63exe=open(SH+r"\JUpdater Gsp1101vC63.exe",'rb').read()
B63=find_all(vc63exe,bytes.fromhex("ea806802307a5391"))[0]
b63=[vc63exe[B63+k*ST+8:B63+(k+1)*ST] for k in range(16)]
b20=[v20fw[k*0x10000+8:(k+1)*0x10000] for k in range(16)]
img20=b''.join(b20); img63=b''.join(b63)

def dump(img,base,start,end):
    print("  base b%d  range 0x%04X-0x%04X"%(base,start,end))
    for a in range(start,end,16):
        c=img[base*0x10000+a:base*0x10000+a+16]
        print("   %04X  %-47s %s"%(a,c.hex(' '),''.join(chr(x) if 32<=x<127 else '.' for x in c)))

print("=== V20 bank10 0x5600-0x5A40 ===")
dump(img20,10,0x5600,0x5A40)
print()
print("=== vC63 bank11 0xD600-0xDA80 ===")
dump(img63,11,0xD600,0xDA80)

print()
print("=== 'USER' occurrences ===")
for nm,img in (("V20",img20),("vC63",img63)):
    hs=find_all(img,b'USER')
    print("  %s n=%d"%(nm,len(hs)))
    for h in hs[:20]:
        s=img[h:h+24].split(b'\0')[0]
        print("    b%d:%04X  %r"%(h>>16,h&0xFFFF,s))

print()
print("=== 'GLOBAL CABINET' / 'NO CABINET' occurrences ===")
for nm,img in (("V20",img20),("vC63",img63)):
    for k in (b'GLOBAL CABINET',b'NO CABINET',b'CABINET',b'GLOBAL'):
        hs=find_all(img,k)
        if hs:
            print("  %s %-15s %s"%(nm,k.decode(),[('b%d:%04X'%(x>>16,x&0xFFFF)) for x in hs[:8]]))

print()
print("=== V20 bank10 cab table from 0x57A0 ===")
dump(img20,10,0x57A0,0x58A0)
