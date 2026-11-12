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


import struct
RP=open(_P("rp_fw.bin"),'rb').read()
B=RP[4*0x10000:5*0x10000]

def dump(bank,a,b,tag):
    print("--- %s 0x%04X-0x%04X ---"%(tag,a,b))
    for i in range(a,b,16):
        c=bank[i:i+16]
        print("0x%04X  %-47s  %s"%(i,c.hex(' '),''.join(chr(x) if 32<=x<127 else '.' for x in c)))

def cstr(bank,off,maxn=24):
    out=[]
    for i in range(off,min(off+maxn,len(bank))):
        if bank[i]==0: break
        out.append(chr(bank[i]) if 32<=bank[i]<127 else '?')
    return ''.join(out)

dump(B,0x4210,0x4340,"PRE/POST record")
print()
dump(B,0x4320,0x4380,"MONO/1-4 records")
print()
dump(B,0x4680,0x4740,"AMP SEL/CAB SEL/AMP list")
print()
dump(B,0x4780,0x4800,"CAB list header")

print()
print("=== BE16 refs to descriptor addresses across whole image ===")
targets = {
 'PRE/POST list 0x4224':0x4224, '0x4226':0x4226,
 'MONO/STEREO list 0x4336':0x4336,'0x4337':0x4337,'0x4338':0x4338,
 '1/4 list 0x4355':0x4355,'0x4357':0x4357,
 'AMP SEL list 0x4697':0x4697,'0x4699':0x4699,
 'AMP list 0x46B6':0x46B6,'0x46B8':0x46B8,
 'CAB list 0x478C':0x478C,'0x478E':0x478E,
}
for name,v in targets.items():
    be=bytes([v>>8,v&0xFF])
    hits=[]
    idx=0
    while True:
        i=RP.find(be,idx)
        if i<0: break
        hits.append(i); idx=i+1
    print("%-26s 0x%04X  n=%d  %s" % (name,v,len(hits),[('b%d:%04X'%(h>>16,h&0xFFFF)) for h in hits[:20]]))

print()
print("=== BE16 refs to the string/table area 0x2c00-0x3600 from bank4 near descriptor table ===")
# look for a pointer array in 0x4800-0x5000
for i in range(0x4800,0x5000,2):
    v=(B[i]<<8)|B[i+1]
    if 0x4000<=v<0x4900:
        print("0x%04X -> 0x%04X"%(i,v))

print()
print("=== strings 0x35E0-0x3650 (tail of string area) ===")
off=0x35E0
while off<0x3680:
    s=cstr(B,off,24)
    if s:
        print("0x%04X %r"%(off,s)); off+=len(s)+1
    else:
        print("0x%04X %02X"%(off,B[off])); off+=1
