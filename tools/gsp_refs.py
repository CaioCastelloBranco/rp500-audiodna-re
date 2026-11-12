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


import re, struct

GSP = [open(_P("gsp_fw.bin"),'rb').read()[k*0x10000:(k+1)*0x10000] for k in range(16)]
RP  = [open(_P("rp_fw.bin"),'rb').read()[k*0x10000:(k+1)*0x10000] for k in range(16)]

targets = {
    "SEND BLOCK":0x337F, "SEND PRESET":0x338A, "SEND AMP":0x3396,
    "BLOCK: %D":0x33D3, "PROGRAM: %D":0x33DD, "GLOBAL: %D":0x33E9,
    "USER AMP %D":0x33FB, "USER_CAB %D":0x3407, "MIDI ERROR":0x3413,
    "FLASH ERASE ERROR":0x3456, "FLASH WRITE ERROR":0x3468,
    "FLASH WRITE ERR %D":0x347A, "FLASH INIT SEC ERR":0x34AA,
    "FLASH BUSY":0x34E6, "VERSION":0x355C, "PRE DSP":0x3576,
    "POST DSP":0x357E, "PRE SAMPLE":0x3587, "FLASH_DATA":0x3592,
}
b = GSP[15]
print("=== references into bank15 string table (MOV DPTR #imm16 = 90 lo hi) ===")
for name,addr in targets.items():
    pat = bytes([0x90, addr & 0xFF, (addr>>8)&0xFF])
    hits = [m.start() for m in re.finditer(re.escape(pat), b)]
    # also plain 2-byte address anywhere (tables)
    pat2 = struct.pack('<H', addr)
    hits2 = [m.start() for m in re.finditer(re.escape(pat2), b)]
    print("%-20s 0x%04X  MOVDPTR:%s   addr16:%s" % (name, addr,
          [hex(h) for h in hits[:12]], [hex(h) for h in hits2[:12]]))

# Dump code around USER_CAB refs
def dump(bank, off, n=160, tag=""):
    print("--- %s bank15 0x%04X ---" % (tag, off))
    for i in range(max(0,off), min(0x10000,off+n), 16):
        c = bank[i:i+16]
        print("0x%04X  %-47s  %s" % (i, c.hex(' '), ''.join(chr(x) if 32<=x<127 else '.' for x in c)))

for name,addr in [("USER_CAB",0x3407),("FLASH_DATA",0x3592),("PROGRAM",0x33DD),("SEND BLOCK",0x337F)]:
    pat = bytes([0x90, addr & 0xFF, (addr>>8)&0xFF])
    for h in [m.start() for m in re.finditer(re.escape(pat), b)][:3]:
        dump(b, max(0,h-48), 192, name)
