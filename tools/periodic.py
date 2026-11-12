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
def payload16(img):
    return b''.join(img[k*0x10008+8:k*0x10008+0x10008] for k in range(16))
V20 = open(_P("v20_res_51E18.bin"),'rb').read()
C48 = payload16(open(_P("c48_fw.bin"),'rb').read())

print('V20 0xD400:', V20[0xD400:0xD440].hex(' '))
print('C48 0xEEAC0:', C48[0xEEAC0:0xEEB00].hex(' '))
print()
# check periodicity
for name, d, o in (('V20', V20, 0xD400), ('C48', C48, 0xEEAC0)):
    p = 0x1536
    ok = all(d[o+i] == d[o+i+p] for i in range(0x1536*3))
    print(name, 'period 0x1536 over 3 periods:', ok)
print()
# how far does the period-0x1536 pattern extend in V20?
d = V20
o = 0xD400
p = 0x1536
n = o
while n + p < len(d) and d[n:n+16] == d[n+p:n+p+16]:
    n += 16
print('periodic from 0xD400 up to', hex(n))
print('region start check: 0xD400-0x100', V20[0xD300:0xD320].hex(' '))
print('first 16 of period:', V20[0xD400:0xD410].hex(' '))
print('second copy:', V20[0xD400+p:0xD400+p+16].hex(' '))
