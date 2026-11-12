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
SH=_FW
v20=open(SH+r"\v20_res_51E18.bin",'rb').read()
exe=open(SH+r"\JUpdater Gsp1101vC63.exe",'rb').read()
B=exe.find(bytes.fromhex("ea806802307a5391"))
b63=b''.join(exe[B+k*0x10008+8:B+(k+1)*0x10008] for k in range(16))
b20=b''.join(v20[k*0x10000+8:(k+1)*0x10000] for k in range(16))

def find_all(img,pat):
    out=[];i=0
    while True:
        j=img.find(pat,i)
        if j<0: break
        out.append(j); i=j+1
    return out

# code that loads DPTR with a given 16-bit address: 90 hi lo
def dptr_refs(img,addr):
    pat=bytes([0x90,(addr>>8)&0xFF,addr&0xFF])
    return find_all(img,pat)

print("=== references to key strings (MOV DPTR,#addr) in vC63 ===")
targets={
 "USER %d b0:BFF4":0xBFF4,
 "USER 1 b11:D9D8":0xBD9D8 & 0xFFFF,  # b11 -> linear? use bank-relative
}
# bank-qualified: linear offset in concatenated image
for name,lin in (("USER %d",0xBFF4),("USER 1 (b11)",0xBD9D8),("USER_CAB",None),("DIGISPKR",0xBD9C6)):
    if lin is None: continue
    refs=dptr_refs(b63,lin&0xFFFF)
    print("  %-16s lin=0x%X dptr-refs=%s"%(name,lin,['b%d:%04X'%(r>>16,r&0xFFFF) for r in refs[:10]]))

print()
print("=== 0xD070 / 0xE000 / 0xD06E refs per firmware ===")
for nm,img in (("V20",b20),("vC63",b63)):
    for a in (0xD070,0xE000,0xD06E):
        print("  %s 0x%04X refs=%d"%(nm,a,len(dptr_refs(img,a))))
    # also direct mov dptr patterns of 0xD070 with movx
    print()

print("=== C63 bank0: code around USER %d reference ===")
refs=dptr_refs(b63,0xBFF4)
print(" refs:",['b0:%04X'%(r&0xFFFF) for r in refs])
# dump code 96 bytes before first ref
if refs:
    r=refs[0]-32
    for a in range(r,r+160,16):
        c=b63[a:a+16]
        print("   %04X  %-47s"%(a&0xFFFF,c.hex(' ')))

print()
print("=== search for 0xD070 usage in C63 bank0 near user-cab region ===")
# any MOV DPTR,#D070 in bank0 and bank15
for bank in range(16):
    refs=[r for r in dptr_refs(b63,0xD070) if r>>16==bank]
    if refs: print("  b%d: %s"%(bank,['%04X'%(x&0xFFFF) for x in refs]))
