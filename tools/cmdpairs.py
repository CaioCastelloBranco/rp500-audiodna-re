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
from collections import Counter

def payload16(img):
    return b''.join(img[k*0x10008+8:k*0x10008+0x10008] for k in range(16))
D = {
    'C48': payload16(open(_P("c48_fw.bin"),'rb').read()),
    'C63': payload16(open(_P("c63_fw.bin"),'rb').read()),
    'RP':  open(_P("rp500_fw.bin"),'rb').read(),
}

for name, d in D.items():
    print('='*70, name)
    pairs = Counter()
    calls = Counter()
    for b in range(16):
        bank = d[b*0x10000:(b+1)*0x10000]
        for i in range(len(bank)-5):
            if bank[i] == 0x7D and bank[i+2] == 0x7F and bank[i+4] == 0x12:
                data = bank[i+1]; cmd = bank[i+3]
                tgt = (bank[i+5] << 8) | (bank[i+6] if i+6 < len(bank) else 0)
                pairs[(cmd, data)] += 1
                calls[(cmd, tgt)] += 1
    print('  (R5=data, R7=cmd) pairs, cmd first:')
    for (cmd, data), n in sorted(pairs.items()):
        print(f'    cmd {cmd:02X} data {data:02X}  x{n}')
    print('  distinct call targets per cmd:')
    tg = {}
    for (cmd, tgt), n in calls.items():
        tg.setdefault(cmd, set()).add(tgt)
    for cmd in sorted(tg):
        print(f'    cmd {cmd:02X} ->', [hex(t) for t in sorted(tg[cmd])])
