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

c48raw = open(_P("c48_fw.bin"), 'rb').read()
g = open(_P("gsp1101_fw.bin"), 'rb').read()
c63raw = g[0x19F8:0x19F8+16*0x10008]
open(_OUT("c63_fw.bin"), 'wb').write(c63raw)
v20 = open(_P("v20_res_51E18.bin"), 'rb').read()
p48 = b''.join(c48raw[k*0x10008+8:k*0x10008+0x10008] for k in range(16))
p63 = b''.join(c63raw[k*0x10008+8:k*0x10008+0x10008] for k in range(16))

def ident(a, b):
    return sum(x == y for x, y in zip(a, b)) / len(a)

def win32(a, b, n=32):
    ha = set(a[i:i+n] for i in range(0, len(a)-n+1, n))
    return sum(1 for i in range(0, len(b)-n+1, n) if b[i:i+n] in ha) / (len(b)//n)

for na, A, nb, B in [('V20', v20, 'C48', p48), ('V20', v20, 'C63', p63), ('C48', p48, 'C63', p63)]:
    print(f'{na} vs {nb}: bytes {ident(A,B):.3f} | 32B windows {win32(A,B):.3f}')
    per = [ident(A[k*0x10000:(k+1)*0x10000], B[k*0x10000:(k+1)*0x10000]) for k in range(16)]
    print('   per bank', ' '.join(f'{x:.2f}' for x in per))

print()
for s in [b'USER 1', b'USER 2', b'USER 10', b'USER_CAB', b'CAB_EN_XLR_LPF', b'GLOBAL CABINET', b'CABINET']:
    print(s, 'V20', v20.count(s), 'C48', p48.count(s), 'C63', p63.count(s))
