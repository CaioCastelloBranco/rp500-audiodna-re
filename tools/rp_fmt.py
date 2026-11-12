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
import struct, collections, math

rp = open(_P("rp500_fw.bin"),'rb').read()
print("len", hex(len(rp)))

freq = collections.Counter(rp)
print("top bytes:", [(hex(b), c, round(c/len(rp)*100,2)) for b,c in freq.most_common(16)])

def ent(d):
    c=collections.Counter(d); n=len(d)
    return -sum((v/n)*math.log2(v/n) for v in c.values()) if n else 0

# zero/ff density per 64KB
print("=== per 64KB: entropy, 00%, FF%, most common ===")
for off in range(0, len(rp), 0x10000):
    w = rp[off:off+0x10000]
    cc = collections.Counter(w).most_common(3)
    print("0x%06X ent=%.2f 00=%d%% FF=%d%% top=%s" % (
        off, ent(w), w.count(0)/len(w)*100, w.count(0xff)/len(w)*100,
        [(hex(b),n) for b,n in cc]))

# Try transforms and count ARM-like prologue / BL / B
def score(d, tag):
    # ARM push {...,lr}: E92Dxxxx has bytes xx xx 2D E9 little endian -> word & 0xFFFF0000 == 0xE92D0000
    # also E1A0C00D (mov r12,sp) pattern
    n = len(d)
    push = 0; bl = 0; b = 0; bx = 0; ldr_pc = 0
    for i in range(0, n-3, 4):
        w = struct.unpack_from('<I', d, i)[0]
        if (w & 0xFFFF0000) == 0xE92D0000: push += 1
        if (w & 0xFF000000) == 0xEB000000: bl += 1
        if (w & 0xFF000000) == 0xEA000000: b += 1
        if w == 0xE12FFF1E: bx += 1
        if (w & 0xFFFFF000) == 0xE59FF000: ldr_pc += 1
    print("%-24s push=%d BL=%d B=%d BXLR=%d LDRpc=%d" % (tag, push, bl, b, bx, ldr_pc))

score(rp, "raw LE32")

# transform: swap 16-bit halves of each 32-bit word
sw = bytearray(rp)
for i in range(0, len(sw)-3, 4):
    sw[i], sw[i+1], sw[i+2], sw[i+3] = sw[i+2], sw[i+3], sw[i], sw[i+1]
score(bytes(sw), "half-swapped")

# transform: reverse 4 bytes
rev = bytearray(rp)
for i in range(0, len(rev)-3, 4):
    rev[i], rev[i+1], rev[i+2], rev[i+3] = rev[i+3], rev[i+2], rev[i+1], rev[i]
score(bytes(rev), "byte-reversed")

# transform: deinterleave 2 (even bytes then odd bytes)
ev = rp[0::2]; od = rp[1::2]
score(ev, "even bytes")
score(od, "odd bytes")
score(ev+od, "deinterleave2")

# transform: swap adjacent bytes
swb = bytearray(len(rp))
swb[0::2] = rp[1::2]; swb[1::2] = rp[0::2]
score(bytes(swb), "byte-swapped16")

# transform: deinterleave 4
q0 = rp[0::4]; q1 = rp[1::4]; q2 = rp[2::4]; q3 = rp[3::4]
for tag, d in [("q0",q0),("q1",q1),("q2",q2),("q3",q3),("q0123",q0+q1+q2+q3)]:
    score(d, tag)

# Check known patterns anywhere (unaligned too)
for pat, name in [(b'\x2d\xe9', 'push-half'), (b'\x1e\xff\x2f\xe1','bx lr'), (b'\x00\x00\x2d\xe9','push')]:
    idx = rp.find(pat)
    print(name, "first at", hex(idx) if idx>=0 else None, "count", rp.count(pat))
