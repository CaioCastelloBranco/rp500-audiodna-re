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
import collections, math, struct

rp = open(_P("rp500_fw.bin"),'rb').read()

def ent(d):
    c=collections.Counter(d); n=len(d)
    return -sum((v/n)*math.log2(v/n) for v in c.values()) if n else 0

print("=== periodicity: entropy of XOR with shifted copy ===")
for k in [1,2,4,8,16,32,64,128,256,512,1024,2048,4096,8192,16384,32768,65536]:
    a = rp[:len(rp)-k]
    b = rp[k:]
    x = bytes(p^q for p,q in zip(a,b))
    print("shift %6d  xor-ent=%.3f  equal-frac=%.4f" % (k, ent(x), sum(p==q for p,q in zip(a,b))/len(a)))

print("=== repeated 16-byte block count (first 256KB) ===")
for block in [16,32,64]:
    seen = collections.Counter()
    for i in range(0, 0x40000-block, block):
        seen[rp[i:i+block]] += 1
    dups = sum(v-1 for v in seen.values() if v>1)
    print("block", block, "duplicate blocks:", dups, "of", len(seen))

print("=== byte histogram 0x30000-0x44000 ===")
seg = rp[0x30000:0x44000]
c = collections.Counter(seg)
print("ent", round(ent(seg),3), "top:", [(hex(b),n) for b,n in c.most_common(20)])

print("=== halfword stats 0x30000-0x44000 (LE) ===")
hw = [struct.unpack_from('<H', seg, i)[0] for i in range(0, len(seg)-1, 2)]
cc = collections.Counter(hw)
print("top:", [(hex(v),n) for v,n in cc.most_common(20)])

print("=== 4-byte words top 0x30000-0x44000 ===")
w4 = [struct.unpack_from('<I', seg, i)[0] for i in range(0, len(seg)-3, 4)]
c4 = collections.Counter(w4)
print("top:", [(hex(v),n) for v,n in c4.most_common(20)])

print("=== check 0x30000 block periodicity with 0x10000 ===")
a = rp[0x30000:0x40000]
b = rp[0x40000:0x50000]
print("ent a", round(ent(a),3), "ent b", round(ent(b),3))
x = bytes(p^q for p,q in zip(a,b))
print("xor ent", round(ent(x),3), "equal", sum(p==q for p,q in zip(a,b))/len(a))
print("a[:64]", a[:64].hex(' '))
print("b[:64]", b[:64].hex(' '))
