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
import numpy as np

def payload16(img):
    return b''.join(img[k*0x10008+8:k*0x10008+0x10008] for k in range(16))

D = {
    'C48': payload16(open(_P("c48_fw.bin"),'rb').read()),
    'C63': payload16(open(_P("c63_fw.bin"),'rb').read()),
    'RP':  open(_P("rp500_fw.bin"),'rb').read(),
}

def fir_blocks(d):
    # interpret as big-endian int32 stream; every 128 ints = 1 block
    n = len(d) // 4
    a = np.frombuffer(d[:n*4], dtype='>i4').astype(np.int64)
    blocks = a[:n//128*128].reshape(-1, 128)
    nz = (blocks != 0).sum(1)
    small = (np.abs(blocks) < (1 << 27)).sum(1)
    e = (blocks.astype(np.float64) ** 2)
    front = e[:, :32].sum(1)
    back = e[:, -32:].sum(1)
    ok = (nz >= 120) & (small >= 120) & (front > 2.5 * (back + 1))
    return blocks, ok

for name, d in D.items():
    blocks, ok = fir_blocks(d)
    idx = np.nonzero(ok)[0]
    print('='*70)
    print(name, 'candidate 512B FIR blocks:', len(idx), 'of', len(blocks))
    # find runs of consecutive line up
    runs = []
    for i in idx:
        if runs and i - runs[-1][1] == 1:
            runs[-1][1] = i
        else:
            runs.append([int(i), int(i)])
    runs = [r for r in runs if r[1] - r[0] + 1 >= 4]
    for a, b in runs[:20]:
        print(f'  run blocks {a}..{b} ({b-a+1} blocks) at {a*512:06X}..{(b+1)*512:06X} bank {a*512//0x10000}')
