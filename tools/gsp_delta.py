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
v20=open(SH+r"\v20_res_51E18.bin",'rb').read()
exe=open(SH+r"\JUpdater Gsp1101vC63.exe",'rb').read()
pat=bytes.fromhex("ea806802307a5391")
i=exe.find(pat); B63=i
b63=b''.join(exe[B63+k*0x10008+8:B63+(k+1)*0x10008] for k in range(16))
b20=b''.join(v20[k*0x10000+8:(k+1)*0x10000] for k in range(16))

print("=== 32-byte block hash containment (is V20 shifted or rewritten?) ===")
def blockhashes(d,bs=32):
    return {d[i:i+bs] for i in range(0,len(d)-bs+1,bs)}
h63=blockhashes(b63); h20=blockhashes(b20)
inter=len(h20 & h63)
print("  V20 32B blocks:",len(h20)," vC63:",len(h63)," shared:",inter,
      " %.1f%% of V20"%(100*inter/max(1,len(h20))))

# rolling: for each 32-byte aligned V20 block, does it appear ANYWHERE in vC63 (byte-aligned)?
def contains_any(d,pat_set):
    return sum(1 for p in pat_set if d.find(p)>=0)
# sample 2000 blocks
blocks=list(h20)[:4000]
found=0
for p in blocks:
    if b63.find(p)>=0: found+=1
print("  of first %d distinct V20 blocks, found-in-vC63 at any offset: %d (%.1f%%)"%(
    len(blocks),found,100*found/max(1,len(blocks))))

print()
print("=== longest common substring between bank0s (rough) ===")
def lcs(a,b,minlen=16):
    best=b''
    # sample windows from a, extend
    step=1
    for i in range(0,len(a)-minlen,step):
        w=a[i:i+minlen]
        j=b.find(w)
        if j>=0:
            # extend
            k=minlen
            while i+k<len(a) and j+k<len(b) and a[i+k]==b[j+k]: k+=1
            if k>len(best): best=a[i:i+k]
    return best
lc=lcs(b20[:0x10000],b63[:0x10000])
print("  LCS bank0 len=%d  %r"%(len(lc),lc[:120]))

print()
print("=== C63-only strings in bank0 (user-cab upload code?) ===")
def strings(d,minlen=4):
    out=[];i=0
    while i<len(d):
        if 32<=d[i]<127:
            s=i
            while i<len(d) and 32<=d[i]<127: i+=1
            if i-s>=minlen: out.append((s,d[s:i].decode('ascii')))
        else: i+=1
    return out
s20={s for _,s in strings(b20[:0x10000])}
for off,s in strings(b63[:0x10000]):
    if s not in s20:
        print("   b0:%04X %r"%(off,s))

print()
print("=== 'USER %d' context in C63 bank0 ===")
k=b63.find(b'USER %d')
print("  off b0:%04X"%(k&0xFFFF))
s=max(0,k-96)
for a in range(s,k+128,16):
    c=b63[a:a+16]
    print("   %04X  %-47s %s"%(a&0xFFFF,c.hex(' '),''.join(chr(q) if 32<=q<127 else '.' for q in c)))

print()
print("=== large data blocks: compare entropy/zero density per 4KB page, both images ===")
import collections,math
def ent(b):
    if not b: return 0
    c=collections.Counter(b);n=len(b)
    return -sum((v/n)*math.log2(v/n) for v in c.values())
# find pages that are 'data-like' (low entropy, many non-FF) and differ
def pages(d):
    out=[]
    for o in range(0,len(d),0x1000):
        p=d[o:o+0x1000]
        if len(p)<0x1000: break
        out.append((o,ent(p),p.count(0xff)/len(p),p.count(0)/len(p)))
    return out
p20=pages(b20); p63=pages(b63)
print("  top 12 highest-entropy 4K pages vC63 (likely DSP/data payloads):")
for o,e,ff,z in sorted(p63,key=lambda x:-x[1])[:12]:
    print("    b%d:%04X ent=%.2f ff%%=%.2f zero%%=%.2f"%(o>>16,o&0xFFFF,e,100*ff,100*z))
print("  top 12 highest-entropy 4K pages V20:")
for o,e,ff,z in sorted(p20,key=lambda x:-x[1])[:12]:
    print("    b%d:%04X ent=%.2f ff%%=%.2f zero%%=%.2f"%(o>>16,o&0xFFFF,e,100*ff,100*z))
