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
import re, struct, collections

up = open(_P("JUpdater Gsp1101vC63.exe"),'rb').read()

# UTF-16LE strings
def utf16_strings(data, minlen=4):
    out=[]; i=0; n=len(data)
    while i < n-1:
        # try start of run
        j=i; chars=[]
        while j < n-1 and 32 <= data[j] <= 126 and data[j+1] == 0:
            chars.append(chr(data[j])); j += 2
        if len(chars) >= minlen:
            out.append((i, ''.join(chars)))
            i = j
        else:
            i += 1
    return out

ws = utf16_strings(up, 4)
print("wide strings:", len(ws))
for off,s in ws:
    low = s.lower()
    if any(k in low for k in ["http","www","digitech","harman","update","firmware","gsp","version","download",".com",".net"]):
        print("0x%06X %s" % (off, s[:200]))

# ASCII strings with context around user cab
def strings(data, minlen=4):
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

allstr = strings(up, 4)
print("=== strings near USER_CAB / UserCab / CABINET / WAV ===")
for off,s in allstr:
    low = s.lower()
    if ("user_cab" in low or "usercab" in low or "cabinet" in low or "cab" == low.strip()
        or "impulse" in low or "convol" in low or low.strip().startswith("wav")
        or "sample" in low and "rate" in low):
        print("0x%06X %s" % (off, s[:200]))
