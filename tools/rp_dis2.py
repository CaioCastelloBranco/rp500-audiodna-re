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

def find_all(pat):
    out=[]; idx=0
    while True:
        i=RP.find(pat,idx)
        if i<0: break
        out.append(i); idx=i+1
    return out

def show(bank, off, n=80, before=16):
    data=BANKS[bank]
    a=max(0,off-before)
    print("--- bank%d @0x%04X (context 0x%04X) ---"%(bank,off&0xFFFF,a))
    for addr,raw,text in mcs51.disasm(data,a,off&0xFFFF+n):
        mark=" <<<" if addr==(off&0xFFFF) else ""
        print("  %04X: %-9s %s%s"%(addr,raw,text,mark))

print("=== occurrences of key 3-byte immediates ===")
for addr in (0xD070,0xE000,0xFF24,0xFF25,0xD000,0xE100,0x4000,0x4336,0x4355):
    pat=bytes([0x90,(addr>>8)&0xFF,addr&0xFF])
    hits=find_all(pat)
    print("MOV DPTR,#%04X  n=%d  %s"%(addr,len(hits),[('b%d:%04X'%(h>>16,h&0xFFFF)) for h in hits[:25]]))

print()
print("=== boot / bank trampoline bank0 0x0000-0x0120 ===")
show(0,0x0000,0x120,0)
