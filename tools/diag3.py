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
S = _FW
for nm, path in (('c63', S+r'\c63_fw.bin'), ('c48', S+r'\c48_fw.bin')):
    d = open(path,'rb').read()
    print('===', nm, 'size', hex(len(d)))
    hits = []
    for m in re.finditer(rb'\x00(..)\x00\x00\x00\x01\x00\x00', d, re.S):
        k = m.group(1)[0]
        hits.append((m.start(), k))
    print(' descriptor-like hits:', len(hits))
    print(' offsets:', [hex(o) for o,_ in hits][:20])
    print(' indices:', [k for _,k in hits][:20])
    # check the expected [body][desc] model: desc_k at (k)*(0x10000)+ (k-1)*8
    print(' model [body0][desc1][body1]...:')
    for k in range(1,16):
        exp = k*0x10000 + (k-1)*8
        got = d[exp:exp+8]
        print('   desc%-2d expected@%06X -> %s  %s' % (k, exp, got.hex(' '), 'OK' if got[:2]==b'\x00'+bytes([k]) else 'MISMATCH'))
    print(' last 16 bytes:', d[-16:].hex(' '))
    print(' stub occurrences (first 12):', [hex(m.start()) for m in re.finditer(re.escape(bytes.fromhex('ea806802')), d)][:12])
