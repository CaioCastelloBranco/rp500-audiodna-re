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


import collections, struct, re, os

GSP = open(_P("gsp1101_fw.bin"),'rb').read()
RP  = open(_P("rp500_fw.bin"),'rb').read()

FW = 0x19F8
BANKHDR = 8
BANKSZ = 0x10008
NB = 16

gsp_banks = [GSP[FW + k*BANKSZ + BANKHDR: FW + k*BANKSZ + BANKHDR + 0x10000] for k in range(NB)]
# sanity
for k,b in enumerate(gsp_banks):
    assert len(b) == 0x10000, (k,len(b))
print("GSP firmware: %d bytes, %d banks" % (NB*0x10000, NB))

# extract to files
open(_OUT("gsp_fw.bin"), "wb").write(b"".join(gsp_banks))
open(_OUT("rp_fw.bin"), "wb").write(RP)
print("wrote gsp_fw.bin / rp_fw.bin")

def ffspace(b):
    runs=[]; i=0; n=len(b)
    while i<n:
        if b[i]==0xff:
            j=i
            while j<n and b[j]==0xff: j+=1
            if j-i>=256: runs.append((i,j-i))
            i=j
        else: i+=1
    return runs

print("=== GSP per-bank 0xFF free space (runs >=256) ===")
tot_all=0
for k,b in enumerate(gsp_banks):
    runs=ffspace(b)
    tot=sum(l for _,l in runs)
    big=max([l for _,l in runs], default=0)
    tot_all+=tot
    print("bank %2d total=0x%05X (%6d) largest=0x%05X (%6d) runs=%d" % (k,tot,tot,big,big,len(runs)))
print("GSP total free = 0x%X (%d bytes)" % (tot_all, tot_all))

print("=== RP per-bank 0xFF free space (runs >=256) ===")
tot_all=0
for k in range(NB):
    b=RP[k*0x10000:(k+1)*0x10000]
    runs=ffspace(b)
    tot=sum(l for _,l in runs)
    big=max([l for _,l in runs], default=0)
    tot_all+=tot
    print("bank %2d total=0x%05X (%6d) largest=0x%05X (%6d) runs=%d" % (k,tot,tot,big,big,len(runs)))
print("RP total free = 0x%X (%d bytes)" % (tot_all, tot_all))

# ---------- string localization in GSP firmware ----------
def ascii_strings(data, minlen=4):
    out=[]; cur=bytearray(); start=0
    for i,c in enumerate(data):
        if 32 <= c <= 126:
            if not cur: start=i
            cur.append(c)
        else:
            if len(cur)>=minlen: out.append((start,cur.decode('ascii')))
            cur=bytearray()
    if len(cur)>=minlen: out.append((start,cur.decode('ascii')))
    return out

def locate(s, data):
    return [m.start() for m in re.finditer(re.escape(s.encode()), data)]

keys = ["GLOBAL CABINET","USER 1","USER 2","USER 10","USER_CAB %D","USER_CAB","FLASH_DATA: %D",
        "SEND PRESET","PROGRAM: %D","FLASH ERASE ERROR","FLASH WRITE ERROR","CABINET MODEL TO AMP",
        "CABINET TO AMP","USER AMP %D","CAB MODEL","CAB TYPE","CABINET"]
print("=== GSP key string locations (flat firmware offset) ===")
for s in keys:
    hits = locate(s, b"".join(gsp_banks))
    if not hits and s.startswith("USER ") and s[5:].isdigit():
        continue
    print("%-24s %s" % (s, [hex(h) for h in hits[:8]]))

print("=== USER n strings in GSP firmware ===")
for s in ["USER %d" % i for i in range(1,11)]:
    hits = locate(s, b"".join(gsp_banks))
    print("%-8s %s" % (s, [hex(h) for h in hits[:4]]))

# map flat offset -> (bank, offset within bank)
flat = b"".join(gsp_banks)
def bankof(off):
    return (off // 0x10000, off % 0x10000)

# dump context around USER 1 .. USER 10
hits = locate("USER 1", flat)
for h in hits[:3]:
    bk, bo = bankof(h)
    print("=== USER 1 at flat 0x%X bank %d offset 0x%X ===" % (h, bk, bo))
    a = bo
    for i in range(max(0,a-64), min(0x10000, a+320), 16):
        c = gsp_banks[bk][i:i+16]
        print("0x%04X  %-47s  %s" % (i, c.hex(' '), ''.join(chr(x) if 32<=x<127 else '.' for x in c)))

# find 0-terminated strings and the table structure around USER 10
print("=== raw dump 0x5000 around USER labels (bank5) ===")
# locate USER 1 in bank 5 if present
for bk in range(NB):
    idx = gsp_banks[bk].find(b"USER 1\x00")
    if idx >= 0:
        print("bank %d USER 1 at 0x%04X" % (bk, idx))
