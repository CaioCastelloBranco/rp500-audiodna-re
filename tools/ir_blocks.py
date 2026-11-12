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


import collections, math, struct

RP = open(_P("rp_fw.bin"),'rb').read()
GSP = open(_P("gsp_fw.bin"),'rb').read()

def ent(d):
    c=collections.Counter(d); n=len(d)
    return -sum((v/n)*math.log2(v/n) for v in c.values()) if n else 0

def blocks(data, win=256, thresh=6.0):
    # mark windows that are high-entropy and not mostly 0xFF or ASCII
    marks=[]
    for i in range(0, len(data)-win, win):
        w=data[i:i+win]
        if w.count(0xFF) > win*0.5: marks.append(0); continue
        if ent(w) < thresh: marks.append(0); continue
        # exclude ASCII-heavy
        asc=sum(1 for b in w if 32<=b<127)
        marks.append(1 if asc < win*0.85 else 0)
    runs=[];start=None
    for j,m in enumerate(marks):
        if m and start is None: start=j
        if (not m) and start is not None:
            a,b=start*win,j*win
            if b-a>=1024: runs.append((a,b))
            start=None
    if start is not None:
        a,b=start*win,len(data)
        if b-a>=1024: runs.append((a,b))
    return runs

for name,data in [("RP",RP),("GSP",GSP)]:
    print("==== %s high-entropy non-text runs >=1KB ====" % name)
    rs=blocks(data)
    print("count",len(rs),"total",sum(b-a for a,b in rs))
    for a,b in rs[:60]:
        w=data[a:a+64]
        print("  %06X-%06X len %6d  %s" % (a,b,b-a,w.hex(' ')))

print()
print("==== GSP: 30-record periodic structures in 0xD0000-0xE0000 ====")
# look for equal spacing between 0xFF gaps
region=GSP[0xD0000:0xE0000]
# split on runs of 0xFF >= 8
parts=[];cur=[];i=0
while i < len(region):
    if region[i]==0xFF and region[i:i+8]==b'\xff'*8:
        j=i
        while j<len(region) and region[j]==0xFF: j+=1
        if cur:
            s=len(cur)
            if s>=256: parts.append((0xD0000+i-s,s))
            cur=[]
        i=j
    else:
        cur.append(region[i]); i+=1
if len(cur)>=256: parts.append((0xD0000+len(region)-len(cur),len(cur)))
print("blocks>=256B after 0xFF gaps:", [(hex(a),l) for a,l in parts][:40], "total", len(parts))
if parts:
    print("length histogram:", collections.Counter(l for _,l in parts).most_common(10))

print()
print("==== GSP 0xDAE0-0xDC00 as 8-bit and 16-bit ====")
def dump(off,n):
    for i in range(off,off+n,16):
        c=GSP[i:i+16]
        print("0x%06X  %-47s  %s" % (i,c.hex(' '),''.join(chr(x) if 32<=x<127 else '.' for x in c)))
dump(0xDAE0,0x140)

print()
print("==== RP: any 0xFF-free region >= 4KB whose 16-bit values look like audio (zero-mean, bounded)? ====")
for k in range(16):
    b=RP[k*0x10000:(k+1)*0x10000]
    # longest non-FF run
    best=(0,0);start=None
    for i,v in enumerate(b):
        if v!=0xFF and start is None: start=i
        if v==0xFF and start is not None:
            if i-start>best[1]-best[0]: best=(start,i)
            start=None
    if start is not None and len(b)-start>best[1]-best[0]: best=(start,len(b))
    a,c=best
    if c-a>2048:
        seg=b[a:c]
        asc=sum(1 for x in seg if 32<=x<127)/len(seg)
        print("bank %2d longest non-FF 0x%04X-0x%04X len %d ent %.2f ascii %.2f" % (k,a,c,c-a,ent(seg),asc))
