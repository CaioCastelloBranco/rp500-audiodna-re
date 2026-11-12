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
raw48 = open(_P("c48_fw.bin"),'rb').read()
bodies = [raw48[k*0x10008:(k+1)*0x10008] for k in range(16)]

b0 = bodies[0]
for k in range(1, 16):
    b = bodies[k]
    same = 0
    while same < len(b) and b[same] == b0[same]:
        same += 1
    # also find last differing from end
    tail = 0
    while tail < len(b) and b[len(b)-1-tail] == b0[len(b)-1-tail]:
        tail += 1
    print(f'bank{k}: first diff 0x{same:04x}  identical prefix {same/0x10008:.1%}  identical suffix 0x{tail:04x}')

# block-level identity: compare 256-byte blocks
print()
print('per-256B-block identity of bank0 vs each bank (only blocks < 0x8000):')
for k in range(1,16):
    b = bodies[k]
    hits = sum(1 for o in range(0, 0x8000, 256) if b[o:o+256] == b0[o:o+256])
    print(k, f'{hits}/128')
