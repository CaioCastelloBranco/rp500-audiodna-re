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
_FW = _os.path.join(_ROOT, "01_source_firmware")


def _OUT(name):
    """Derived/output artifacts go to the script directory."""
    return _os.path.join(_SW, name)


import sys
sys.path.insert(0, _FW)
from d51 import disasm

def payload16(img):
    return b''.join(img[k*0x10008+8:k*0x10008+0x10008] for k in range(16))

RP = open(_P("rp500_fw.bin"),'rb').read()

def decode_at(d, a):
    r = disasm(d, 0, a, a+4, max_ins=1)
    if not r: return None
    addr, raw, txt = r[0]
    return len(raw.split()), txt

def targets(d):
    ts = set()
    for i in range(len(d)-2):
        if d[i] in (0x02, 0x12):
            ts.add((d[i+1] << 8) | d[i+2])
    return ts

def trace(d, seeds, limit=500000):
    seen = {}
    work = list(seeds)
    while work and len(seen) < limit:
        a = work.pop()
        if a in seen or a < 0 or a >= len(d): continue
        r = decode_at(d, a)
        if r is None: continue
        size, txt = r
        seen[a] = (size, txt)
        nxt = a + size
        op = txt.split()[0]
        def targ():
            return int(txt.replace(',', ' ').split()[-1].rstrip('h'), 16)
        if op in ('LJMP', 'AJMP', 'SJMP'): work.append(targ()); continue
        if op in ('JC','JNC','JZ','JNZ','JB','JNB','JBC','DJNZ','CJNE'):
            work.append(targ()); work.append(nxt); continue
        if op in ('LCALL','ACALL'): work.append(targ()); work.append(nxt); continue
        if op in ('RET','RETI','JMP'): continue
        work.append(nxt)
    return seen

bank = 9
d = RP[bank*0x10000:(bank+1)*0x10000]
seeds = set(range(0, 0x2C, 1)) | targets(d) | {0xB774, 0xB700, 0xB740}
seen = trace(d, seeds)
print('traced', len(seen))
lo, hi = 0xB6C0, 0xB860
for a in sorted(seen):
    if lo <= a <= hi:
        size, txt = seen[a]
        print(f'{a:04X}: {d[a:a+size].hex(" "):<10} {txt}')
print()
print('--- raw ---')
for a in range(0xB740, 0xB820, 16):
    print(f'{a:04X}: {d[a:a+16].hex(" ")}')
