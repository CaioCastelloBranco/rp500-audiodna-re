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

def strings(d, minlen=5):
    out = []
    for m in re.finditer(rb'[\x20-\x7e]{%d,}' % minlen, d):
        out.append((m.start(), m.group().decode('latin1')))
    for m in re.finditer(rb'(?:[\x20-\x7e]\x00){%d,}' % minlen, d):
        out.append((m.start(), m.group().decode('utf-16le')))
    return out

p = _P("JUserCabUpdater vC59.exe")
d = open(p, 'rb').read()
print('len', len(d))
print('PE', d[:2], 'mz', d[:2] == b'MZ')
ss = strings(d, 4)
keys = ('cab', 'Cab', 'CAB', 'wav', 'Wav', 'WAV', 'aiff', 'Aiff', 'Impulse', 'impulse',
        'USER', 'User', 'user', 'Sysex', 'Super7', '128', 'sample', 'Sample', 'IR ',
        '.ir', 'Load', 'load', 'Store', 'store', 'Position', 'Gain', 'gain', 'File', 'file')
seen = set()
for off, s in ss:
    if any(k in s for k in keys) and s not in seen:
        seen.add(s)
        print(hex(off), repr(s))
