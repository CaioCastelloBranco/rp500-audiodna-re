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
img=open(SH+r"\GSPUpdaterV20.exe",'rb').read()

def sections(img):
    e=struct.unpack_from('<I',img,0x3C)[0]
    nsec=struct.unpack_from('<H',img,e+6)[0]
    optsz=struct.unpack_from('<H',img,e+20)[0]
    base=e+24+optsz
    out=[]
    for i in range(nsec):
        o=base+i*40
        name=img[o:o+8].rstrip(b'\0').decode('latin1')
        vsz,va,rsz,ro=struct.unpack_from('<IIII',img,o+8)
        out.append(dict(name=name,va=va,vsz=vsz,ro=ro,rsz=rsz))
    return out

secs=sections(img)
rsrc=[s for s in secs if s['name']=='.rsrc'][0]
print("rsrc:",rsrc)

base=rsrc['ro']
def walk(off,level,path,out):
    n_named,n_id=struct.unpack_from('<HH',img,base+off+12)
    for i in range(n_named+n_id):
        e=base+off+16+i*8
        name,off2=struct.unpack_from('<II',img,e)
        isdir=bool(off2&0x80000000)
        o=off2&0x7FFFFFFF
        if name&0x80000000:
            so=base+(name&0x7FFFFFFF)
            ln=struct.unpack_from('<H',img,so)[0]
            nm=img[so+2:so+2+ln*2].decode('utf-16le','ignore')
        else:
            nm=name
        if isdir:
            walk(o,level+1,path+[nm],out)
        else:
            rva,sz,cp,res=struct.unpack_from('<IIII',img,base+o)
            foff=rva-rsrc['va']+rsrc['ro']
            out.append((tuple(path),nm,sz,rva,foff))
walk(0,0,[],out:=[])

print("resources (size >= 0x1000):")
for path,nm,sz,rva,foff in out:
    if sz>=0x1000:
        print("  %-26s id=%-6s size=0x%-7X rva=0x%-7X foff=0x%X"%(path,nm,sz,rva,foff))

print()
print("resources containing file offset 0x145000:")
for path,nm,sz,rva,foff in out:
    if foff<=0x145000<foff+sz:
        print("  %-26s id=%-6s size=0x%X foff=0x%X"%(path,nm,sz,foff))
        d=img[foff:foff+sz]
        print("  first 32:",d[:32].hex(' '))
        print("  sha1:",hashlib.sha1(d).hexdigest()[:16])
        open(SH+r"\v20_res_%X.bin"%foff,'wb').write(d)
