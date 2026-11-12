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

GSPF = open(_P("gsp_fw.bin"),'rb').read()
RP = open(_P("rp_fw.bin"),'rb').read()
UP = open(_P("JUpdater Gsp1101vC63.exe"),'rb').read()

def ascii_strings(data, minlen=3):
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

print("=== 'C63' / firmware version in updater and firmwares ===")
for name,data in [("UP",UP),("GSP",GSPF),("RP",RP)]:
    for m in re.finditer(rb'C\d\d|c\d\d', data):
        ctx=data[max(0,m.start()-24):m.start()+40]
        print(name, "0x%06X %r" % (m.start(), ctx))

print("=== GSP dump around SDram/DNA diagnostics 0xD3140-0xD3220 ===")
for i in range(0xD3140, 0xD3220, 16):
    c=GSPF[i:i+16]
    print("0x%06X  %-47s  %s" % (i, c.hex(' '), ''.join(chr(x) if 32<=x<127 else '.' for x in c)))

print("=== RP 'PRE DSP'/'POST DSP'/'SAMPLE' ===")
for off,s in ascii_strings(RP,3):
    low=s.lower()
    if "dsp" in low or "sample" in low or "flash_data" in low:
        print("0x%06X %r" % (off,s[:100]))

print("=== GSP 'USER_CAB' etc. in *bank 15* raw offsets and nearby bytes ===")
b=GSPF[15*0x10000:16*0x10000]
for s in [b"USER_CAB %D", b"FLASH_DATA: %D", b"SEND BLOCK", b"PROGRAM: %D", b"PRE SAMPLE"]:
    i=b.find(s)
    print(s, hex(0x3000+i) if i>=0 else None)

print("=== does GSP firmware contain 'convol'/'impulse'/'tap'/'fir' ===")
for name,data in [("GSP",GSPF),("RP",RP)]:
    for kw in [b'CONVOL',b'Convol',b'convol',b'IMPULSE',b'Impulse',b'impulse',b'TAP ',b'FIR ']:
        if kw in data:
            print(name, kw, hex(data.find(kw)))
