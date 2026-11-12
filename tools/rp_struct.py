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
import struct, collections, math, re

rp = open(_P("rp500_fw.bin"),'rb').read()
n = len(rp)

def ent(d):
    c=collections.Counter(d); n=len(d)
    return -sum((v/n)*math.log2(v/n) for v in c.values()) if n else 0

print("=== entropy of deinterleaved streams ===")
for k in (1,2,4,8):
    parts = [rp[i::k] for i in range(k)]
    print("k=%d entropies: %s" % (k, [round(ent(p),2) for p in parts]))

print("=== 16-bit halfword stats (LE) ===")
hw = [struct.unpack_from('<H', rp, i)[0] for i in range(0, n-1, 2)]
c = collections.Counter(hw)
print("top halfwords:", [(hex(v), cnt) for v,cnt in c.most_common(20)])
# Thumb push {lr}: 0xB5xx (bits 15..8 = 0xB5)
thumb_push = sum(1 for v in hw if (v & 0xFF00) == 0xB500)
thumb_bx = sum(1 for v in hw if v == 0x4770)
thumb_bl = sum(1 for v in hw if (v & 0xF800) == 0xF000)
thumb_b  = sum(1 for v in hw if (v & 0xF800) == 0xE000)
print("thumb push B5xx=%d bx lr=%d bl=%d b=%d" % (thumb_push, thumb_bx, thumb_bl, thumb_b))

print("=== 32-bit word top ===")
w32 = [struct.unpack_from('<I', rp, i)[0] for i in range(0, n-3, 4)]
c32 = collections.Counter(w32)
print([(hex(v), cnt) for v,cnt in c32.most_common(20)])

print("=== ASCII strings in tail 0xE0000-0x100000 ===")
seg = rp[0xE0000:]
for m in re.finditer(rb'[\x20-\x7E]{4,}', seg):
    print("0x%06X %s" % (0xE0000+m.start(), m.group().decode()[:120]))

print("=== copyright / version patterns ===")
for m in re.finditer(rb'(?i)(copyright|\(c\)|version|v\d+\.\d+|20\d\d)', rp):
    s = rp[max(0,m.start()-20):m.start()+80]
    print("0x%06X %r" % (m.start(), s))

print("=== head 0x0-0x200 with byte classes ===")
for i in range(0, 0x200, 16):
    c = rp[i:i+16]
    print("0x%06X  %-47s  %s" % (i, c.hex(' '), ''.join(chr(b) if 32<=b<127 else '.' for b in c)))
