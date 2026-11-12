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

c48 = payload16(open(_P("c48_fw.bin"),'rb').read())
c63 = payload16(open(_P("c63_fw.bin"),'rb').read())

# Build instruction map by linear-sweep from 0 but re-sync at every 0x22 (RET) - crude.
# Instead: decode one instruction at an address using d51.disasm
def decode_at(d, a):
    r = disasm(d, 0, a, a+4, max_ins=1)
    if not r:
        return None
    addr, raw, txt = r[0]
    size = len(raw.split())
    return size, txt

def trace(d, seeds, limit=200000):
    seen = {}
    work = list(seeds)
    while work:
        a = work.pop()
        if a in seen or a < 0 or a >= len(d):
            continue
        r = decode_at(d, a)
        if r is None:
            continue
        size, txt = r
        seen[a] = (size, txt)
        nxt = a + size
        op = txt.split()[0]
        if op in ('LJMP', 'AJMP', 'SJMP'):
            t = int(txt.split()[1].rstrip('h'), 16)
            work.append(t)
            continue
        if op in ('JC', 'JNC', 'JZ', 'JNZ'):
            t = int(txt.split()[1].rstrip('h'), 16)
            work.append(t); work.append(nxt)
            continue
        if op in ('JB', 'JNB', 'JBC'):
            # JB bit,target   (bit, target have h suffix)
            parts = txt.replace(',', ' ').split()
            t = int(parts[-1].rstrip('h'), 16)
            work.append(t); work.append(nxt)
            continue
        if op == 'DJNZ' or op == 'CJNE':
            parts = txt.replace(',', ' ').split()
            t = int(parts[-1].rstrip('h'), 16)
            work.append(t); work.append(nxt)
            continue
        if op in ('LCALL', 'ACALL'):
            t = int(txt.split()[1].rstrip('h'), 16)
            work.append(t); work.append(nxt)
            continue
        if op in ('RET', 'RETI', 'LJMP'):
            continue
        if op in ('JMP',):
            continue
        work.append(nxt)
    return seen

def dump(d, seen, start, end, label):
    print('='*80)
    print(label, f'{start:04X}..{end:04X}')
    for a in sorted(seen):
        if start <= a <= end:
            size, txt = seen[a]
            print(f'{a:04X}: {d[a:a+size].hex(" "):<10} {txt}')

for name, img, bank, lo, hi in [
    ('C48 b14', c48, 14, 0xDA00, 0xDB20),
    ('C63 b14', c63, 14, 0xDA50, 0xDB70),
]:
    d = img[bank*0x10000:(bank+1)*0x10000]
    seeds = [0x0000] + list(range(0x0003, 0x002C, 8))
    seen = trace(d, seeds)
    dump(d, seen, lo, hi, name)
