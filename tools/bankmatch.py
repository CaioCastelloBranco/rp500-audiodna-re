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
import hashlib

c48 = open(_P("c48_fw.bin"), 'rb').read()
c63 = open(_P("gsp1101_fw.bin"), 'rb').read()

def payload16(img):
    return b''.join(img[k*0x10008+8:k*0x10008+0x10008] for k in range(16))

p48 = payload16(c48)
p63 = payload16(c63)

def ident(a, b):
    return sum(x == y for x, y in zip(a, b)) / len(a)

print('best match for each C48 bank among C63 banks')
for i in range(16):
    a = p48[i*0x10000:(i+1)*0x10000]
    scores = [(ident(a, p63[j*0x10000:(j+1)*0x10000]), j) for j in range(16)]
    scores.sort(reverse=True)
    print(f'C48 bank {i:2d} -> C63 bank {scores[0][1]:2d} ({scores[0][0]:.3f}), next {scores[1][1]} ({scores[1][0]:.3f})')

# string checks
for s in [b'USER 1', b'USER 10', b'USER_CAB', b'CAB_EN_XLR_LPF', b'Jcabinet', b'GLOBAL CABINET']:
    print(s, 'C48', c48.count(s), 'C63', c63.count(s))
