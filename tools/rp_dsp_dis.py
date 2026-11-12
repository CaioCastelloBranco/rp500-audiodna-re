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


from capstone import *
from capstone.mcs51 import *
import capstone

RP=open(_P("rp_fw.bin"),'rb').read()
BANKS=[RP[k*0x10000:(k+1)*0x10000] for k in range(16)]

md=Cs(CS_ARCH_MCS51, CS_MODE_MCS51)
md.detail=False

def find_all(pat):
    out=[]; idx=0
    while True:
        i=RP.find(pat,idx)
        if i<0: break
        out.append(i); idx=i+1
    return out

def dis_at(bank, off, n=80, before=0):
    data=BANKS[bank]
    a=max(0,off-before)
    code=data[a:off+n]
    print("--- disasm bank%d:0x%04X (start 0x%04X) ---"%(bank,off,a))
    for ins in md.disasm(code, a):
        mark=" <<<" if ins.address==off else ""
        print("0x%04X  %-10s %s%s"%(ins.address, ins.mnemonic, ins.op_str, mark))

print("=== MOV DPTR,#0xD070 / #0xE000 / #0xFF24 / #0xFF25 refs ===")
for addr in (0xD070,0xE000,0xFF24,0xFF25,0xD000,0xE100):
    pat=bytes([0x90,(addr>>8)&0xFF,addr&0xFF])
    hits=find_all(pat)
    print("DPTR=#%04X n=%d %s"%(addr,len(hits),[('b%d:%04X'%(h>>16,h&0xFFFF)) for h in hits[:20]]))

print()
print("=== disasm around each DPTR=#0xD070 ===")
for h in find_all(bytes([0x90,0xD0,0x70]))[:8]:
    dis_at(h>>16, h&0xFFFF, 60, 12)

print()
print("=== disasm around each DPTR=#0xE000 ===")
for h in find_all(bytes([0x90,0xE0,0x00]))[:8]:
    dis_at(h>>16, h&0xFFFF, 60, 12)

print()
print("=== disasm around each DPTR=#0xFF24 ===")
for h in find_all(bytes([0x90,0xFF,0x24]))[:6]:
    dis_at(h>>16, h&0xFFFF, 60, 12)
