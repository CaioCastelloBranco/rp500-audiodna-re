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
import struct, hashlib

SH=_FW
v20fw=open(SH+r"\v20_res_51E18.bin",'rb').read()
fwfile=open(SH+r"\gsp1101_fw.bin",'rb').read()
vc63exe=open(SH+r"\JUpdater Gsp1101vC63.exe",'rb').read()

# vC63 firmware directly from exe
B63=0xC1E38; ST=0x10008
if vc63exe[B63:B63+8]!=bytes.fromhex("ea806802307a5391"):
    print("!! header mismatch at 0xC1E38:",vc63exe[B63:B63+8].hex(' '))
b63x=[vc63exe[B63+k*ST+8:B63+(k+1)*ST] for k in range(16)]

print("=== gsp1101_fw.bin[0x19F8:] == vC63.exe[0xC1E38:] ? ===")
a=fwfile[0x19F8:0x19F8+0x100000]
b=vc63exe[B63:B63+0x100000]
print("  equal:",a==b, " sha_a",hashlib.sha1(a).hexdigest()[:12]," sha_b",hashlib.sha1(b).hexdigest()[:12])

print()
print("=== vC63 exe banks: key strings ===")
img63=b''.join(b63x)
for k in (b'CHAMP1X8',b'USER 1',b'USER_CAB',b'DIGISPKR'):
    print("  %-10s %d"%(k.decode(),img63.count(k)))

print()
print("=== V20: broad cab-name search ===")
for k in (b'CHAMP',b'TWIN',b'BRIT',b'JAZZ',b'SPKR',b'CAB',b'4X12',b'1X12',b'2X12',b'DLUX',b'DIGI'):
    print("  %-7s %d"%(k.decode(),v20fw.count(k)))

print()
print("=== V20 bank11 0xD800-0xDA80 (where vC63 has cab list) ===")
B11=v20fw[11*0x10000+8:12*0x10000]
for a in range(0xD800,0xDA80,16):
    c=B11[a:a+16]
    print("  %04X  %-47s %s"%(a,c.hex(' '),''.join(chr(x) if 32<=x<127 else '.' for x in c)))

print()
print("=== vC63 exe bank11 0xD800-0xDA80 ===")
C11=b63x[11]
for a in range(0xD800,0xDA80,16):
    c=C11[a:a+16]
    print("  %04X  %-47s %s"%(a,c.hex(' '),''.join(chr(x) if 32<=x<127 else '.' for x in c)))

print()
print("=== VERSIONINFO / product strings in updaters ===")
for name,img in (("V20.exe",open(SH+r"\GSPUpdaterV20.exe",'rb').read()),
                 ("vC63.exe",vc63exe)):
    print("--",name)
    for k in (b'FileVersion',b'ProductVersion',b'ProductName',b'FileDescription',b'CompanyName'):
        i=img.find(k)
        if i>=0:
            seg=img[i:i+80]
            print("   %-15s %r"%(k.decode(),seg))
