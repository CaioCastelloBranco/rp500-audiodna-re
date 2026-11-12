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


import struct, re

RP = open(_P("rp_fw.bin"),'rb').read()
RPB=[RP[k*0x10000:(k+1)*0x10000] for k in range(16)]

def strings(data, minlen=3):
    out=[]; cur=bytearray(); start=0
    for i,c in enumerate(data):
        if 32<=c<=126:
            if not cur: start=i
            cur.append(c)
        else:
            if len(cur)>=minlen: out.append((start,bytes(cur).decode('ascii')))
            cur=bytearray()
    if len(cur)>=minlen: out.append((start,bytes(cur).decode('ascii')))
    return out

print("=== RP strings matching output/XLR/cab/sim/monitor/balanced etc ===")
kw = ('XLR','CAB','SPKR','SPEAK','SIM','OUT','MONO','STEREO','LEFT','RIGHT','BAL','MIC','LINE',
      'DIRECT','MIX','ROUT','DEST','MAIN','PHONES','HEADPH','AMP','SPK','EMU','FILTER','EQ')
seen=set()
for off,s in strings(RP,3):
    u=s.upper()
    if any(w in u for w in kw) and len(s)<=48:
        # skip obvious amp model names and duplicated UI labels if desired; print all with bank
        bank=off>>16; boff=off&0xFFFF
        print("0x%06X (b%02d:%04X) %r" % (off,bank,boff,s))

print()
print("=== Full RP parameter-name table (86 x 18 bytes at bank6 0xC551) ===")
start=0xC551
for i in range(86):
    rec=RPB[6][start+i*0x12:start+(i+1)*0x12]
    s=rec.split(b'\x00')[0]
    try: name=s.decode('ascii')
    except: name=repr(s)
    print("%2d  0x%04X  %s" % (i, start+i*0x12, name))
