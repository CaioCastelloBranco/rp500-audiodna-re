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
print("=== wide strings 0x0A5F00-0x0A6500 ===")
for off,s in ws:
    if 0x0A5F00 <= off < 0x0A6500:
        print("0x%06X %s" % (off, s))

print("=== wide strings containing load/import/export/open/file/wav/sample/ir ===")
for off,s in ws:
    low = s.lower()
    if any(k in low for k in ["load","import","export","open","file","wav","sample","impulse","response","ir "]):
        if len(s) < 160:
            print("0x%06X %s" % (off, s))

print("=== RTTI strings containing Cab ===")
for off,s in ws:
    if s.startswith(".?AV") and "cab" in s.lower():
        print("0x%06X %s" % (off, s))

print("=== raw 'wav' occurrences (ascii, case-insensitive) ===")
for m in re.finditer(rb'(?i)wav', up):
    ctx = up[max(0,m.start()-32):m.start()+64]
    print("0x%06X %r" % (m.start(), ctx))

print("=== raw UTF-16 'wav' occurrences ===")
for m in re.finditer(rb'w\x00a\x00v\x00', up):
    ctx = up[max(0,m.start()-64):m.start()+128]
    print("0x%06X %r" % (m.start(), ctx))
