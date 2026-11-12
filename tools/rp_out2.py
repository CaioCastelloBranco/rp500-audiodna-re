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


RP=open(_P("rp_fw.bin"),'rb').read()
BANKS=[RP[k*0x10000:(k+1)*0x10000] for k in range(16)]
B4=BANKS[4]

def cstr(bank,off,maxn=32):
    out=[]
    for i in range(off,min(off+maxn,len(bank))):
        if bank[i]==0: break
        out.append(chr(bank[i]) if 32<=bank[i]<127 else '?')
    return ''.join(out)

print("=== CAB enum @0x478C, 28 entries, with index ===")
for n in range(28):
    p=(B4[0x478C+n*2]<<8)|B4[0x478C+n*2+1]
    print("  %2d  ptr=0x%04X  %r"%(n,p,cstr(B4,p,20)))

print()
print("=== AMP enum @0x46B6 first/last ===")
for n in range(53):
    p=(B4[0x46B6+n*2]<<8)|B4[0x46B6+n*2+1]
    if n<4 or n>=50:
        print("  %2d  ptr=0x%04X  %r"%(n,p,cstr(B4,p,20)))
    elif n==4:
        print("  ...")

print()
print("=== search for codec / converter / analog-switch related strings ===")
needles=[b'CODEC',b'DAC',b'ADC',b'AK4',b'CS4',b'WM8',b'AIC',b'I2C',b'I2S',b'SPI',
         b'RELAY',b'MUTE',b'BAL',b'XLR',b'PHANTOM',b'MONO',b'STEREO',
         b'CABSIM',b'CAB SIM',b'SPKR',b'SPEAKER',b'MIC',b'LINE']
for nd in needles:
    hits=[]; i=0
    while True:
        j=RP.find(nd,i)
        if j<0: break
        hits.append(j); i=j+1
    print("  %-9s n=%d  %s"%(nd.decode('latin1'),len(hits),
        [('b%d:%04X'%(h>>16,h&0xFFFF)) for h in hits[:10]]))

print()
print("=== any per-cab numeric tables? pointer-ish arrays in 0x4700-0x4800 ===")
for a in range(0x46F0,0x47A0,2):
    v=(B4[a]<<8)|B4[a+1]
    tag=''
    if 0x2600<=v<0x3700: tag=cstr(B4,v,14)
    print("  %04X: %04X %s"%(a,v,tag))
