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
    data=BANKS[bank]
    print("===== %s  bank%d:0x%04X-0x%04X ====="%(label,bank,a,b))
    for addr,raw,text in mcs51.disasm(data,0,a,b):
        print("  %04X: %-9s %s"%(addr,raw,text))
    print()

dump(14,0x99F0,0x9B00,"DSP handshake / D070 writer (b14)")
dump(15,0xBDE0,0xBEF0,"DSP handshake / D070 writer (b15)")
dump(14,0x7500,0x75C0,"0xE000 writer area b14:754D")
dump(14,0x78A0,0x7920,"0xE000 writer area b14:78CE")
