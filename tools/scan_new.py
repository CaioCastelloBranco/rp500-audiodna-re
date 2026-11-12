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
import re, os, hashlib

files = [
    _P("JUpdater GSP1101vC48.exe"),
    _P("JUserCabUpdater vC59.exe"),
    _P("JUpdater Gsp1101vC63.exe"),
]

for p in files:
    d = open(p, 'rb').read()
    print('=' * 70)
    print(os.path.basename(p), len(d), hashlib.sha1(d).hexdigest())
    # find candidate firmware headers
    for sig in (b'\xea\x80\x68\x02', b'\xea\x00\x02\x00'):
        offs = [m.start() for m in re.finditer(re.escape(sig), d)]
        print('sig', sig.hex(), 'count', len(offs), [hex(o) for o in offs[:8]])
    # candidate base for 16x0x10008 with repeated 8-byte header
    for m in re.finditer(re.escape(b'\xea\x80\x68\x02'), d):
        base = m.start()
        hdr = d[base:base+8]
        ok = all(d[base + k*0x10008:base + k*0x10008+8] == hdr for k in range(1, 16))
        if ok and base + 16*0x10008 <= len(d):
            print('  FIRMWARE base', hex(base), 'header', hdr.hex(' '), 'end', hex(base+16*0x10008))
    # interesting strings
    keys = [b'Wav', b'WAV', b'Aiff', b'AIFF', b'AudioFormat', b'AudioFormatManager',
            b'128', b'user cab', b'User Cab', b'USER CAB', b'Jcabinet', b'JCAB',
            b'cabinet', b'Cabinet', b'ir ', b'Impulse', b'Sysex', b'Super7']
    for k in keys:
        c = d.count(k)
        if c:
            print('  str', k, c)
