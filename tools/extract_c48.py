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
import re, hashlib

# extract C48 firmware
d = open(_P("JUpdater GSP1101vC48.exe"), 'rb').read()
base = 0xBF5F0
fw = d[base:base+16*0x10008]
open(_OUT("c48_fw.bin"), 'wb').write(fw)
print('wrote c48_fw.bin', len(fw), hashlib.sha1(fw).hexdigest())

v20 = open(_P("v20_res_51E18.bin"), 'rb').read()
c63 = open(_P("gsp1101_fw.bin"), 'rb').read()

def payload16(img):
    out = bytearray()
    for k in range(16):
        out += img[k*0x10008+8:k*0x10008+0x10008]
    return bytes(out)

p48 = payload16(fw)
p63 = payload16(c63)
p20 = v20  # flat 16x0x10000, headers inside each bank

def ident(a, b):
    n = min(len(a), len(b))
    return sum(x == y for x, y in zip(a[:n], b[:n])) / n

print('C48 payload len', len(p48))
# compare per bank (C48/C63 payloads are flat 64K each after header strip)
for name, A in (('V20 flat', p20), ('C48 flat', p48)):
    for name2, B in (('C48 flat', p48), ('C63 flat', p63)):
        if name == name2:
            continue
        print(f'{name} vs {name2}: overall {ident(A,B):.3f}')
        per = [ident(A[k*0x10000:(k+1)*0x10000], B[k*0x10000:(k+1)*0x10000]) for k in range(16)]
        print('   per bank', ' '.join(f'{x:.2f}' for x in per))

# shared 32-byte windows
def win32(a, b, n=32):
    ha = {}
    for i in range(0, len(a)-n+1, n):
        ha.setdefault(a[i:i+n], 0)
        ha[a[i:i+n]] += 1
    tot = sum(ha.values())
    hit = 0
    for i in range(0, len(b)-n+1, n):
        w = b[i:i+n]
        if w in ha:
            hit += 1
    return hit / (len(b)//n)
print('32B window share C48<->C63', round(win32(p48,p63),3))
print('32B window share V20<->C48', round(win32(p20,p48),3))
print('32B window share V20<->C63', round(win32(p20,p63),3))
