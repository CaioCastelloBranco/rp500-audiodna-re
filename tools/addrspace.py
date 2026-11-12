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

# Use only bank15 (top bank, usually the driver/master) and bank0 to reduce noise.
for name, d in D.items():
    print('='*78)
    print(name)
    for b in (0, 15):
        bank = d[b*0x10000:(b+1)*0x10000]
        hi = Counter()
        for m in re.finditer(rb'\x90(.)(.)', bank, re.S):
            addr = (m.group(1)[0] << 8) | m.group(2)[0]
            hi[addr >> 8] += 1
        print(f'  bank{b} MOV DPTR high-byte histogram (top 14):',
              [(f'{k:02X}xx', v) for k, v in hi.most_common(14)])
    # global special XRAM addresses
    print('  addr counts (whole image):')
    for addr in (0xE000, 0xEE00, 0xE200, 0xE400, 0xE600, 0xE800,
                 0xFDFC, 0xD01F, 0xD020, 0xD05A, 0xD05B, 0xD066,
                 0xD06D, 0xD06E, 0xD070, 0x1780, 0x1483, 0x1566):
        n = d.count(bytes([0x90, addr >> 8, addr & 0xFF]))
        if n:
            print(f'    {addr:04X}: {n}')
