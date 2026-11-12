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
S = _FW
v20raw = open(S+r'\v20_res_51E18.bin','rb').read()
v20 = [v20raw[k*0x10000:(k+1)*0x10000] for k in range(16)]
def bodies(img):
    return [img[k*0x10000 + k*8 : (k+1)*0x10000 + k*8] for k in range(16)]
c63 = bodies(open(S+r'\c63_fw.bin','rb').read())
c48 = bodies(open(S+r'\c48_fw.bin','rb').read())

def names(b, start, maxn=40):
    out=[]; p=start
    for _ in range(maxn):
        e = b.find(b'\x00', p)
        if e < 0: break
        s = b[p:e]
        if not s: break
        out.append(s.decode('ascii','replace'))
        p = e+1
    return out

print('V20 bank10 from 0x5844:', names(v20[10], 0x5844))
print()
print('C63 bank11 from 0xD8F6:', names(c63[11], 0xD8F6))
print()
print('C48 bank10 from 0x7620:', names(c48[10], 0x7620))
print()
print('V20 specials:', names(v20[10], 0x5820, 5))
print('C63 specials:', names(c63[11], 0xD8D2, 5))
print('C48 specials:', names(c48[10], 0x7606, 5))
print()
print('V20 USER present?', b'USER' in v20raw)
print('V20 USER_CAB %D:', [hex(m.start()) for m in re.finditer(re.escape(b'USER_CAB %D'), v20raw)])
