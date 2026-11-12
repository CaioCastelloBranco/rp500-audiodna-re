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
"""Robust search for stored FIR/IR coefficient tables.

A real 128-tap coefficient block has: small integer values, a smooth
(monotone-ish decaying) envelope, and front-loaded energy.  Code or data
bytes interpreted as int32 look like huge random values.
"""
import struct, math
S = _FW
v20=[open(S+r'\v20_res_51E18.bin','rb').read()[k*0x10000:(k+1)*0x10000] for k in range(16)]
def bodies(img): return [img[k*0x10000+k*8:(k+1)*0x10000+k*8] for k in range(16)]
c63=bodies(open(S+r'\c63_fw.bin','rb').read())
c48=bodies(open(S+r'\c48_fw.bin','rb').read())
rp=[open(S+r'\rp500_fw.bin','rb').read()[k*0x10000:(k+1)*0x10000] for k in range(16)]

def is_fir(vals):
    n = len(vals)
    if any(v == 0 for v in vals):
        pass
    if sum(1 for v in vals if v != 0) < 100:
        return False
    if any(abs(v) >= (1 << 24) for v in vals):
        return False
    mag = sum(abs(v) for v in vals)
    if mag == 0:
        return False
    tv = sum(abs(vals[i+1] - vals[i]) for i in range(n-1))
    if tv > 0.6 * mag:          # smooth sequence
        return False
    e = [v*v for v in vals]
    front = sum(e[:24]); back = sum(e[-24:])
    if front < 2.0 * (back + 1):
        return False
    return True

def scan(banks, label):
    hits = []
    for k, b in enumerate(banks):
        # aligned 512-byte blocks, plus 4-byte-shifted grids to catch any alignment
        for off in range(0, len(b)-512+1, 512):
            vals = struct.unpack('>128i', b[off:off+512])
            if is_fir(vals):
                hits.append((k, off))
    # runs at 512 stride
    runs = []
    for k, o in hits:
        if runs and runs[-1][0] == k and o - runs[-1][1] == 512:
            runs[-1][1] = o
        else:
            runs.append([k, o])
    maxrun = max([(r[1]-r[0])//512 + 1 for r in runs] or [0])
    print('  %-4s hits=%d  runs=%d  max_run=%d' % (label, len(hits), len(runs), maxrun))
    for r in runs[:8]:
        print('       bank%d 0x%04X..0x%04X (%d blocks)' % (r[0], r[1], r[1]+512, (r[1]-r[0])//512+1))
    return hits

if __name__ == '__main__':
    print('=== strict FIR-block scan ===')
    for nm, bs in (('c48', c48), ('c63', c63), ('rp', rp), ('v20', v20)):
        scan(bs, nm)

    print()
    print('=== how many 512B blocks have all |v| < 2^24 (necessary condition)? ===')
    for nm, bs in (('c48', c48), ('c63', c63), ('rp', rp)):
        cnt = 0; tot = 0
        for b in bs:
            for off in range(0, len(b)-512+1, 512):
                vals = struct.unpack('>128i', b[off:off+512]); tot += 1
                if all(abs(v) < (1 << 24) for v in vals): cnt += 1
        print('  %-4s %d / %d' % (nm, cnt, tot))
