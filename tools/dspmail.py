# --- portable path resolution (added 2026-11-10) ---------------------------
import os as _os

_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_SW = _os.path.dirname(_os.path.abspath(__file__))


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
_FW = _os.path.join(_ROOT, "01_source_firmware")


def _OUT(name):
    """Derived/output artifacts go to the script directory."""
    return _os.path.join(_SW, name)


import sys
sys.path.insert(0, _FW)
from d51 import disasm

def payload16(img):
    return b''.join(img[k*0x10008+8:k*0x10008+0x10008] for k in range(16))
D = {
    'V20': open(_P("v20_res_51E18.bin"),'rb').read(),
    'C48': payload16(open(_P("c48_fw.bin"),'rb').read()),
    'C63': payload16(open(_P("c63_fw.bin"),'rb').read()),
    'RP':  open(_P("rp500_fw.bin"),'rb').read(),
}

def align_back(d, ref, maxback=160):
    """find a start address <= ref from which linear disassembly hits ref,
    preferring a start right after a RET/RETI/LJMP."""
    best = None
    for back in range(0, maxback):
        s = ref - back
        if s < 0: break
        ins = disasm(d, 0, s, ref + 1, max_ins=200)
        hit = any(a == ref for a, _, _ in ins)
        if not hit: continue
        prev = d[s-1] if s > 0 else None
        score = (prev in (0x22, 0x32), back)
        if best is None or (score[0], -back) > (best[0], -best[1]):
            best = (score[0], back, s)
    return best

def show(name, img, bank, ref, span=0x90):
    d = img[bank*0x10000:(bank+1)*0x10000]
    al = align_back(d, ref)
    s = al[2] if al else ref - 0x40
    print('='*80)
    print(f'{name} bank{bank} ref {ref:04X} start {s:04X} (after ret={al[0] if al else None})')
    for a, raw, txt in disasm(d, 0, s, ref + span):
        mark = ' <== D05B' if a == ref else ''
        print(f'{a:04X}: {raw:<10} {txt}{mark}')

show('C48', D['C48'], 14, 0xB307)
show('RP', D['RP'], 14, 0x89FD)
