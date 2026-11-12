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
import struct, math, collections

SH=_FW
v20=open(SH+r"\GSPUpdaterV20.exe",'rb').read()

def pe_sections(img):
    if img[:2]!=b'MZ': return None
    e=struct.unpack_from('<I',img,0x3C)[0]
    if img[e:e+4]!=b'PE\0\0': return None
    mach,nsec=struct.unpack_from('<HH',img,e+4)
    optsz=struct.unpack_from('<H',img,e+20)[0]
    opt=e+24
    base=opt+optsz
    out=[]
    for i in range(nsec):
        o=base+i*40
        name=img[o:o+8].rstrip(b'\0').decode('latin1')
        vsz,va,rsz,ro=struct.unpack_from('<IIII',img,o+8)
        out.append((name,va,vsz,ro,rsz))
    return mach,out

def ent(d):
    if not d: return 0
    c=collections.Counter(d); n=len(d)
    return -sum((v/n)*math.log2(v/n) for v in c.values())

info=pe_sections(v20)
print("PE:",info[0] if info else None)
for name,va,vsz,ro,rsz in info[1]:
    print("  %-8s VA=0x%08X vsz=0x%X raw=0x%X..0x%X  ent=%.2f"%(
        name,va,vsz,ro,ro+rsz,ent(v20[ro:ro+rsz])))

print()
print("=== entropy of raw file in 64KB windows (find compressed/embedded blobs) ===")
for off in range(0,len(v20),0x10000):
    d=v20[off:off+0x10000]
    e=ent(d)
    flag=' <== low' if e<6.0 else (' <== HIGH' if e>7.8 else '')
    if e<6.0 or e>7.8:
        print("  0x%06X  ent=%.2f%s"%(off,e,flag))

print()
print("=== firmware markers in V20.exe ===")
marks={
 'CHAMP1X8':b'CHAMP1X8','DLUX1X12':b'DLUX1X12','DIGISPKR':b'DIGISPKR',
 'DREAD AC':b'DREAD AC','JUMBO AC':b'JUMBO AC','USER 1':b'USER 1','USER 2':b'USER 2',
 'USER_CAB':b'USER_CAB','SEND BLOCK':b'SEND BLOCK','1/4 AMP':b'1/4 AMP','MONO':b'MONO',
 'reset 02 00 6B':bytes.fromhex('02006b'),'MOV P1,#FF 75 90 FF':bytes.fromhex('7590ff'),
}
for k,p in marks.items():
    n=v20.count(p)
    print("  %-20s %d"%(k,n))

print()
print("=== zlib/gzip candidates ===")
for sig,name in ((b'\x78\x9c','zlib 9c'),(b'\x78\xda','zlib da'),(b'\x1f\x8b\x08','gzip')):
    hits=[];i=0
    while True:
        j=v20.find(sig,i)
        if j<0: break
        hits.append(j); i=j+1
    print("  %-9s n=%d %s"%(name,len(hits),['0x%X'%h for h in hits[:10]]))

print()
print("=== where do the protocol strings sit? (offsets + section) ===")
for k in (b'USER_CAB',b'SEND BLOCK',b'BULK DUMP',b'FLASH_DATA',b'GSP1101',b'WAVE'):
    off=v20.find(k)
    sec='?'
    for name,va,vsz,ro,rsz in info[1]:
        if ro<=off<ro+rsz: sec=name
    print("  %-12s @0x%06X  section=%s"%(k.decode(),off,sec))
