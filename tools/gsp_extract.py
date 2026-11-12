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
import collections, struct

gsp = open(_P("gsp1101_fw.bin"),'rb').read()
rp = open(_P("rp500_fw.bin"),'rb').read()

FW_START = 0xA00
BANK = 0x10008
print("gsp size 0x%X, fw start 0x%X, bank 0x%X, banks %d" % (len(gsp), FW_START, BANK, (len(gsp)-FW_START)//BANK))

def dump(data, off, n=64, tag=""):
    print("--- %s 0x%X ---" % (tag, off))
    for i in range(0, n, 16):
        c = data[off+i:off+i+16]
        print("0x%06X  %-47s  %s" % (off+i, c.hex(' '), ''.join(chr(b) if 32<=b<127 else '.' for b in c)))

print("=== gsp1101_fw.bin offsets 0x0-0xA40 ===")
dump(gsp, 0, 0x40, "fw-file head")
dump(gsp, FW_START, 0x40, "bank0 start")
dump(gsp, FW_START+0x1000, 0x80, "bank0 +0x1000")
dump(gsp, FW_START+0x22E3, 0x80, "bank0 NMLp")

print("=== per-bank headers ===")
for k in range((len(gsp)-FW_START)//BANK):
    off = FW_START + k*BANK
    print("bank %2d 0x%06X: %s" % (k, off, gsp[off:off+16].hex(' ')))

print("=== NMLp offsets in gsp ===")
i = 0
while True:
    j = gsp.find(b'NMLp', i)
    if j < 0: break
    print("0x%X (fw offset 0x%X, mod 0x10008 = 0x%X)" % (j, j-FW_START, (j-FW_START) % BANK))
    i = j+1

print("=== RP500 header in gsp? ===")
hdr = bytes.fromhex("ea0002006b5391df")
print("count", gsp.count(hdr), [hex(m) for m in [gsp.find(hdr)] if m>=0])
print("RP500 bank0 0x0-0x80:")
dump(rp, 0, 0x80, "rp500 bank0")
print("RP500 bank0 +0x1000:")
dump(rp, 0x1000, 0x80, "rp500 +1000")

# similarity: gsp bank0 payload vs rp bank0 at various shifts
b0 = gsp[FW_START:FW_START+BANK]
r0 = rp[0:0x10000]
print("=== similarity gsp bank0 vs rp500 bank0 at shifts ===")
for shift in [0, 0x8, 0x10, 0x100, 0x400, 0x800, 0x1000, 0x2000, 0x22E3-0x1051]:
    # compare gsp[shift:shift+0x10000] vs r0
    a = b0[shift:shift+0x10000]
    if len(a) < 0x10000: continue
    s = sum(x==y for x,y in zip(a,r0))/0x10000
    print("gsp +0x%X vs rp +0x0: %.4f" % (shift, s))

# cross-chunk mapping: find 16-byte chunks of rp in gsp bank0
print("=== rp500 bank0 16-byte chunks found in gsp bank0 (first 8KB) ===")
found = 0
for off in range(0, 0x2000, 16):
    idx = b0.find(r0[off:off+16])
    if idx >= 0:
        found += 1
        if found <= 20:
            print("rp 0x%04X -> gsp 0x%04X" % (off, idx))
print("found", found, "of", 0x2000//16)
