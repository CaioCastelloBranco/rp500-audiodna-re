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
import collections, math

rp = open(_P("rp500_fw.bin"),'rb').read()
nb = len(rp)//0x10000
banks = [rp[i*0x10000:(i+1)*0x10000] for i in range(nb)]

def sim(a,b):
    return sum(x==y for x,y in zip(a,b))/len(a)

print("=== similarity to bank 0 ===")
for i in range(nb):
    print("bank %2d vs 0: %.4f" % (i, sim(banks[0], banks[i])))

print("=== similarity matrix (first 8) ===")
for i in range(min(8,nb)):
    print(" ".join("%.3f" % sim(banks[i], banks[j]) for j in range(min(8,nb))))

print("=== difference map bank0 vs bank1 in 4KB blocks ===")
for off in range(0,0x10000,0x1000):
    a = banks[0][off:off+0x1000]; b = banks[1][off:off+0x1000]
    s = sim(a,b)
    print("0x%04X %.3f" % (off, s), end="  ")
    if (off//0x1000) % 4 == 3: print()

print()
print("=== difference map bank0 vs bank2 in 4KB blocks ===")
for off in range(0,0x10000,0x1000):
    a = banks[0][off:off+0x1000]; b = banks[2][off:off+0x1000]
    s = sim(a,b)
    print("0x%04X %.3f" % (off, s), end="  ")
    if (off//0x1000) % 4 == 3: print()

print()
print("=== unique regions: for each offset, are all banks equal? ===")
eq = 0; neq = 0; runs=[]
cur_start=None
for off in range(0,0x10000):
    vals = [banks[i][off] for i in range(nb)]
    same = all(v==vals[0] for v in vals)
    if same:
        eq += 1
        if cur_start is None: cur_start = off
    else:
        neq += 1
        if cur_start is not None:
            runs.append((cur_start, off-cur_start)); cur_start=None
if cur_start is not None: runs.append((cur_start, 0x10000-cur_start))
print("bytes equal across all 16 banks: %d (%.1f%%), differing: %d (%.1f%%)" % (eq, eq/0x10000*100, neq, neq/0x10000*100))
print("top equal runs:", [(hex(o), hex(l)) for o,l in sorted(runs, key=lambda t:-t[1])[:10]])

# where do banks differ? show first diff offsets
diffs = [off for off in range(0x10000) if len(set(banks[i][off] for i in range(nb)))>1]
print("first diff offsets:", [hex(d) for d in diffs[:10]], "last:", [hex(d) for d in diffs[-10:]])
