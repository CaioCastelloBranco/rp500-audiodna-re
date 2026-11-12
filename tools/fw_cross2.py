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
fw = open(_P("gsp1101_fw.bin"),'rb').read()
up = open(_P("JUpdater Gsp1101vC63.exe"),'rb').read()
rp = open(_P("rp500_fw.bin"),'rb').read()

print("sizes:", len(fw), len(up), len(rp))

# probe several 64-byte chunks of fw in updater
for off in [0, 0x1000, 0x10000, 0x40000, 0x54000, 0x90000, 0xF0000, 0x100000]:
    chunk = fw[off:off+64]
    print("fw 0x%X in updater at:" % off, hex(up.find(chunk)))

for off in [0, 0x10000, 0x40000, 0x80000]:
    chunk = fw[off:off+64]
    print("fw 0x%X in rp500 at:" % off, hex(rp.find(chunk)))

for off in [0, 0x10000, 0x40000, 0x80000]:
    chunk = rp[off:off+64]
    print("rp500 0x%X in fw at:" % off, hex(fw.find(chunk)))
