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

rp = open(_P("rp500_fw.bin"),'rb').read()

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

allstr = strings(rp, 4)
print("total strings:", len(allstr))
print("=== cab / amp / ir / user / preset related ===")
for off,s in allstr:
    low = s.lower()
    if any(k in low for k in ["cab","amp","ir ","user","convol","impulse","speaker","mic","preset","dsp","firmware","version","flash","sysex","midi","model"]):
        print("0x%06X %s" % (off, s[:140]))

print("=== strings 0x30000-0x60000 ===")
for off,s in allstr:
    if 0x30000 <= off < 0x60000:
        print("0x%06X %s" % (off, s[:140]))

def dump(off, n=128):
    print("--- 0x%X ---" % off)
    for i in range(0, n, 16):
        c = rp[off+i:off+i+16]
        asc = ''.join(chr(b) if 32 <= b < 127 else '.' for b in c)
        print("0x%06X  %-47s  %s" % (off+i, c.hex(' '), asc))

# dump around known cab strings if found
for off,s in allstr:
    if s.strip() in ("CAB_TYPE","CAB SEL","DXRV1X12","DIRECT","AMP/CAB"):
        dump(max(0,off-32), 96)
