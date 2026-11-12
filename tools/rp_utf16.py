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
BANKS=[RP[k*0x10000:(k+1)*0x10000] for k in range(16)]

def find_all(pat):
    out=[]; i=0
    while True:
        j=RP.find(pat,i)
        if j<0: break
        out.append(j); i=j+1
    return out

def u16(s):
    return s.encode('utf-16le')

def u16be(s):
    return s.encode('utf-16be')

terms=['XLR','BALANCED','BAL','CABINET','CAB ','CAB','CABSIM','CAB SIM','SPEAKER','SPKR',
       'AMP','MIX','OUTPUT','MONO','STEREO','DIRECT','LINE','MIC','PHANTOM','GROUND','LIFT',
       '1/4','USB OUT','REC GAIN','AMP/CAB']
print("=== UTF-16LE and UTF-16BE search ===")
for t in terms:
    a=find_all(u16(t)); b=find_all(u16be(t))
    if a or b:
        print("  %-10s LE n=%d %s"%(t,len(a),[('b%d:%04X'%(h>>16,h&0xFFFF)) for h in a[:8]]))
        if b: print("             BE n=%d %s"%(len(b),[('b%d:%04X'%(h>>16,h&0xFFFF)) for h in b[:8]]))
    else:
        print("  %-10s (none)"%t)

print()
print("=== relationship b14 0x2DC2 blob vs b15 0x2E3B vs b15 0x2DC2 ===")
a=BANKS[14][0x2DC2:0x2DC2+0x8000]
b=BANKS[15][0x2E3B:0x2E3B+0x8000]
print("  b14[2DC2:+32K] == b15[2E3B:+32K] ?", a==b)
print("  b14[2DC3:+32K] == b15[2E3B:+32K] ?", BANKS[14][0x2DC3:0x2DC3+0x8000]==b)
c=BANKS[15][0x2DC2:0x2DC2+0x8000]
print("  b14[2DC2:+32K] == b15[2DC2:+32K] ?", a==c)

print()
print("=== does b14 0x2DC2..0xADC2 equal any other 32KB window? (first 64B match) ===")
sig=BANKS[14][0x2DC2:0x2DC2+64]
i=0; hits=[]
while True:
    j=RP.find(sig,i)
    if j<0: break
    hits.append(j); i=j+1
print("  first64 matches:",[('b%d:%04X'%(h>>16,h&0xFFFF)) for h in hits])

print()
print("=== where are ASCII UI strings? count ASCII vs UTF-16 in bank4 ===")
B4=BANKS[4]
def is_ascii_run(d):
    n=0
    for i in range(len(d)-4):
        if all(32<=d[i+k]<127 for k in range(4)): n+=1
    return n
print("  bank4 ascii-ish 4-runs:",is_ascii_run(B4))
# count utf16 ascii runs
n=0
for i in range(0,len(B4)-8,1):
    if B4[i+1]==0 and B4[i+3]==0 and B4[i+5]==0:
        if all(32<=B4[i+2*k]<127 for k in range(4)): n+=1
print("  bank4 utf16 4-runs:",n)

print()
print("=== bank4 0x2D90-0x2DE0 raw (what is 0x2DAC placeholder) ===")
for a in range(0x2D90,0x2DF0,16):
    c=B4[a:a+16]
    print("  %04X: %-47s %s"%(a,c.hex(' '),''.join(chr(x) if 32<=x<127 else '.' for x in c)))
