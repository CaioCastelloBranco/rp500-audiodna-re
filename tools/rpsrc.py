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
def dump(d, base, lo, hi, label):
    print('='*78)
    print(label, hex(base+lo), '->', hex(base+hi))
    for a in range(lo, hi, 16):
        row = d[base+a:base+a+16]
        txt = ''.join(chr(b) if 32 <= b < 127 else '.' for b in row)
        print(f'{a:04X}: {row.hex(" "):<48} {txt}')

rp = open(_P("rp500_fw.bin"),'rb').read()
dump(rp, 15*0x10000, 0x2E20, 0x2F40, 'RP500 bank15 (DSP upload source 0x2E3B)')

# how much of 0x2E3B..0xAE33 is 0xFF?
seg = rp[15*0x10000+0x2E3B:15*0x10000+0xAE33]
print()
print('segment 0x2E3B..0xAE33 len', hex(len(seg)), '0xFF fraction %.1f%%' % (100*seg.count(0xff)/len(seg)))
print('distinct bytes', len(set(seg)))
