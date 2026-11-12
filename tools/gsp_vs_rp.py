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
import collections

gsp = open(_P("gsp1101_fw.bin"),'rb').read()
rp = open(_P("rp500_fw.bin"),'rb').read()

GSP_FW = 0x19F8
GSP_BANK = 0x10008
gsp_banks = []
for k in range(16):
    off = GSP_FW + k*GSP_BANK
    hdr = gsp[off:off+8]
    payload = gsp[off+8:off+8+0x10000]
    gsp_banks.append((hdr, payload, off))

print("=== GSP bank headers ===")
for k,(hdr,payload,off) in enumerate(gsp_banks):
    print("bank %2d off=0x%06X hdr=%s" % (k, off, hdr.hex(' ')))

rp_banks = [rp[k*0x10000:(k+1)*0x10000] for k in range(16)]

def chunks(b, size=16):
    return [b[i:i+size] for i in range(0, len(b)-size+1, size)]

gsp_chunks = [chunks(p) for _,p,_ in gsp_banks]
rp_chunks = [chunks(b) for b in rp_banks]
gsp_sets = [set(c) for c in gsp_chunks]
rp_sets = [set(c) for c in rp_chunks]

print("=== containment: GSP bank k chunks found in RP500 bank j ===")
for k in range(16):
    row = []
    for j in range(16):
        n = sum(1 for c in gsp_chunks[k] if c in rp_sets[j])
        row.append(n/len(gsp_chunks[k]))
    best = max(range(16), key=lambda j: row[j])
    print("GSP %2d -> RP best %2d (%.3f)  row: %s" % (k, best, row[best], " ".join("%.2f"%v for v in row)))

print("=== containment: RP500 bank j chunks found in GSP bank k (best) ===")
for j in range(16):
    row = []
    for k in range(16):
        n = sum(1 for c in rp_chunks[j] if c in gsp_sets[k])
        row.append(n/len(rp_chunks[j]))
    best = max(range(16), key=lambda k: row[k])
    print("RP %2d -> GSP best %2d (%.3f)" % (j, best, row[best]))

# byte similarity with small shifts for same-index banks
print("=== byte similarity GSP bank k payload vs RP bank k, shifts -16..16 ===")
for k in range(16):
    a = gsp_banks[k][1]; b = rp_banks[k]
    best = (0, None)
    for s in range(-16, 17):
        if s >= 0:
            av = a[s:]; bv = b[:len(av)]
        else:
            bv = b[-s:]; av = a[:len(bv)]
        n = min(len(av), len(bv))
        eq = sum(1 for i in range(0, n, 4) if av[i:i+4] == bv[i:i+4])
        score = eq/(n/4)
        if score > best[0]: best = (score, s)
    print("bank %2d best shift %+d similarity %.4f" % (k, best[1], best[0]))

# Dump first 64 bytes of GSP bank 0 payload and RP bank 0
print("GSP bank0 payload first 64:", gsp_banks[0][1][:64].hex(' '))
print("RP  bank0 first 64        :", rp_banks[0][:64].hex(' '))
