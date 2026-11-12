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
    'RP':  open(_P("rp500_fw.bin"),'rb').read(),
    'C48': payload16(open(_P("c48_fw.bin"),'rb').read()),
    'C63': payload16(open(_P("c63_fw.bin"),'rb').read()),
}
tabs = {'RP': 0x43486, 'C48': 0xa7618, 'C63': 0xbd8ee}

for name, addr in tabs.items():
    d = D[name]
    bank = addr // 0x10000
    off = addr % 0x10000
    pat = bytes([0x90, off >> 8, off & 0xFF])
    hits = []
    for b in range(16):
        base = b * 0x10000
        for i in range(base, base + 0x10000 - 2):
            if d[i:i+3] == pat:
                hits.append((b, i - base))
    print('='*60)
    print(name, f'cab table {addr:06X} (bank {bank}, off {off:04X})')
    print(' MOV DPTR,#%04X hits:' % off, [(b, hex(o)) for b, o in hits])
    # also AJMP/LJMP/LCALL target equals this offset
    for op in (0x02, 0x12, 0x01):
        pat2 = bytes([op, off >> 8, off & 0xFF]) if op in (2, 0x12) else None
        if pat2:
            h2 = []
            for b in range(16):
                base = b * 0x10000
                for i in range(base, base + 0x10000 - 2):
                    if d[i:i+3] == pat2:
                        h2.append((b, i - base))
            print(f' op{op:02X} hits:', [(b, hex(o)) for b, o in h2][:8])
