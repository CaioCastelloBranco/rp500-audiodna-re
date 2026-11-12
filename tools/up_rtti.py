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
import re, struct

UP = open(_P("JUpdater Gsp1101vC63.exe"),'rb').read()

# section map
e = struct.unpack_from('<I', UP, 0x3C)[0]
n = struct.unpack_from('<H', UP, e+6)[0]
opt = struct.unpack_from('<H', UP, e+20)[0]
so = e+24+opt
secs=[]
for i in range(n):
    name = UP[so+i*40:so+i*40+8].rstrip(b'\x00').decode()
    vs,va,rs,ro = struct.unpack_from('<IIII', UP, so+i*40+8)
    secs.append((name,va,vs,ro,rs))
def f2va(f):
    for name,va,vs,ro,rs in secs:
        if ro <= f < ro+rs:
            return va + (f-ro), name
    return None,None
def va2f(v):
    for name,va,vs,ro,rs in secs:
        rva = v - 0x400000
        if va <= rva < va+vs:
            return ro + (rva-va), name
    return None,None

print("sections:", [(s[0],hex(s[1]),hex(s[2]),hex(s[3])) for s in secs])

# ASCII RTTI
print("=== ASCII RTTI classes with Cab/User/Impulse/IR/Wav/Amp/Speaker ===")
for m in re.finditer(rb'\.\?AV[A-Za-z0-9_@?$<>]+@@', UP):
    s=m.group().decode('ascii','replace')
    low=s.lower()
    if any(k in low for k in ["cab","user","impulse","ir","wav","amp","speaker","conv"]):
        va,sec=f2va(m.start())
        print("0x%06X (VA 0x%X %s) %s" % (m.start(), va, sec, s))

print("=== all RTTI with 'Cab' (any) ===")
for m in re.finditer(rb'\.\?AV[A-Za-z0-9_@?$<>]+@@', UP):
    s=m.group().decode('ascii','replace')
    if "cab" in s.lower():
        print(s)

# wide strings list around the user-cab UI and their VAs
print("=== wide strings 0xA6000-0xA6500 with VA ===")
i=0
def wide_at(i):
    j=i; chars=[]
    while j < len(UP)-1 and 32 <= UP[j] <= 126 and UP[j+1]==0:
        chars.append(chr(UP[j])); j+=2
    return ''.join(chars)
n2=len(UP)
i=0xA6000
while i<0xA6500:
    s=wide_at(i)
    if len(s)>=3:
        va,sec=f2va(i)
        print("0x%06X VA=0x%X %r" % (i,va,s))
        i += len(s)*2
    else:
        i+=1
