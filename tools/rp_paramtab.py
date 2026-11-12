# --- portable path resolution (added 2026-11-10) ---------------------------
import os as _os

_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_SW = _os.path.dirname(_os.path.abspath(__file__))


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


RP=open(_P("rp_fw.bin"),'rb').read()
B6=RP[6*0x10000:7*0x10000]
B4=RP[4*0x10000:5*0x10000]

def cstr(bank,off,maxn=20):
    out=[]
    for i in range(off,min(off+maxn,len(bank))):
        if bank[i]==0: break
        out.append(chr(bank[i]) if 32<=bank[i]<127 else '?')
    return ''.join(out)

print("=== bank6 0xC500-0xCA80 raw ===")
for a in range(0xC500,0xCA80,16):
    c=B6[a:a+16]
    print("0x%04X  %-47s  %s"%(a,c.hex(' '),''.join(chr(x) if 32<=x<127 else '.' for x in c)))

print()
print("=== 86 x 18-byte records at 0xC551 ===")
start=0xC551
for i in range(86):
    rec=B6[start+i*0x12:start+(i+1)*0x12]
    hexs=rec.hex(' ')
    be=[ (rec[j]<<8)|rec[j+1] for j in range(0,16,2)]
    s=rec.split(b'\x00')[0]
    try: name=s.decode('ascii')
    except: name=repr(s)
    ptrs=[]
    for j in range(0,16,2):
        v=(rec[j]<<8)|rec[j+1]
        if 0!=(v>>8):
            ps=cstr(B6,v,18) if 0x8000<=v<0x10000 else ""
        else:
            ps=""
    print("%2d  0x%04X  %-40s  %s" % (i, start+i*0x12, hexs, name))
