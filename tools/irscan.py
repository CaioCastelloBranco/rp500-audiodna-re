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
D = {
    'V20': open(_P("v20_res_51E18.bin"),'rb').read(),
    'C48': payload16(open(_P("c48_fw.bin"),'rb').read()),
    'C63': payload16(open(_P("c63_fw.bin"),'rb').read()),
    'RP':  open(_P("rp500_fw.bin"),'rb').read(),
}

import struct
def ints_be(blk):
    return struct.unpack('>128i', blk)

def ir_like(blk):
    v = ints_be(blk)
    nz = sum(1 for x in v if x != 0)
    if nz < 100: return False
    small = sum(1 for x in v if abs(x) < (1 << 20))
    if small < 100: return False
    # energy should be front-loaded (decay)
    e = [x*x for x in v]
    front = sum(e[:16]); back = sum(e[-16:])
    return front > back * 3

for name, d in D.items():
    hits = []
    for i in range(0, len(d) - 512, 16):
        blk = d[i:i+512]
        if ir_like(blk):
            hits.append(i)
    # group
    groups = []
    for h in hits:
        if groups and h - groups[-1][1] <= 1024:
            groups[-1][1] = h
        else:
            groups.append([h, h])
    print('='*60, name, 'candidate IR-like 512B windows:', len(hits))
    for a, b in groups[:20]:
        print(f'  {a:06X}-{b+512:06X} bank {a//0x10000} ({b-a+512} bytes)')
