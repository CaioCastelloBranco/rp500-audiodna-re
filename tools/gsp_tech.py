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


import re, struct, collections

GSPF = open(_P("gsp_fw.bin"),'rb').read()
RP   = open(_P("rp_fw.bin"),'rb').read()
GSP = [GSPF[k*0x10000:(k+1)*0x10000] for k in range(16)]
RPB = [RP[k*0x10000:(k+1)*0x10000] for k in range(16)]

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

def gs(off, d, n=16):
    return d[off:off+n].hex(' ')

tech = ["SHARC","ADSP","Blackfin","AudioDNA","DNA","AL3201","AL3101","AL1201","Wavefront",
        "DSP","MOTOROLA","TMS","TMS320","Freescale","ARM","8051","C8051","PIC","Xilinx",
        "FPGA","CPLD","SRAM","SDRAM","DRAM","FLASH","EEPROM","I2C","SPI","UART","USB",
        "CODEC","ADC","DAC","AUDIO","SAMPLE","CONVOL","IMPULSE","FIR","IIR","TAP","COEFF"]
print("=== tech keyword hits in GSP firmware ===")
seen=set()
for off,s in strings(GSPF,4):
    up=s.upper()
    for k in tech:
        if k in up and (off,s) not in seen:
            seen.add((off,s))
            print("0x%06X %s" % (off, s[:120]))
            break
print("=== tech keyword hits in RP500 firmware ===")
seen=set()
for off,s in strings(RP,4):
    up=s.upper()
    for k in tech:
        if k in up and (off,s) not in seen:
            seen.add((off,s))
            print("0x%06X %s" % (off, s[:120]))
            break

print("=== GSP bank 15 strings 0x3300-0x3A00 ===")
for off,s in strings(GSP[15],4):
    if 0x3200 <= off < 0x3C00:
        print("0x%04X %r" % (off, s))

print("=== GSP bank 15 string list (all) ===")
for off,s in strings(GSP[15],4):
    print("0x%04X %r" % (off, s[:100]))
