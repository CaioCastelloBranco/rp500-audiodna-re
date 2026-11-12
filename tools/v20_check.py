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
import os, hashlib

SH=_FW
v20=open(os.path.join(SH,"GSPUpdaterV20.exe"),'rb').read()
vc63=open(os.path.join(SH,"JUpdater Gsp1101vC63.exe"),'rb').read()
fw63=open(os.path.join(SH,"gsp1101_fw.bin"),'rb').read()

HDR=bytes.fromhex("ea8068023 07a5391".replace(" ",""))
print("header len",len(HDR),HDR.hex())

def find_all(img,pat):
    out=[];i=0
    while True:
        j=img.find(pat,i)
        if j<0: break
        out.append(j); i=j+1
    return out

print("=== bank header occurrences ===")
print(" V20 :",find_all(v20,HDR))
print(" vC63:",find_all(vc63,HDR))
print(" fw  :",find_all(fw63,HDR))

# also look for repeated 8-byte block every 0x10008
def scan_headers(img,label):
    hits=find_all(img,HDR)
    print("%s: %d headers"% (label,len(hits)))
    if len(hits)>=2:
        print("   spacing:", [hits[i+1]-hits[i] for i in range(min(6,len(hits)-1))])
    return hits
scan_headers(v20,"V20")
scan_headers(vc63,"vC63")

KEY=[b'USER_CAB',b'SEND BLOCK',b'BULK DUMP',b'FLASH_DATA',b'USER AMP',b'USER 1',b'USER 2',
     b'IMPULSE',b'CONVOL',b'CABINET',b'.wav',b'.WAV',b'.aif',b'WAVE',b'IR FILE',b'IRFILE',
     b'VERSION',b'GSP1101',b'RP500',b'RP 500']
print()
print("=== key strings in each binary ===")
for name,img in (("V20.exe",v20),("vC63.exe",vc63),("fw63",fw63)):
    print("--",name)
    for k in KEY:
        n=img.count(k)
        if n: print("   %-12s %d"%(k.decode('latin1'),n))

print()
print("=== sizes / hashes ===")
for name,img in (("V20.exe",v20),("vC63.exe",vc63),("fw63",fw63)):
    print(" %-10s size=%d sha1=%s"%(name,len(img),hashlib.sha1(img).hexdigest()[:16]))
