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
import mcs51

RP=open(_P("rp_fw.bin"),'rb').read()
BANKS=[RP[k*0x10000:(k+1)*0x10000] for k in range(16)]

def dump(bank,a,b,label):
    d=BANKS[bank]
    print("===== %s bank%d:0x%04X-0x%04X ====="%(label,bank,a,b))
    for addr,raw,text in mcs51.disasm(d,0,a,b):
        print("  %04X: %-9s %s"%(addr,raw,text))
    print()

dump(14,0xA120,0xA1D0,"helper A132")
dump(3,0x7C20,0x7CD0,"caller b3:7C68")
dump(3,0x85C0,0x8680,"caller b3:8610")

print("=== all LCALL/AJMP targets within b14 0x9900-0x9A20 ===")
for tgt in range(0x9900,0x9A20):
    for op in (0x12,0x02,0x01,0x11,0x21,0x31,0x41,0x51,0x61,0x71,0x81,0x91,0xA1,0xB1,0xC1,0xD1,0xE1,0xF1):
        if op in (0x12,0x02):
            pat=bytes([op,(tgt>>8)&0xFF,tgt&0xFF])
        else:
            # AJMP/ACALL encode high 3 bits of target in opcode
            continue
        i=0; hits=[]
        while True:
            j=RP.find(pat,i)
            if j<0: break
            hits.append(j); i=j+1
        if hits and op==0x12:
            print("  LCALL %04X n=%d %s"%(tgt,len(hits),[('b%d:%04X'%(h>>16,h&0xFFFF)) for h in hits[:6]]))

print()
print("=== does b14 blob contain cab/model names? ===")
blob=BANKS[14][0x2DC2:0xADC2]
for nd in (b'CHAMP',b'DIGISPKR',b'CAB',b'DIRECT',b'DREAD',b'BRIT',b'TWIN',b'AMP'):
    print("  %-9s in blob: %s"%(nd.decode(), blob.find(nd)))

print()
print("=== first 512 bytes of blob as 16-bit BE and LE words (structure check) ===")
for a in range(0,256,16):
    c=blob[a:a+16]
    be=' '.join('%04X'%((c[i]<<8)|c[i+1]) for i in range(0,16,2))
    print("  +%04X  %-47s  BE: %s"%(a,c.hex(' '),be))
