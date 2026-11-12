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
v20 = open(_P("v20_res_51E18.bin"),'rb').read()

def strs(d):
    return [(m.start(), m.group().decode('latin1')) for m in re.finditer(rb'[\x20-\x7e]{3,}', d)]

for name, img in (('C48', c48), ('C63', c63), ('V20', v20)):
    print('='*60, name)
    for pat in (b'CHAMP1X8', b'USER', b'CAB', b'CABINET'):
        offs = [m.start() for m in re.finditer(re.escape(pat), img)]
        print(pat, len(offs), [hex(o) for o in offs[:12]])

# dump strings around CHAMP1X8 in each
for name, img in (('C48', c48), ('C63', c63), ('V20', v20)):
    i = img.find(b'CHAMP1X8')
    print('='*60, name, 'CHAMP1X8 at', hex(i))
    if i >= 0:
        lo = max(0, i-0x200); hi = i+0x400
        seq = [(m.start()+lo, m.group().decode('latin1')) for m in re.finditer(rb'[\x20-\x7e]{3,}', img[lo:hi])]
        for o,s in seq:
            print(hex(o), repr(s))
