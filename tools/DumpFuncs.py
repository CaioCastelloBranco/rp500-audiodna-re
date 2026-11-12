# --- portable path resolution (added 2026-11-10) ---------------------------
import os as _os

_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_SW = _os.path.dirname(_os.path.abspath(__file__))


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


# Dump functions and their sizes for raw program
from ghidra.program.model.symbol import SourceType

with open(_P("rp500_funcs.txt"), "w") as f:
    fm = currentProgram.getFunctionManager()
    count = 0
    for func in fm.getFunctions(True):
        entry = func.getEntryPoint()
        size = func.getBody().getNumAddresses()
        name = func.getName()
        f.write("%s %s %d %s\n" % (entry, name, int(size), func.getSignature() if hasattr(func,'getSignature') else ""))
        count += 1
    f.write("TOTAL %d\n" % count)
