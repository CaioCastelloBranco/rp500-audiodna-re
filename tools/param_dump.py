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


import re

RP = open(_P("rp_fw.bin"),'rb').read()
GSP = open(_P("gsp_fw.bin"),'rb').read()
RPB=[RP[k*0x10000:(k+1)*0x10000] for k in range(16)]
GSPB=[GSP[k*0x10000:(k+1)*0x10000] for k in range(16)]

def dump(bank, off, n, tag):
    print("--- %s 0x%04X ---" % (tag, off))
    for i in range(off, off+n, 16):
        c=bank[i:i+16]
        print("0x%04X  %-47s  %s" % (i, c.hex(' '), ''.join(chr(x) if 32<=x<127 else '.' for x in c)))

print("=== RP bank6 0x6C680-0x6C800 (parameter names) ===")
dump(RPB[6], 0x6C680, 0x180, "RP b6")

print("=== locate CAB_TYPE / USER_CAB / CABINET in RP and GSP ===")
for name,data in [("RP",RP),("GSP",GSP)]:
    for kw in [b'CAB_TYPE',b'USER_CAB',b'CABINET',b'CAB_INDEX',b'CABINET_TYPE',b'CABINET_MODEL']:
        idx=0; hits=[]
        while True:
            i=data.find(kw,idx)
            if i<0: break
            hits.append(i); idx=i+1
        if hits: print(name, kw, [hex(h) for h in hits[:10]])

print("=== RP bank0/1/2 common param-name block 0x6C600? (flat) ===")
for bank in range(3):
    idx=RPB[bank].find(b'CAB_TYPE')
    print("bank",bank,"CAB_TYPE at",hex(idx) if idx>=0 else None)
    if idx>=0:
        dump(RPB[bank], max(0,idx-0x40), 0xE0, "bank%d around CAB_TYPE"%bank)
        break

print("=== GSP: find CAB_TYPE and dump around ===")
for bank in range(16):
    idx=GSPB[bank].find(b'CAB_TYPE')
    if idx>=0:
        dump(GSPB[bank], max(0,idx-0x40), 0xE0, "GSP bank%d around CAB_TYPE"%bank)
        break
else:
    print("no CAB_TYPE in GSP")

print("=== GSP: strings containing CAB in param-name style (uppercase underscores) ===")
def strings(data, minlen=4):
    out=[]; cur=bytearray(); start=0
    for i,c in enumerate(data):
        if 32 <= c <= 126:
            if not cur: start=i
            cur.append(c)
        else:
            if len(cur)>=minlen: out.append((start,cur.decode('ascii')))
            cur=bytearray()
    return out
for off,s in strings(GSP,4):
    if "CAB" in s.upper() and len(s)<40:
        print("0x%06X %r" % (off,s))
