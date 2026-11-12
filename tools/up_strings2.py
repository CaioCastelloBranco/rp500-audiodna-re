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
import re, struct

up = open(_P("JUpdater Gsp1101vC63.exe"),'rb').read()

def strings(data, minlen=4):
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

allstr = strings(up, 4)
kws = ["firmware","flash","boot","loader","update","upgrade","sysex","midi","codec",
       "hex","s19","srec","download","upload","program","verify","erase","device",
       "GSP","RP500","RP","cab","cabinet","impulse","convol","IR ","user cab","USER_CAB",
       "wav","aiff","sample rate","48k","44.1","preset","bundle","bin","dat","raw"]
exts = [".bin",".dat",".hex",".syx",".mid",".wav",".aif",".aiff",".gsp",".rp500",".fw",".img",".rom",".zip",".exe",".dll"]

print("=== keyword strings ===")
for off,s in allstr:
    low = s.lower()
    if any(k.lower() in low for k in kws):
        print("0x%06X %s" % (off, s[:160]))

print("=== extension strings ===")
for off,s in allstr:
    low = s.lower()
    if any(e in low for e in exts):
        print("0x%06X %s" % (off, s[:160]))

# PE resources
e_lfanew = struct.unpack_from('<I', up, 0x3C)[0]
num_sec = struct.unpack_from('<H', up, e_lfanew+6)[0]
opt_size = struct.unpack_from('<H', up, e_lfanew+20)[0]
sec_off = e_lfanew + 24 + opt_size
print("=== sections ===")
for i in range(num_sec):
    name = up[sec_off+i*40:sec_off+i*40+8].rstrip(b'\x00').decode('ascii','replace')
    vsize, vaddr, rawsize, rawoff = struct.unpack_from('<IIII', up, sec_off+i*40+8)
    print("%-8s VA=0x%08X VSize=0x%-8X raw=0x%-8X rawsize=0x%X" % (name,vaddr,vsize,rawoff,rawsize))

# resource dir entries (names)
print("=== .rsrc trees (types/names) ===")
# find .rsrc section
for i in range(num_sec):
    name = up[sec_off+i*40:sec_off+i*40+8].rstrip(b'\x00').decode('ascii','replace')
    if name == ".rsrc":
        vsize, vaddr, rawsize, rawoff = struct.unpack_from('<IIII', up, sec_off+i*40+8)
        base = rawoff
        # type entries
        n_named, n_id = struct.unpack_from('<HH', up, base+12)
        print("types:", n_named, n_id)
        for k in range(n_named+n_id):
            nm, off = struct.unpack_from('<II', up, base+16+k*8)
            print("  entry", k, "name/off=0x%X id=%d" % (nm, nm & 0x7fffffff))
        break
