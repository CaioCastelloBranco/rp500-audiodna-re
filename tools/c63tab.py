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
import struct

def payload16(img):
    return b''.join(img[k*0x10008+8:k*0x10008+0x10008] for k in range(16))

D = {
    'C48': payload16(open(_P("c48_fw.bin"),'rb').read()),
    'C63': payload16(open(_P("c63_fw.bin"),'rb').read()),
    'RP':  open(_P("rp500_fw.bin"),'rb').read(),
}

def nonblank(d):
    n = 0
    for i in range(0, len(d), 4096):
        blk = d[i:i+4096]
        if blk != b'\xff'*len(blk):
            n += len(blk)
    return n

for name, d in D.items():
    print(name, 'non-0xFF bytes ~', hex(nonblank(d)))

print()
print('='*80)
print('Region around C63 cab names (bank11 D800-E000) - look for structured tables')
d = D['C63'][11*0x10000:12*0x10000]
for a in range(0xD800, 0xE000, 16):
    row = d[a:a+16]
    if row == b'\xff'*16:
        continue
    txt = ''.join(chr(b) if 32 <= b < 127 else '.' for b in row)
    print(f'{a:04X}: {row.hex(" "):<48} {txt}')
