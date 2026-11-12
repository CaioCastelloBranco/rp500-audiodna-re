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
def payload16(img):
    return b''.join(img[k*0x10008+8:k*0x10008+0x10008] for k in range(16))

D = {
    'V20': open(_P("v20_res_51E18.bin"),'rb').read(),
    'C48': payload16(open(_P("c48_fw.bin"),'rb').read()),
    'C63': payload16(open(_P("c63_fw.bin"),'rb').read()),
    'RP':  open(_P("rp500_fw.bin"),'rb').read(),
}

W = 64
def informative(blk):
    return len(set(blk)) >= 12

def blockmap(d):
    m = {}
    for i in range(0, len(d) - W + 1, W):
        blk = d[i:i+W]
        if informative(blk):
            m.setdefault(blk, []).append(i)
    return m

def runs(a, b, minlen=768):
    mb = blockmap(b)
    out = []
    i = 0
    n = len(a)
    while i + W <= n:
        blk = a[i:i+W]
        cand = mb.get(blk) if informative(blk) else None
        if cand:
            best = 0; bestj = None
            for j in cand:
                k = 0
                while i + k < n and j + k < len(b) and a[i+k] == b[j+k]:
                    k += 1
                if k > best:
                    best = k; bestj = j
            if best >= minlen:
                out.append((i, bestj, best))
                i += best
                continue
        i += W
    return out

for name in ('C48', 'C63', 'RP'):
    print('='*76)
    print(f'V20 vs {name}: informative identical runs >= 768 bytes')
    rr = runs(D['V20'], D[name], 768)
    for a, b, l in rr:
        print(f'  V20 {a:06X} == {name} {b:06X}  len {l:5d}  banks {a//0x10000}->{b//0x10000}')
    print('  runs', len(rr), 'bytes', sum(x[2] for x in rr))
