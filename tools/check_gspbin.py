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
p = _P("gsp1101_fw.bin")
d = open(p, 'rb').read()
e = open(_P("JUpdater Gsp1101vC63.exe"), 'rb').read()
print('gsp1101_fw.bin len', len(d), hex(len(d)), 'sha1', hashlib.sha1(d).hexdigest())
print('first 32', d[:32].hex(' '))
offs = [m.start() for m in re.finditer(re.escape(b'\xea\x80\x68\x02\x30\x7a'), d)]
print('header occurrences', len(offs), [hex(o) for o in offs[:20]])
# compare to exe slice
ex = e[0xC0FF8:0xC0FF8+len(d)]
print('exe slice equal?', ex == d)
# does file contain the 16-bank image at some offset?
for base in range(0, min(len(d), 0x4000)):
    if base + 16*0x10008 <= len(d):
        hdr = d[base:base+8]
        if hdr[:4] == b'\xea\x80\x68\x02' and all(d[base+k*0x10008:base+k*0x10008+8] == hdr for k in range(1,16)):
            print('full 16-bank image at', hex(base), 'to', hex(base+16*0x10008))
# tail
print('last 32', d[-32:].hex(' '))
