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

def regions_ff(data, minlen=4096):
    out = []
    i = 0; n = len(data)
    while i < n:
        if data[i] == 0xFF:
            j = i
            while j < n and data[j] == 0xFF: j += 1
            if j - i >= minlen: out.append((i, j - i))
            i = j
        else:
            i += 1
    return out

def entropy(data):
    import math
    from collections import Counter
    c = Counter(data); n = len(data)
    return -sum((v/n)*math.log2(v/n) for v in c.values())

for path in [_P("gsp1101_fw.bin"), _P("rp500_fw.bin")]:
    data = open(path,'rb').read()
    print("="*70)
    print(path, "size", hex(len(data)))
    print("MZ count:", data.count(b'MZ'), "PE\\0\\0 count:", data.count(b'PE\x00\x00'),
          "ELF count:", data.count(b'\x7fELF'), "URAR count:", data.count(b'UPX'))
    print("entropy:", round(entropy(data),3))
    ff = regions_ff(data)
    print("FF regions >=4KB:", [(f"0x{a:X}", hex(l)) for a,l in ff[:20]])
    print("total FF >=4KB bytes:", hex(sum(l for _,l in ff)))

# GSP IR-related full string dump region 0x54000-0x58000
data = open(_P("gsp1101_fw.bin"),'rb').read()
print("="*70)
print("GSP strings 0x54000-0x59000:")
for m in re.finditer(rb'[\x20-\x7E]{4,}', data[0x54000:0x59000]):
    print(f"0x{m.start()+0x54000:06X} {m.group().decode()[:100]}")
