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
_FW = _os.path.join(_ROOT, "01_source_firmware")


def _OUT(name):
    """Derived/output artifacts go to the script directory."""
    return _os.path.join(_SW, name)


import sys
sys.path.insert(0, _FW)

gsp=open(_P("gsp_fw.bin"),'rb').read()
rp =open(_P("rp_fw.bin"),'rb').read()

def find_all(img,pat):
    out=[];i=0
    while True:
        j=img.find(pat,i)
        if j<0: break
        out.append(j); i=j+1
    return out

def locs(hits):
    return [('b%d:%04X'%(h>>16,h&0xFFFF)) for h in hits]

print("=== host->DSP window usage: GSP vs RP ===")
for name,pat in [
    ("MOV DPTR,#D070", bytes([0x90,0xD0,0x70])),
    ("MOV DPTR,#D06E", bytes([0x90,0xD0,0x6E])),
    ("MOV DPTR,#E000", bytes([0x90,0xE0,0x00])),
    ("MOV DPTR,#FF24", bytes([0x90,0xFF,0x24])),
    ("MOV DPTR,#FF25", bytes([0x90,0xFF,0x25])),
]:
    g=find_all(gsp,pat); r=find_all(rp,pat)
    print("  %-16s GSP n=%3d %s"%(name,len(g),locs(g[:8])))
    print("  %-16s RP  n=%3d %s"%("",len(r),locs(r[:8])))

print()
print("=== loader idiom: ADD A,#imm ; MOV DPL,A ; MOV A,#hi ; ADDC A,R6 ; MOV DPH,A ; CLR A ; MOVC ===")
# pattern: 24 imm F5 82 74 hi 3E F5 83 E4 93
import re
for img,label in ((gsp,'GSP'),(rp,'RP')):
    print(" ",label)
    for m in re.finditer(rb'\x24(.)\xF5\x82\x74(.)\x3E\xF5\x83\xE4\x93', img, re.S):
        off=m.start()
        imm=m.group(1)[0]; hi=m.group(2)[0]
        base=(hi<<8)|imm
        print("    b%d:%04X  base=0x%04X"%(off>>16,off&0xFFFF, (base+0x100)&0xFFFF if imm>=0x80 else base))

print()
print("=== GSP: does it contain the RP500-style 32KB blob start bytes? ===")
for sig in [bytes.fromhex('c9121234121000'), bytes.fromhex('121234121000')]:
    print("  ",sig.hex(),"GSP",locs(find_all(gsp,sig)[:5]),"RP",locs(find_all(rp,sig)[:5]))

print()
print("=== GSP service strings around USER_CAB / SEND BLOCK (bank15) ===")
B15=gsp[15*0x10000:16*0x10000]
def strings(bank,a,b,minlen=3):
    out=[];i=a
    while i<b:
        if 32<=bank[i]<127:
            s=i
            while i<b and 32<=bank[i]<127: i+=1
            if i-s>=minlen: out.append((s,bank[s:i].decode('ascii')))
        else: i+=1
    return out
for off,s in strings(B15,0x3200,0x3700,3):
    print("  %04X  %s"%(off,s))
