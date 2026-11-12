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
S = _FW
v20raw = open(S+r'\v20_res_51E18.bin','rb').read()
v20 = [v20raw[k*0x10000:(k+1)*0x10000] for k in range(16)]
def bodies(img):
    return [img[k*0x10000 + k*8 : (k+1)*0x10000 + k*8] for k in range(16)]
c63 = bodies(open(S+r'\c63_fw.bin','rb').read())
c48 = bodies(open(S+r'\c48_fw.bin','rb').read())

print('=== V20: search cab-ish tokens ===')
for tok in (b'DLUX', b'BRIT', b'TWIN', b'JAZZ', b'METL', b'ROCK', b'DREAD', b'JUMBO',
            b'DIRECT', b'CHAMP', b'CAB', b'SPKR', b'4X12', b'2X12', b'1X12'):
    hits = [m.start() for m in re.finditer(re.escape(tok), v20raw)]
    print('  %-8s n=%d  %s' % (tok.decode(), len(hits), [hex(h) for h in hits[:6]]))

print()
print('=== V20 bank10 around 0x57C8 ===')
b = v20[10]
for a in range(0x5780, 0x5900, 16):
    row = b[a:a+16]
    txt = ''.join(chr(x) if 32<=x<127 else '.' for x in row)
    print('   %04X: %-48s %s' % (a, row.hex(' '), txt))

print()
print('=== C48 cab block tail (after JUMBO AC) ===')
b = c48[10]
i = b.find(b'JUMBO AC')
print('  JUMBO AC @0x%04X' % i)
for a in range(i-0x10, i+0x80, 16):
    row = b[a:a+16]
    txt = ''.join(chr(x) if 32<=x<127 else '.' for x in row)
    print('   %04X: %-48s %s' % (a, row.hex(' '), txt))

print()
print('=== C63 USER slots tail ===')
b = c63[11]
i = b.find(b'USER 1')
for a in range(i-0x10, i+0x70, 16):
    row = b[a:a+16]
    txt = ''.join(chr(x) if 32<=x<127 else '.' for x in row)
    print('   %04X: %-48s %s' % (a, row.hex(' '), txt))
