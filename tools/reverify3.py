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

print('=== V20 raw-file absolute offsets ===')
for s in (b'USER_CAB %D', b'CHAMP1X8', b'SEND BLOCK', b'USER 1'):
    hits = [m.start() for m in re.finditer(re.escape(s), v20raw)]
    print('  %-14s %s' % (s.decode(), [hex(h) for h in hits[:8]]))

print()
print('=== V20 cab name block (bank10) ===')
b = v20[10]
i = b.find(b'CHAMP1X8')
print('  CHAMP1X8 @0x%04X' % i)
for a in range(max(0,i-0x60), i+0x100, 16):
    row = b[a:a+16]
    print('   %04X: %s' % (a, row.hex(' ')))

print()
print('=== C63 cab name block extent (bank11) ===')
b = c63[11]
i = b.find(b'CHAMP1X8')
print('  CHAMP1X8 @0x%04X' % i)
for a in range(max(0,i-0x40), i+0x120, 16):
    row = b[a:a+16]
    txt = ''.join(chr(x) if 32<=x<127 else '.' for x in row)
    print('   %04X: %-48s %s' % (a, row.hex(' '), txt))

print()
print('=== C48 cab block extent (bank10) ===')
b = c48[10]
i = b.find(b'CHAMP1X8')
print('  CHAMP1X8 @0x%04X' % i)
for a in range(max(0,i-0x40), i+0x100, 16):
    row = b[a:a+16]
    txt = ''.join(chr(x) if 32<=x<127 else '.' for x in row)
    print('   %04X: %-48s %s' % (a, row.hex(' '), txt))

print()
print('=== V20 vs C63: same cab-name list? ===')
def names(banks, bank, start, n=30):
    b = banks[bank]
    out=[]
    p = start
    for _ in range(n):
        e = b.find(b'\x00', p)
        if e < 0 or e == p: break
        out.append(b[p:e].decode('ascii','replace'))
        p = e+1
    return out
print('  V20 bank10 from 0x%04X:' % (v20[10].find(b'CHAMP1X8')-0*1))
print('   ', names(v20, 10, v20[10].find(b'CHAMP1X8'))[:30])
print('  C63 bank11 from CHAMP1X8:')
print('   ', names(c63, 11, c63[11].find(b'CHAMP1X8'))[:30])
print('  C48 bank10 from CHAMP1X8:')
print('   ', names(c48, 10, c48[10].find(b'CHAMP1X8'))[:30])
