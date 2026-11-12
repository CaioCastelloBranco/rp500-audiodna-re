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
import re, struct

SH=_FW

def strings(d,minlen=4):
    out=[];i=0
    while i<len(d):
        if 32<=d[i]<127:
            s=i
            while i<len(d) and 32<=d[i]<127: i+=1
            if i-s>=minlen: out.append((s,d[s:i].decode('ascii')))
        else: i+=1
    return out

print("="*70)
print("X-Edit.exe : model + IR related strings")
x=open(SH+r"\X-Edit.exe",'rb').read()
print(" size",len(x))
# ascii strings
ss=[s for _,s in strings(x,4)]
print(" total ascii strings",len(ss))
def show(label,pred,limit=60):
    hits=[s for s in ss if pred(s)]
    print("  -- %s (%d)"%(label,len(hits)))
    for s in hits[:limit]:
        print("     %r"%s)

show("GSP1101", lambda s: 'GSP1101' in s or 'GSP 1101' in s)
show("RP500",   lambda s: 'RP500' in s or 'RP 500' in s)
show("IR/impulse/wav", lambda s: re.search(r'(?i)(impulse|\.wav|\.aif|ir file|irfile|user cab|usercab|user ir|convol)',s) is not None)
show("cab", lambda s: re.search(r'(?i)user ?cab',s) is not None)

# utf-16 strings
u16=[]
for m in re.finditer((b'(?:[ -~]\x00){4,}'), x):
    try: u16.append(m.group(0).decode('utf-16le'))
    except: pass
print()
print(" utf16 strings",len(u16))
for pat in ("GSP1101","RP500","Impulse",".wav","User Cab","IR File"):
    hits=[s for s in u16 if pat.lower() in s.lower()]
    if hits: print("  %-10s %s"%(pat,hits[:10]))

print()
print("="*70)
print("GSPUpdaterV20.exe : UI / version strings (.rdata + .rsrc)")
v=open(SH+r"\GSPUpdaterV20.exe",'rb').read()
vs=[s for _,s in strings(v,4)]
print(" total strings",len(vs))
for pat in ("2.0","Version","version","Firmware","firmware","IR","Impulse","User Cab","USER","C63"):
    hits=[s for s in vs if pat in s]
    if hits:
        print("  -- %s (%d)"%(pat,len(hits)))
        for s in hits[:25]: print("     %r"%s)

print()
print("="*70)
print("firmware version tables: look for compact version constants")
v20=open(SH+r"\v20_res_51E18.bin",'rb').read()
fw63=open(SH+r"\gsp1101_fw.bin",'rb').read()
exe=open(SH+r"\JUpdater Gsp1101vC63.exe",'rb').read()
hits=[];i=0
pat=bytes.fromhex("ea806802307a5391")
while True:
    j=exe.find(pat,i)
    if j<0: break
    hits.append(j); i=j+1
B63=hits[0]
b63=b''.join(exe[B63+k*ST if False else B63+k*0x10008+8:B63+(k+1)*0x10008] for k in range(16))
b20=b''.join(v20[k*0x10000+8:(k+1)*0x10000] for k in range(16))

for nm,img in (("V20",b20),("vC63",b63)):
    print("--",nm)
    for off,s in strings(img,4):
        if s.strip() in ('VERSION','2.0','1.0','C63','v2.0','V2.0') or 'Firmware' in s or 'FIRMWARE' in s:
            print("   b%d:%04X  %r"%(off>>16,off&0xFFFF,s))

    # dump around 'VERSION %D.%D'
    k=img.find(b'VERSION %D.%D')
    if k>=0:
        print("   --- around VERSION fmt b%d:%04X ---"%(k>>16,k&0xFFFF))
        s=max(0,k-64)
        for a in range(s,k+96,16):
            c=img[a:a+16]
            print("     %04X  %-47s %s"%(a&0xFFFF,c.hex(' '),''.join(chr(q) if 32<=q<127 else '.' for q in c)))
