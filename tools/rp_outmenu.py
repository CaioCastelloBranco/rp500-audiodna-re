# --- portable path resolution (added 2026-11-10) ---------------------------
import os as _os

_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_SW = _os.path.dirname(_os.path.abspath(__file__))


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


import struct

RP = open(_P("rp_fw.bin"),'rb').read()
RPB=[RP[k*0x10000:(k+1)*0x10000] for k in range(16)]

def dump(bank, off, n, tag):
    print("--- %s 0x%04X ---" % (tag, off))
    for i in range(off, off+n, 16):
        c=bank[i:i+16]
        print("0x%04X  %-47s  %s" % (i, c.hex(' '), ''.join(chr(x) if 32<=x<127 else '.' for x in c)))

print("=== RP bank4 0x2C00-0x3300 (setup/output UI strings) ===")
dump(RPB[4], 0x2C00, 0x700, "RP b4")

print()
print("=== Cross refs: big-endian 16-bit pointers to key strings (bank4) ===")
targets = {
 'OUTPUT  %2D':0x3197, 'AMP/CAB % *s':0x3274, 'AMP SEL':0x3281, 'CAB SEL':0x3289,
 '57 CHAMP':0x3291, '1/4 AMP':0x3071, '1/4 MIX':0x3079,
 'MONO  ':0x3063, 'STEREO':0x306A, 'LEFT   ':0x2CAC, 'RIGHT  ':0x2CB4,
 'PRE  AMP':0x2FE0, 'POST AMP':0x2FE9, 'AMP LOOP':0x2FFF,
 'USB OUT   ':0x2CB3,
}
for name,off in targets.items():
    be=bytes([off>>8, off&0xFF])
    hits=[]
    for k in range(16):
        b=RPB[k]
        idx=0
        while True:
            i=b.find(be,idx)
            if i<0: break
            hits.append((k,i)); idx=i+1
    print("%-12s 0x%04X  BE hits %s" % (name,off,[('b%d:%04X'%h) for h in hits[:12]]))

print()
print("=== Any XLR text (case-insensitive) in RP image? ===")
for pat in (b'XLR', b'xlr', b'Xlr', b'BALANCED', b'Balanced'):
    idx=0; hits=[]
    while True:
        i=RP.find(pat,idx)
        if i<0: break
        hits.append(i); idx=i+1
    print(pat, [hex(h) for h in hits[:20]], 'count', len(hits))

print()
print("=== Strings containing GLOBAL/GL / SETUP / CONFIG / OUTPUT / ROUTING ===")
def strings(data, minlen=3):
    out=[]; cur=bytearray(); start=0
    for i,c in enumerate(data):
        if 32<=c<=126:
            if not cur: start=i
            cur.append(c)
        else:
            if len(cur)>=minlen: out.append((start,bytes(cur).decode('ascii')))
            cur=bytearray()
    return out
for off,s in strings(RP,3):
    u=s.upper()
    if any(w in u for w in ('GLOBAL','GL PARAM','SETUP','CONFIG','ROUT','OUTPUT','1/4','XLR','SPDIF','BALANC','DIRECT OUT')):
        print("0x%06X (b%02d:%04X) %r" % (off,off>>16,off&0xFFFF,s))
