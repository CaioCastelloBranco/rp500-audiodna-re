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

imgs = {
    'RP500': open(_P("rp500_fw.bin"),'rb').read(),
    'V20': open(_P("v20_res_51E18.bin"),'rb').read(),
    'C48': payload16(open(_P("c48_fw.bin"),'rb').read()),
    'C63': payload16(open(_P("c63_fw.bin"),'rb').read()),
}

for name, img in imgs.items():
    print('='*70, name)
    for m in re.finditer(rb'CHAMP[^\x00]{0,10}', img):
        print(' ', hex(m.start()), m.group())
    for m in re.finditer(rb'[A-Z0-9][A-Z0-9 1-9Xx\-]{5,15}', img):
        s = m.group()
        if s in (b'TWIN 12', b'GREENBACK', b'VINTAGE 30', b'BRITISH', b'TWEED'):
            print(' ', hex(m.start()), s)
