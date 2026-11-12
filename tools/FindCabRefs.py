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


# Find xrefs to string addresses; print containing functions
import sys

targets = {}
for line in open(_P("rp500_straddrs.txt")):
    line = line.strip()
    if not line: continue
    addr, s = line.split("|", 1)
    targets[int(addr, 16)] = s

fm = currentProgram.getFunctionManager()
with open(_P("rp500_cabrefs.txt"), "w") as f:
    # map each target address to one function
    for addr, s in sorted(targets.items()):
        addr_obj = currentProgram.getAddressFactory().getDefaultAddressSpace().getAddress(addr)
        funcs = fm.getFunctionsContaining(addr_obj)
        names = []
        for fn in funcs:
            names.append("%s@%s" % (fn.getName(), fn.getEntryPoint()))
        f.write("%s | %s | %s\n" % (hex(addr), s, "; ".join(names) if names else "(no func)"))
