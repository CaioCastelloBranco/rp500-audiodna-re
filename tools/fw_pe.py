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
import struct

up = open(_P("JUpdater Gsp1101vC63.exe"),'rb').read()
fw = open(_P("gsp1101_fw.bin"),'rb').read()

# Parse PE sections
e_lfanew = struct.unpack_from('<I', up, 0x3C)[0]
num_sec = struct.unpack_from('<H', up, e_lfanew+6)[0]
opt_size = struct.unpack_from('<H', up, e_lfanew+20)[0]
sec_off = e_lfanew + 24 + opt_size
print("sections:")
for i in range(num_sec):
    name = up[sec_off+i*40:sec_off+i*40+8].rstrip(b'\x00').decode('ascii','replace')
    vsize, vaddr, rawsize, rawoff = struct.unpack_from('<IIII', up, sec_off+i*40+8)
    print(f"  {name:8s} VA=0x{vaddr:08X} VSize=0x{vsize:X} raw=0x{rawoff:X} rawsize=0x{rawsize:X}")

# compare fw with each section's raw data
secs = [".text", ".rdata", ".data", ".rsrc"]
for i in range(num_sec):
    vsize, vaddr, rawsize, rawoff = struct.unpack_from('<IIII', up, sec_off+i*40+8)
    raw = up[rawoff:rawoff+rawsize]
    common_prefix = 0
    for a, b in zip(fw, raw):
        if a == b: common_prefix += 1
        else: break
    print(f"{secs[i] if i < 4 else i}: rawsize={hex(rawsize)} prefix_match_with_fw={hex(common_prefix)}")

# entropy of fw in 64KB chunks to find firmware blob
from collections import Counter
import math
def ent(d):
    if not d: return 0.0
    c = Counter(d); n = len(d)
    return -sum((v/n)*math.log2(v/n) for v in c.values())
print("=== fw entropy per 64KB ===")
for off in range(0, len(fw), 0x10000):
    print("0x%06X ent=%.2f" % (off, ent(fw[off:off+0x10000])))

# check vectors area
for probe in [0xA7680, 0xCD1A8]:
    print("hexdump 0x%X:" % probe, fw[probe:probe+64].hex(' '))
