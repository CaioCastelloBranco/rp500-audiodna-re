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


import struct

RP = open(_P("rp_fw.bin"),'rb').read()
GSP = open(_P("gsp_fw.bin"),'rb').read()
RPB=[RP[k*0x10000:(k+1)*0x10000] for k in range(16)]
GSPB=[GSP[k*0x10000:(k+1)*0x10000] for k in range(16)]

def dump(bank, off, n, tag):
    print("--- %s 0x%04X ---" % (tag, off))
    for i in range(off, off+n, 16):
        c=bank[i:i+16]
        print("0x%04X  %-47s  %s" % (i, c.hex(' '), ''.join(chr(x) if 32<=x<127 else '.' for x in c)))

print("=== RP bank4 0x3400-0x3620: cab name table + what follows ===")
dump(RPB[4], 0x3400, 0x220, "RP b4")

print("=== GSP bank11 0xD880-0xDB60: cab name table + what follows ===")
dump(GSPB[11], 0xD880, 0x2E0, "GSP b11")

print()
print("=== 16-bit little-endian constants equal to RP cab-table base 0x3486/0x3487 or GSP 0xD8C0/0xD8C1 ===")
for name,banks,targets in [("RP",RPB,[0x3486,0x3487,0x34a0]),("GSP",GSPB,[0xD8C0,0xD8C1,0xD8D0])]:
    for k in range(16):
        b=banks[k]
        for i in range(0,0x10000-1):
            v=b[i] | (b[i+1]<<8)
            if v in targets:
                print("%s bank %d: const 0x%04X at 0x%04X, prev bytes %s" % (name,k,v,i,b[max(0,i-4):i+4].hex(' ')))

print()
print("=== search region right after each cab table for 30-entry tables (stride 1,2,4) ===")
def table_scan(name, bank, start, length, stride):
    res=[]
    for off in range(start, start+length-stride*30, stride):
        vals=[]
        ok=True
        for j in range(30):
            if stride==1: v=bank[off+j]
            elif stride==2: v=struct.unpack_from('<H',bank,off+2*j)[0]
            else: v=struct.unpack_from('<I',bank,off+4*j)[0]
            vals.append(v)
        uniq=len(set(vals))
        if uniq>=8:
            res.append((off,uniq,vals[:6]))
    return res
for name,bank,start in [("RP",RPB[4],0x34C0),("GSP",GSPB[11],0xD960)]:
    for stride in (1,2,4):
        r=table_scan(name,bank,start,0x600,stride)
        print(name,"stride",stride,"candidates",[(hex(o),u,[hex(v) for v in s]) for o,u,s in r[:6]],"total",len(r))

print()
print("=== RP/GSP strings mentioning DSP / DNA / SDRAM / CAB / SPEAKER / IR ===")
def strings(data,minlen=4):
    out=[];cur=bytearray();start=0
    for i,c in enumerate(data):
        if 32<=c<=126:
            if not cur: start=i
            cur.append(c)
        else:
            if len(cur)>=minlen: out.append((start,cur.decode('ascii')))
            cur=bytearray()
    return out
for name,data in [("RP",RP),("GSP",GSP)]:
    print("----",name)
    for off,s in strings(data,4):
        u=s.upper()
        if any(w in u for w in ("DSP","DNA","SDRAM","COEFF","SPEAKER","IMPULSE","CONVOL")):
            print("0x%06X %r" % (off,s))
