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
v = open(_P("v20_res_51E18.bin"),'rb').read()
r = open(_P("rp500_fw.bin"),'rb').read()
for name, d in (('V20', v), ('RP500', r)):
    print('='*50, name)
    for k in (0, 1, 2, 14, 15):
        o = k*0x10000
        print(f'bank{k} start:', d[o:o+24].hex(' '))
print()
# search for the marker in V20
for pat in (b'\xea\x80\x68\x02\x30\x83\x53\x91', b'\xea\x80\x68\x02'):
    import re
    offs = [m.start() for m in re.finditer(re.escape(pat), v)]
    print(pat.hex(), len(offs), [hex(x) for x in offs[:20]])
