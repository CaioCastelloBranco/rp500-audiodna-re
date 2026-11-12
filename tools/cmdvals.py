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
import re
from collections import Counter

def payload16(img):
    return b''.join(img[k*0x10008+8:k*0x10008+0x10008] for k in range(16))

D = {
    'V20': open(_P("v20_res_51E18.bin"),'rb').read(),
    'C48': payload16(open(_P("c48_fw.bin"),'rb').read()),
    'C63': payload16(open(_P("c63_fw.bin"),'rb').read()),
    'RP':  open(_P("rp500_fw.bin"),'rb').read(),
}

REGS = (0xE200, 0xE400, 0xE600, 0xE800, 0xD066, 0xD06D, 0xD06E, 0xFDFC)

for name, d in D.items():
    print('='*78)
    print(name)
    for reg in REGS:
        pat = bytes([0x90, reg >> 8, reg & 0xFF])
        vals = Counter()
        sites = []
        for m in re.finditer(re.escape(pat), d):
            a = m.start()
            win = d[a + 3:a + 14]
            imm = None
            # look for MOV A,#imm (74 xx) or MOV dir,#imm (75 xx yy)
            for i in range(len(win) - 1):
                if win[i] == 0x74:
                    imm = win[i+1]
                    break
            vals[imm] += 1
            sites.append((a // 0x10000, a % 0x10000, imm))
        if sites:
            print(f'  {reg:04X}: n={len(sites)} values={dict(sorted(vals.items(), key=lambda kv: (kv[0] is None, kv[0])))}')
            print('        sites:', ', '.join(f'b{b}:{o:04X}' for b, o, _ in sites))
