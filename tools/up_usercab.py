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

up = open(_P("JUpdater Gsp1101vC63.exe"),'rb').read()

def ascii_strings(data, minlen=4):
    out=[]; cur=bytearray(); start=0
    for i,c in enumerate(data):
        if 32 <= c <= 126:
            if not cur: start=i
            cur.append(c)
        else:
            if len(cur)>=minlen: out.append((start,cur.decode('ascii')))
            cur=bytearray()
    if len(cur)>=minlen: out.append((start,cur.decode('ascii')))
    return out

def utf16_strings(data, minlen=4):
    out=[]; i=0; n=len(data)
    while i < n-1:
        j=i; chars=[]
        while j < n-1 and 32 <= data[j] <= 126 and data[j+1] == 0:
            chars.append(chr(data[j])); j += 2
        if len(chars) >= minlen:
            out.append((i, ''.join(chars))); i = j
        else:
            i += 1
    return out

print("=== ASCII user/cab/wav/ir strings ===")
for off,s in ascii_strings(up, 3):
    low = s.lower()
    if ("user" in low or "cab" in low or "impulse" in low or "convol" in low
        or low.endswith(".wav") or low.endswith(".aif") or low.endswith(".aiff")
        or low.endswith(".syx") or low.endswith(".mid") or low.endswith(".bin")
        or low.endswith(".dat") or low.endswith(".gsp") or "*.wav" in low or "*.aif" in low):
        if len(s) < 160:
            print("0x%06X %s" % (off, s))

print("=== wide user/cab/wav/ir strings ===")
for off,s in utf16_strings(up, 3):
    low = s.lower()
    if ("user" in low or "cab" in low or "impulse" in low or "convol" in low
        or low.endswith(".wav") or low.endswith(".aif") or low.endswith(".aiff")
        or low.endswith(".syx") or low.endswith(".mid") or low.endswith(".bin")
        or low.endswith(".dat") or low.endswith(".gsp") or "*.wav" in low or "*.aif" in low):
        if len(s) < 160:
            print("0x%06X %s" % (off, s))

# pointer search: LE dword of key string VAs
targets = {
    "USER_CAB %D": 0x5b5e7f,
    "UserCabGainPage RTTI": 0x5c3034,
    "Store cabinet...": 0x4a7790,
    "GLOBAL CABINET": 0x5b4aed,  # guess? will verify
}
def find_ptr(val):
    pat = struct.pack('<I', val)
    return [m.start() for m in re.finditer(re.escape(pat), up)]

for name, va in targets.items():
    hits = find_ptr(va)
    print("pointer to %s (0x%X): %s" % (name, va, [hex(h) for h in hits[:20]]))

# locate USER n strings and dump context
print("=== USER n strings ===")
for off,s in ascii_strings(up, 3):
    if re.fullmatch(r'USER ?\d+', s.strip()) or re.fullmatch(r'USER_CAB ?\d*', s.strip()):
        print("0x%06X %r" % (off, s))

# find "USER 1" and dump raw context
m = re.search(rb'USER 1\x00', up)
print("USER 1 first:", hex(m.start()) if m else None)
if m:
    a = m.start()
    for i in range(max(0,a-128), min(len(up), a+512), 16):
        c = up[i:i+16]
        print("0x%06X  %-47s  %s" % (i, c.hex(' '), ''.join(chr(b) if 32<=b<127 else '.' for b in c)))
