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

def payload16(img):
    return b''.join(img[k*0x10008+8:k*0x10008+0x10008] for k in range(16))

c48 = payload16(open(_P("c48_fw.bin"),'rb').read())
c63 = payload16(open(_P("c63_fw.bin"),'rb').read())
v20 = open(_P("v20_res_51E18.bin"),'rb').read()

def scan(name, img):
    print('='*70)
    print(name)
    # DPTR loads
    for target in (0xD070, 0xE000, 0xD06E, 0xD020, 0xD05B, 0xD06D, 0xD06F):
        pat = bytes([0x90, target >> 8, target & 0xFF])
        offs = [i for i in range(len(img)-2) if img[i:i+3] == pat]
        banks = {}
        for o in offs:
            banks.setdefault(o // 0x10000, []).append(o % 0x10000)
        print(f'MOV DPTR,#{target:04X}: total {len(offs)}', {k: [hex(x) for x in v] for k, v in banks.items()})
    # immediate constants (mov r,#imm / mov dir,#imm or lcall args) - just count byte pairs
    for val in (0x0800, 0x07E7, 0x0080, 0x00D0):
        lo, hi = val & 0xFF, val >> 8
        # sequences with hi,lo (big endian) and lo,hi (little)
        be = sum(1 for i in range(len(img)-1) if img[i] == hi and img[i+1] == lo)
        le = sum(1 for i in range(len(img)-1) if img[i] == lo and img[i+1] == hi)
        print(f'const {val:04X}: BE-pair {be}, LE-pair {le}')
    # xrefs to important strings
    for s, addr in [(b'USER %d', None), (b'USER 1', None), (b'USER_CAB', None)]:
        offs = [m.start() for m in re.finditer(re.escape(s), img)]
        print(s, [hex(o) for o in offs])
        for o in offs:
            # search MOV DPTR,#addr within same bank (addr low 16 bits)
            a16 = o % 0x10000
            pat = bytes([0x90, a16 >> 8, a16 & 0xFF])
            bankstart = (o // 0x10000) * 0x10000
            xr = [hex(i - bankstart) for i in range(bankstart, bankstart + 0x10000 - 2) if img[i:i+3] == pat]
            print('   xref MOV DPTR', hex(a16), xr[:10])

scan('C48', c48)
scan('C63', c63)
