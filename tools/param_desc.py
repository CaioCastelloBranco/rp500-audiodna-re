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


import struct, re

RP = open(_P("rp_fw.bin"),'rb').read()
GSP = open(_P("gsp_fw.bin"),'rb').read()
RPB=[RP[k*0x10000:(k+1)*0x10000] for k in range(16)]
GSPB=[GSP[k*0x10000:(k+1)*0x10000] for k in range(16)]

def scan(name, banks, lo, hi):
    print("=== %s: 16-bit values pointing into name-table region 0x%X-0x%X ===" % (name,lo,hi))
    for k in range(16):
        b=banks[k]
        hits=[]
        for i in range(0,0x10000-1,2):
            v=struct.unpack_from('<H',b,i)[0]
            if lo<=v<hi:
                hits.append((i,v))
        # group runs
        groups=[];cur=[];last=None
        for off,v in hits:
            if last is not None and off==last+2: cur.append((off,v))
            else:
                if len(cur)>=4: groups.append(cur)
                cur=[(off,v)]
            last=off
        if len(cur)>=4: groups.append(cur)
        for g in groups[:8]:
            print("bank %d table 0x%04X len %d:"%(k,g[0][0],len(g)), [hex(v) for _,v in g[:40]])

scan("RP", RPB, 0xC600, 0xCA00)
scan("GSP", GSPB, 0xDE00, 0xE500)

# Determine record size of the name table and index of CAB_TYPE
def analyze_names(bank, start_hint, region_len=0x600):
    # find a long run of 18-byte records (string + NUL padding)
    for start in range(start_hint, start_hint+0x200):
        ok=0; names=[]
        for r in range(0, region_len, 0x12):
            rec=bank[start+r:start+r+0x12]
            s=rec.split(b'\x00')[0]
            if len(s)>=2 and all(32<=c<127 for c in s) and rec[len(s):]==b'\x00'*(0x12-len(s)):
                ok+=1; names.append(s.decode())
            else:
                break
        if ok>=10:
            print("record table at 0x%04X: %d records, first=%r last=%r" % (start, ok, names[0], names[-1]))
            for i,n in enumerate(names):
                if n in ("CAB_TYPE","AMP_TYPE","STOMP_TYPE","EQ_ONBY"):
                    print("   index %d = %s" % (i,n))
            return start, names
    return None,None

print("=== GSP name table ===")
gs,gn = analyze_names(GSPB[8], 0xDE00)
print("=== RP name table ===")
rs,rn = analyze_names(RPB[6], 0xC500)
