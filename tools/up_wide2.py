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

up = open(_P("JUpdater Gsp1101vC63.exe"),'rb').read()

def utf16_strings(data, minlen=3):
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

ws = utf16_strings(up, 3)
print("=== wide strings 0xAE000-0xAF000 ===")
for off,s in ws:
    if 0xAE000 <= off < 0xAF000:
        print("0x%06X %s" % (off, s))

print("=== wide strings containing server/target/firmware/url/http ===")
for off,s in ws:
    low = s.lower()
    if any(k in low for k in ["server","target","firmware","url","http","https","download","image","version","gsp"]):
        if len(s) < 200:
            print("0x%06X %s" % (off, s))

print("=== ASCII strings 0xAE200-0xAF200 ===")
seg = up[0xAE200:0xAF200]
for m in re.finditer(rb'[\x20-\x7E]{3,}', seg):
    print("0x%06X %s" % (0xAE200+m.start(), m.group().decode()[:150]))
