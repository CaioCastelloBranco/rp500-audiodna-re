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


import re

UP = open(_P("JUpdater Gsp1101vC63.exe"),'rb').read()
GSPF = open(_P("gsp_fw.bin"),'rb').read()
RP = open(_P("rp_fw.bin"),'rb').read()

def ascii_strings(data, minlen=3):
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

def utf16(data, minlen=3):
    out=[]; i=0; n=len(data)
    while i<n-1:
        j=i; ch=[]
        while j<n-1 and 32<=data[j]<=126 and data[j+1]==0:
            ch.append(chr(data[j])); j+=2
        if len(ch)>=minlen:
            out.append((i,''.join(ch))); i=j
        else: i+=1
    return out

print("=== updater ASCII: DNA / AudioDNA / RP500 / target / device / product ===")
for off,s in ascii_strings(UP,4):
    low=s.lower()
    if any(k in low for k in ["audiodna","dna","rp500","rp 500","rp-500","gsp1101","gsp 1101","target","device id","product","usb vid","vid_","pid_"]):
        if len(s)<160: print("0x%06X %r" % (off,s))

print("=== updater wide: same ===")
for off,s in utf16(UP,3):
    low=s.lower()
    if any(k in low for k in ["audiodna","dna","rp500","rp 500","rp-500","gsp1101","gsp 1101","target","device id","product"]):
        if len(s)<160: print("0x%06X %r" % (off,s))

print("=== GSP firmware: 'AudioDNA' or 'DNA' context ===")
for m in re.finditer(rb'DNA', GSPF):
    print("0x%06X %r" % (m.start(), GSPF[m.start()-60:m.start()+60]))

print("=== RP firmware: 'RP500' product strings ===")
for off,s in ascii_strings(RP,4):
    if "rp" in s.lower() and ("500" in s or "RP 500" in s):
        print("0x%06X %r" % (off,s))

print("=== GSP product strings ===")
for off,s in ascii_strings(GSPF,4):
    if "gsp" in s.lower():
        print("0x%06X %r" % (off,s))
