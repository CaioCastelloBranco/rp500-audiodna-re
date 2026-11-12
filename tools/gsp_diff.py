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
import hashlib

SH=_FW
v20fw=open(SH+r"\v20_res_51E18.bin",'rb').read()
fw63 =open(SH+r"\gsp1101_fw.bin",'rb').read()

# normalize banks
b20=[v20fw[k*0x10000+8:(k+1)*0x10000] for k in range(16)]           # 0xFFF8
b63=[fw63[0x1A00+k*0x10008:0x1A00+(k+1)*0x10008] for k in range(16)] # 0x10000

print("=== per-bank byte equality (V20[0:0xFFF8] vs vC63[0:0xFFF8]) ===")
tot_same=tot=0
for k in range(16):
    n=min(len(b20[k]),len(b63[k]))
    same=sum(1 for i in range(n) if b20[k][i]==b63[k][i])
    tot_same+=same; tot+=n
    print("  bank%2d  %5.1f%%  (n=0x%X)"%(k,100*same/n,n))
print("  TOTAL  %.1f%%"%(100*tot_same/tot))

KEYS=[b'CHAMP1X8',b'DLUX1X12',b'DIGISPKR',b'DIRECT',b'DREAD AC',b'JUMBO AC',
      b'USER 1',b'USER 2',b'USER_CAB',b'USER AMP',b'SEND BLOCK',b'BULK DUMP',
      b'FLASH_DATA',b'IMPULSE',b'CONVOL',b'CABINET',b'PRE DSP',b'POST DSP']
print()
print("=== key strings per firmware (whole image) ===")
print("  %-12s %6s %6s"%("string","V20","vC63"))
img20=b''.join(b20); img63=b''.join(b63)
for k in KEYS:
    print("  %-12s %6d %6d"%(k.decode('latin1'),img20.count(k),img63.count(k)))

print()
print("=== where is CHAMP1X8? ===")
for nm,img in (("V20",img20),("vC63",img63)):
    h=[];i=0
    while True:
        j=img.find(b'CHAMP1X8',i)
        if j<0: break
        h.append(j); i=j+1
    print("  %s: %s"%(nm,[('b%d:%04X'%(x>>16,x&0xFFFF)) for x in h]))

print()
print("=== bank15 service strings diff (present only in vC63) ===")
def strings(d,minlen=4):
    out=[];i=0
    while i<len(d):
        if 32<=d[i]<127:
            s=i
            while i<len(d) and 32<=d[i]<127: i+=1
            if i-s>=minlen: out.append(d[s:i].decode('ascii'))
        else: i+=1
    return out
s20=set(strings(b20[15])); s63=set(strings(b63[15]))
print("  V20-only:", sorted(s20-s63)[:60])
print("  vC63-only:", sorted(s63-s20)[:60])
