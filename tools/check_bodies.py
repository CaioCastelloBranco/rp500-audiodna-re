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

raw48 = open(_P("c48_fw.bin"),'rb').read()
bodies = [raw48[k*0x10008:(k+1)*0x10008] for k in range(16)]
print('bodies len', [len(b) for b in bodies])
print('hashes:')
for k, b in enumerate(bodies):
    print(k, hashlib.sha1(b).hexdigest()[:16], b[:8].hex(' '))

print()
print('bytes at 0x2f52 in each body:')
for k, b in enumerate(bodies):
    print(k, b[0x2f50:0x2f60].hex(' '))
print()
print('distinct body contents count:', len(set(bodies)))
