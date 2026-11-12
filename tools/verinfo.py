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
import struct, re

SH=_FW

def versioninfo_strings(path):
    img=open(path,'rb').read()
    # find VS_VERSION_INFO in utf-16le or ascii
    res=[]
    for enc,pat in (("u16", "VS_VERSION_INFO".encode("utf-16le")),
                    ("a",   b"VS_VERSION_INFO")):
        i=img.find(pat)
        if i>=0: res.append((enc,i))
    out={}
    for enc,i in res:
        # just scan a wide window for utf-16 pairs and ascii runs
        seg=img[max(0,i-0x200): i+0x800]
        # extract utf-16le strings
        txt=seg.decode('utf-16le','ignore')
        vals=re.findall(r'[ -~]{3,}', txt)
        out.setdefault(enc,[]).extend(vals)
    return out

for name in ("GSPUpdaterV20.exe","JUpdater Gsp1101vC63.exe","X-Edit.exe"):
    p=SH+"\\"+name
    print("="*70)
    print(name)
    try:
        vi=versioninfo_strings(p)
        for enc,vals in vi.items():
            # filter useful
            interesting=[v for v in vals if any(k in v for k in
                ("Version","version","Product","GSP","DigiTech","Updater","2.0","C63","1.0","Copyright","Company"))]
            print("  [%s] %s"%(enc, interesting[:40]))
    except Exception as e:
        print("  err",e)

print()
print("="*70)
print("firmware version-ish strings")
v20=open(SH+r"\v20_res_51E18.bin",'rb').read()
fw63=open(SH+r"\gsp1101_fw.bin",'rb').read()
B63=0xC0FF8; ST=0x10008
exe=open(SH+r"\JUpdater Gsp1101vC63.exe",'rb').read()
hits=[]
i=0
pat=bytes.fromhex("ea806802307a5391")
while True:
    j=exe.find(pat,i)
    if j<0: break
    hits.append(j); i=j+1
B63=hits[0]
b63=b''.join(exe[B63+k*ST+8:B63+(k+1)*ST] for k in range(16))
b20=b''.join(v20[k*0x10000+8:(k+1)*0x10000] for k in range(16))

def strings(d,minlen=4):
    out=[];i=0
    while i<len(d):
        if 32<=d[i]<127:
            s=i
            while i<len(d) and 32<=d[i]<127: i+=1
            if i-s>=minlen: out.append((s,d[s:i].decode('ascii')))
        else: i+=1
    return out

for nm,img in (("V20",b20),("vC63",b63)):
    print("--",nm)
    for off,s in strings(img):
        if re.search(r'(?i)(c63|v2\.|2\.0|ver[ .:]|version|firmware|boot|build)',s):
            if len(s)<60:
                print("   b%d:%04X  %r"%(off>>16,off&0xFFFF,s))
