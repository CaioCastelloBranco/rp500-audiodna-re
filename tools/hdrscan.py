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

def payload16(img):
    return b''.join(img[k*0x10008+8:k*0x10008+0x10008] for k in range(16))

c48 = payload16(open(_P("c48_fw.bin"),'rb').read())
c63 = payload16(open(_P("c63_fw.bin"),'rb').read())

for name, img in (('C48', c48), ('C63', c63)):
    print('='*60, name)
    for pat, label in [(b'\x00\x5c\x00\x05', '00 5C 00 05'),
                       (b'\x00\x05\x00\x5c', '00 05 00 5C'),
                       (b'\x05\x00\x5c\x00', '05 00 5C 00'),
                       (b'\x5c\x00\x05\x00', '5C 00 05 00')]:
        offs = [m.start() for m in re.finditer(re.escape(pat), img)]
        print(label, len(offs), [hex(o) for o in offs[:12]])
    for val in (0x0800, 0x07E7, 0x07FE, 0x0080, 0x00D0):
        pat = bytes([0x90, val >> 8, val & 0xFF])
        offs = [i for i in range(len(img)-2) if img[i:i+3] == pat]
        banks = {}
        for o in offs:
            banks.setdefault(o // 0x10000, []).append(o % 0x10000)
        print(f'MOV DPTR,#{val:04X}', len(offs), {k: [hex(x) for x in v[:8]] for k, v in banks.items()})
