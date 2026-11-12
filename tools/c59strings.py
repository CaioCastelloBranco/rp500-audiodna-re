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
import re, os

p = _P("JUserCabUpdater vC59.exe")
d = open(p, 'rb').read()
print('size', hex(len(d)))

def strings16(buf):
    # UTF-16LE printable runs
    out = []
    i = 0
    n = len(buf)
    cur = []
    while i + 1 < n:
        lo, hi = buf[i], buf[i+1]
        if hi == 0 and 32 <= lo < 127:
            cur.append(chr(lo)); i += 2
        else:
            if len(cur) >= 5:
                out.append((i - len(cur)*2, ''.join(cur)))
            cur = []
            i += 2
    if len(cur) >= 5:
        out.append((i - len(cur)*2, ''.join(cur)))
    return out

def strings8(buf):
    return [(m.start(), m.group().decode('ascii', 'replace'))
            for m in re.finditer(rb'[\x20-\x7e]{5,}', buf)]

a8 = strings8(d)
a16 = strings16(d)
allstr = [(o, s, 'A') for o, s in a8] + [(o, s, 'W') for o, s in a16]

keys = ('cab', 'Cab', 'CAB', 'ir', 'IR', 'wav', 'WAV', 'sysex', 'Sysex', 'SysEx',
        'store', 'Store', 'GSP', 'gsp', 'temporary', 'Temporary', 'mono', 'Mono',
        '128', 'position', 'Position', 'gain', 'Gain', 'sample', 'Sample', '44', 'hz')
seen = set()
for o, s, k in sorted(allstr):
    if any(x in s for x in keys) and s not in seen:
        seen.add(s)
        print(f'{o:08X} {k} {s[:110]}')
