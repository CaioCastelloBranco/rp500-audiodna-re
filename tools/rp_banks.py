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
import struct, collections, math

rp = open(_P("rp500_fw.bin"),'rb').read()
n = len(rp)
print("len/banks:", len(rp), len(rp)//0x10000)

def dump(off, n=64, tag=""):
    print("--- %s 0x%X ---" % (tag, off))
    for i in range(0, n, 16):
        c = rp[off+i:off+i+16]
        asc = ''.join(chr(b) if 32 <= b < 127 else '.' for b in c)
        print("0x%06X  %-47s  %s" % (off+i, c.hex(' '), asc))

print("=== start of each 64KB bank ===")
for bank in range(len(rp)//0x10000):
    off = bank*0x10000
    b = rp[off:off+16]
    print("bank %2d 0x%06X: %s" % (bank, off, b.hex(' ')))

print("=== bank 0 vector table 0x0000-0x0060 ===")
dump(0, 0x60, "bank0")

print("=== bank 1 start 0x10000-0x10040 ===")
dump(0x10000, 0x40, "bank1")

print("=== common code at 0x1051 in each bank ===")
for bank in range(len(rp)//0x10000):
    off = bank*0x10000 + 0x1051
    print("bank %2d 0x%06X: %s" % (bank, off, rp[off:off+16].hex(' ')))

print("=== 8051 opcode density per 64KB ===")
# count classic 8051 opcodes: 02 LJMP, 12 LCALL, 90 MOV DPTR, 75 MOV dir,#imm, E5 MOV A,dir, F0 MOVX @DPTR,A, E0 MOVX A,@DPTR
ops = [0x02,0x12,0x90,0x75,0xE5,0xF0,0xE0,0x74,0x24,0x25,0x33,0x93,0xA3,0x70,0x60,0x50,0x40,0x80,0xD5,0xD8,0xC2,0xD2,0xB2,0xA2,0x30,0x20,0x10,0x00]
for bank in range(len(rp)//0x10000):
    seg = rp[bank*0x10000:(bank+1)*0x10000]
    c = collections.Counter(seg)
    score = sum(c[o] for o in ops)/len(seg)
    print("bank %2d 0x%06X opcode-ish=%.3f  02=%5d 12=%5d 90=%5d 75=%5d E5=%5d E0=%5d F0=%5d" % (
        bank, bank*0x10000, score, c[0x02], c[0x12], c[0x90], c[0x75], c[0xE5], c[0xE0], c[0xF0]))
