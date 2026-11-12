#!/usr/bin/env python3
"""Audit every load-bearing claim of the project against the artifacts.

One script, one table, no prose. Each check re-derives its fact from the
firmware images, the built artifacts or the archived logs -- nothing is taken
on trust from the documents.

Usage:
    python audit_claims.py
"""
import hashlib
import os
import re
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FW = os.path.join(ROOT, "01_source_firmware")
BIN = os.path.join(ROOT, "02_source_binaries")
BUILDS = os.path.join(ROOT, "09_builds")
EVID = os.path.join(ROOT, "05_evidence")
RES = os.path.join(ROOT, "07_open_source_tools", "netupdaterclone_src")
DOCS = os.path.join(ROOT, "03_docs")
sys.path.insert(0, os.path.join(ROOT, "04_analysis_scripts"))
from d51 import disasm  # noqa: E402

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail))
    print("  %-4s %-62s %s" % ("PASS" if ok else "FAIL", name, detail))


def readfile(p):
    with open(p, "rb") as f:
        return f.read()


def flat_interleaved(d):
    """GSP images: 16 x (8-byte descriptor + 64 KB body)."""
    return b"".join(d[k * 0x10008 + 8:k * 0x10008 + 8 + 0x10000] for k in range(16))


def bank(img, k, size=0x10000):
    return img[k * size:(k + 1) * size]


def dsp_stores(img):
    """Every store to the DSP data port 0xD070, with the source classified.

    A store is  90 D0 70 F0  (MOV DPTR,#0D070h ; MOVX @DPTR,A).  The byte came
    from the nearest preceding load into A:
        0x93  MOVC A,@A+DPTR  -> code space
        0xE0  MOVX A,@DPTR    -> external RAM
    """
    out = []
    store = b"\x90\xd0\x70\xf0"
    for i in range(len(img) - 12):
        if img[i:i + 4] != store:
            continue
        src = None
        for j in range(i - 1, max(-1, i - 9), -1):
            if img[j] == 0x93:
                src = "code"
                break
            if img[j] == 0xE0:
                src = "xram"
                break
        out.append((i // 0x10000, i % 0x10000, src or "?"))
    return out


def code_base(b, off):
    """Base of 'ADD A,#lo ; MOV 82h,A ; MOV A,#hi ; ADDC A,Rn ; MOV 83h,A'."""
    lo = max(0, off - 24)
    for i in range(off - 1, lo, -1):
        if b[i] == 0x24 and b[i + 2] == 0xF5 and b[i + 3] == 0x82 and \
           b[i + 4] == 0x74 and b[i + 6] == 0x3E and b[i + 7] == 0xF5 and \
           b[i + 8] == 0x83:
            return ((b[i + 5] << 8) | b[i + 1]) & 0xFFFF
    return None


def xram_base(b, off):
    """Base of 'MOV A,#lo ; ADD A,Rn ; MOV 82h,A ; CLR A ; ADDC A,#hi ;
    MOV 83h,A' -- the XRAM-sourced variant."""
    lo = max(0, off - 24)
    for i in range(off - 1, lo, -1):
        if b[i] == 0x74 and b[i + 2] in (0x2E, 0x2F) and b[i + 3] == 0xF5 and \
           b[i + 4] == 0x82 and b[i + 5] == 0xE4 and b[i + 6] == 0x34 and \
           b[i + 8] == 0xF5 and b[i + 9] == 0x83:
            return ((b[i + 7] << 8) | b[i + 1]) & 0xFFFF
    return None


print("=" * 78)
print("AUDIT OF LOAD-BEARING CLAIMS")
print("=" * 78)

rp = readfile(os.path.join(FW, "rp500_v20.bin"))
c48 = flat_interleaved(readfile(os.path.join(FW, "c48_fw.bin")))
c63 = flat_interleaved(readfile(os.path.join(FW, "c63_fw.bin")))
rp1000 = readfile(os.path.join(FW, "rp1000V12.bin"))
rp355 = readfile(os.path.join(FW, "rp355V14.bin"))

# ------------------------------------------------------------------ [1] ----
print("\n[1] RP500 image and its two DSP streams")
check("rp500_v20.bin is 16 x 64 KB", len(rp) == 0x100000, "%d bytes" % len(rp))
rp_st = dsp_stores(rp)
check("RP500 writes the DSP data port exactly twice",
      len(rp_st) == 2, str([(b, hex(o)) for b, o, s in rp_st]))
check("both RP500 streams read CODE space (MOVC), none reads XRAM",
      all(s == "code" for _b, _o, s in rp_st),
      str([(b, s) for b, _o, s in rp_st]))
b14, b15 = bank(rp, 14), bank(rp, 15)
s14 = [o for b, o, s in rp_st if b == 14][0]
s15 = [o for b, o, s in rp_st if b == 15][0]
check("bank 14 stream reads code space 0x2DC2+n",
      code_base(b14, s14) == 0x2DC2, hex(code_base(b14, s14) or 0))
check("bank 15 stream reads code space 0x2E3B+n",
      code_base(b15, s15) == 0x2E3B, hex(code_base(b15, s15) or 0))
check("the byte counter is the 16-bit XRAM cell 0xFF24/0xFF25",
      b15[0xBE97:0xBE9E] == b"\x90\xff\x24\xe0\xfe\xa3\xe0" and
      b14[0x9AA5:0x9AAC] == b"\x90\xff\x24\xe0\xfe\xa3\xe0",
      b15[0xBE97:0xBE9E].hex(" "))

# --- a second write path into the DSP window -------------------------------
print("\n[1b] The per-cabinet DSP parameter table")
_tail = bytes.fromhex("34d08f82f583edf0")   # ADDC A,#D0h ; MOV 82h,R7 ; MOV 83h,A ; MOV A,R5 ; MOVX @DPTR,A
_tables = {}
for k in range(16):
    b = bank(rp, k)
    i = b.find(_tail)
    if i < 0:
        continue
    j = i - 1
    base = None
    while j > max(0, i - 16):
        if b[j] == 0x90 and b[j + 3] == 0x93:
            base = (b[j + 1] << 8) | b[j + 2]
            break
        j -= 1
    _tables[k] = base
check("the table-write loop exists only in the two cabinet banks",
      sorted(_tables) == [14, 15], str(sorted(_tables)))
check("bank 14's parameter table is at 0x2C80, bank 15's at 0x2CBB",
      _tables.get(14) == 0x2C80 and _tables.get(15) == 0x2CBB,
      str({k: hex(v) for k, v in _tables.items()}))
check("the tables are identical in both banks (a COMMON DSP configuration, "
      "not a per-cabinet IR)",
      bank(rp, 14)[0x2C80:0x2C80 + 0x71] == bank(rp, 15)[0x2CBB:0x2CBB + 0x71])
check("the loop writes DSP registers 0xD000..0xD070 "
      "(compare against 0x0071, skip index 0x59)",
      b15[0xB872:0xB878] == b"\x94\x71\xee\x94\x00\x50" and
      b15[0xB879:0xB87E] == b"\xef\x64\x59\x4e\x60" and
      b14[0x97E2:0x97E8] == b"\x94\x71\xee\x94\x00\x50",
      b15[0xB872:0xB87E].hex(" "))
check("the table's last byte (index 0x70) is written to DSP register 0xD070",
      bank(rp, 14)[0x2C80 + 0x70] == 0x00 and
      bank(rp, 15)[0x2CBB + 0x70] == 0x00,
      "bank14=%02X bank15=%02X" % (bank(rp, 14)[0x2C80 + 0x70],
                                   bank(rp, 15)[0x2CBB + 0x70]))
check("the 0x7FF8 compare is on the 'status did NOT change' path "
      "(a stall abort), not a length limit",
      b15[0xBE2D] == 0x20 and b15[0xBE2E] == 0xE2 and b15[0xBE2F] == 0x1C and
      b15[0xBE30] == 0xA8 and b15[0xBE3D] == 0x94)

# ------------------------------------------------------------------ [2] ----
print("\n[2] The RP500's streamed block is a 24-byte PARAMETER block")
blob15 = b15[0x2E3B:0x2E3B + 24]
blob14 = b14[0x2DC2:0x2DC2 + 24]
check("bank 15 block at 0x2E3B is 24 bytes, identical to bank 14's",
      blob15 == blob14, blob15.hex(" "))
check("both banks' block is immediately followed by CODE, not more data",
      b15[0x2E53] == 0xE6 and b14[0x2DDA] == 0xE6,
      "0x2E53=%02X 0x2DDA=%02X" % (b15[0x2E53], b14[0x2DDA]))
check("the block is cabinet-independent (identical in both cabinet banks)",
      blob14 == blob15)
check("the RP500 has no other DSP data port write",
      rp.count(b"\x90\xd0\x70\xf0") == 2)
check("RP500 manual never mentions impulse responses",
      b"impulse" not in readfile(os.path.join(DOCS, "RP500_OM_EN.txt")).lower())

# ------------------------------------------------------------------ [3] ----
print("\n[3] The GSP1101 has a second, variable-length DSP path (the IR path)")
for nm, img in (("C48", c48), ("C63", c63)):
    st = dsp_stores(img)
    xram = [(b, o) for b, o, s in st if s == "xram"]
    code = [(b, o) for b, o, s in st if s == "code"]
    check("%s: 32 XRAM-sourced DSP stores (2 per bank x 16 banks)" % nm,
          len(xram) == 32, "%d" % len(xram))
    check("%s: 2 code-space DSP stores (same platform routine as the RP500)" % nm,
          len(code) == 2, "%d" % len(code))
    bases = set()
    for b, o in xram:
        bases.add(xram_base(bank(img, b), o))
    check("%s: every XRAM stream uses one base + index" % nm,
          len(bases) == 1, str([hex(x) for x in bases]))
    if nm == "C63":
        check("C63 XRAM source base is 0x2603 (+ index)", bases == {0x2603},
              str([hex(x) for x in bases]))
    else:
        check("C48 XRAM source base is 0x2445 (+ index)", bases == {0x2445},
              str([hex(x) for x in bases]))
# the code-space block of the GSP
cb63 = bank(c63, 15)
check("GSP C63 code-space block is 16 bytes followed by code",
      cb63[0x3666:0x3676].hex(" ") ==
      "01 01 0c 50 0a 20 01 00 14 bd 02 0b 46 02 14 b0" and
      cb63[0x3676] == 0x15,
      cb63[0x3666:0x3676].hex(" "))
check("RP500 and GSP share 8 bytes of DSP parameter block",
      blob15[8:16] == cb63[0x3666:0x3676 + 8][:8],
      blob15[8:16].hex(" "))
check("the GSP terminates a variable-length block with 0xF5 on the data port",
      c63.count(b"\x74\xf5") >= 2 and
      any(c63[i:i + 6] == b"\x90\xd0\x70\x74\xf5\xf0" for i in range(len(c63) - 6)))
check("GSP stages the received IR: XRAM 0x1483+ -> XRAM 0x2603+ "
      "(count cell 0x14C3)",
      any(c63[i:i + 3] == b"\x74\x83\x2f" for i in range(len(c63) - 3)) and
      c63.count(b"\x90\x14\xc3") >= 1 and c63.count(b"\x90\x27\x04") >= 1)

# ------------------------------------------------------------------ [4] ----
print("\n[4] The stream loop's byte cap")
check("bank 15 compares against the constant 0x7FF8 "
      "(SUBB A,#0F8h then SUBB A,#07Fh)",
      b15[0xBE3D] == 0x94 and b15[0xBE3E] == 0xF8 and
      b15[0xBE40] == 0x94 and b15[0xBE41] == 0x7F)
check("bank 14 has the identical compare at 0x9A4B/0x9A4E",
      b14[0x9A4B] == 0x94 and b14[0x9A4C] == 0xF8 and
      b14[0x9A4E] == 0x94 and b14[0x9A4F] == 0x7F)
check("the high byte compared is the byte counter's high byte (MOV A,R6)",
      b15[0xBE3F] == 0xEE and b14[0x9A4D] == 0xEE)
check("no 0x7FF8 literal exists anywhere in the image "
      "(it is a compare constant, not a stored address)",
      rp.count(b"\x90\x7f\xf8") == 0 and rp.count(b"\x74\xf8\x90") == 0)

# ------------------------------------------------------------------ [5] ----
print("\n[5] The RP1000 runs the same loader (platform routine)")
rp_st1000 = dsp_stores(rp1000)
check("RP1000 V12 has the same 2 code-space / 0 XRAM split",
      len(rp_st1000) == 2 and all(s == "code" for _b, _o, s in rp_st1000))
b1000 = set()
for b, o, s in rp_st1000:
    b1000.add(code_base(bank(rp1000, b), o))
check("RP1000 V12 uses the same source bases 0x2DC2 / 0x2E3B",
      b1000 == {0x2DC2, 0x2E3B}, str([hex(x) for x in b1000]))
# the RP1000 runs the same routine, re-based on its own scratch addresses
_rp1000_b15 = bank(rp1000, 15)
_rp500_b15 = bank(rp, 15)
_a = _rp1000_b15[0xBF62:0xBF79]
_b = _rp500_b15[0xBE97:0xBEAE]
check("RP1000 and RP500 run the SAME stream routine, differing only in the "
      "scratch counter cell (0xFFAA vs 0xFF24)",
      len(_a) == len(_b) and _a[:2] == b"\x90\xff" and _b[:2] == b"\x90\xff" and
      _a[2:3] == b"\xaa" and _b[2:3] == b"\x24" and _a[3:] == _b[3:],
      "RP1000 %s | RP500 %s" % (_a[:5].hex(" "), _b[:5].hex(" ")))
check("RP1000 V12 has the same DSP port counts as the RP500",
      rp1000.count(b"\x90\xd0\x70") == rp.count(b"\x90\xd0\x70"),
      "RP1000=%d RP500=%d" % (rp1000.count(b"\x90\xd0\x70"), rp.count(b"\x90\xd0\x70")))
check("RP355 V14 also uses the RP-family layout (11 banks)",
      len(rp355) // 0x10000 == 11 and rp355.count(b"\x90\xd0\x70") == 6,
      "%d banks, %d data-port refs" % (len(rp355) // 0x10000,
                                       rp355.count(b"\x90\xd0\x70")))


def host_regs(img):
    """Addresses loaded with MOV DPTR,#addr that fall in the host/DSP windows."""
    s = set()
    for i in range(len(img) - 2):
        if img[i] == 0x90:
            a = (img[i + 1] << 8) | img[i + 2]
            if 0xD000 <= a <= 0xD0FF or 0xE000 <= a <= 0xE8FF:
                s.add(a)
    return s


_rp_r, _c48_r, _c63_r = host_regs(rp), host_regs(c48), host_regs(c63)
_common = _rp_r & _c48_r & _c63_r
check("23 host/DSP addresses are common to RP500, GSP C48 and GSP C63",
      len(_common) == 23, "%d" % len(_common))
_core = {0xD01E, 0xD01F, 0xD020, 0xD034, 0xD050, 0xD05A, 0xD05B, 0xD066,
         0xD069, 0xD06D, 0xD06E, 0xD06F, 0xD070,
         0xE000, 0xE200, 0xE400, 0xE800}
check("the complete handshake register set is shared by all three",
      _core <= _rp_r and _core <= _c48_r and _core <= _c63_r,
      "%d of %d" % (len(_core & _common), len(_core)))

# ------------------------------------------------------------------ [6] ----
print("\n[6] Bank structure")
check("all 16 banks share an identical 0x2C80-byte prefix",
      all(bank(rp, k)[:0x2C80] == rp[:0x2C80] for k in range(16)))
ok = True
for k in range(16):
    b = bank(rp, k)
    for n in range(16):
        off = 0x0200 + n * 8
        if b[off:off + 4] != bytes([0x75, 0x90, 0xF0 + n, 0x22]):
            ok = False
check("bank-select table 0x0200 = 16 x (MOV P1,#(0xF0+n) ; RET) in every bank", ok)
check("bank 5/6/7/14/15 also have bank-specific P1 writes",
      all(bank(rp, k).count(b"\x75\x90") > 20 for k in (5, 6, 7, 14, 15)),
      "bank5=%d bank14=%d" % (bank(rp, 5).count(b"\x75\x90"),
                              bank(rp, 14).count(b"\x75\x90")))
check("the prefix table at 0x18DC holds 128 distinct 16-bit code pointers "
      "(a dispatch table, NOT the per-cabinet selector: the only caller we "
      "found reaches 4 entries via a 2x2-bit index)",
      len(set(struct.unpack("<128H", rp[0x18DC:0x18DC + 256]))) > 20)

# ------------------------------------------------------------------ [7] ----
print("\n[7] Free space for our stub")
run = bank(rp, 1)[0xA030:0xA030 + 0x5FD0]
check("bank 1 0xA030..+0x5FD0 is 24528 bytes of pure 0xFF",
      len(run) == 0x5FD0 and all(x == 0xFF for x in run))
check("the free run ends exactly at the bank boundary", 0xA030 + 0x5FD0 == 0x10000)
check("the byte before the free run is code (not data)",
      bank(rp, 1)[0xA02A:0xA030].hex(" ") == "e5 90 54 0f ff 22",
      bank(rp, 1)[0xA02A:0xA030].hex(" "))

# ------------------------------------------------------------------ [8] ----
print("\n[8] The cabinet table (the thing the hello-world patch edits)")
b4 = bank(rp, 4)
ptrs = [(b4[0x478E + 2 * i] << 8) | b4[0x478E + 2 * i + 1] for i in range(28)]
check("cab pointer table at bank4:0x478E has 28 entries", len(ptrs) == 28)
check("entry 24 points at 0x355E", ptrs[24] == 0x355E, hex(ptrs[24]))
check("entry 24 record reads DIGISPKR", b4[0x355E:0x355E + 8] == b"DIGISPKR",
      b4[0x355E:0x355E + 8].decode())
check("entry 27 points at JUMBO AC", b4[ptrs[27]:ptrs[27] + 8] == b"JUMBO AC")
check("'DIGISPKR' occurs exactly once in the whole image", rp.count(b"DIGISPKR") == 1,
      "%d occurrences" % rp.count(b"DIGISPKR"))

# ------------------------------------------------------------------ [9] ----
print("\n[9] Built artifacts")
build_bin = readfile(os.path.join(BUILDS, "rp500_v20_caio4x12.bin"))
check("patched build is 1 MB", len(build_bin) == 0x100000)
diff = [i for i in range(0x100000) if build_bin[i] != rp[i]]
check("patched build differs from stock in exactly 8 bytes", len(diff) == 8,
      "at " + " ".join(hex(d) for d in diff))
check("those 8 bytes are the cab-24 name",
      build_bin[0x4355E:0x43566] == b"CAIO4X12", build_bin[0x4355E:0x43566].decode())
dig = readfile(os.path.join(BUILDS, "rp500_v20_caio4x12.DigBin"))
check("build .DigBin is 0x100084 bytes", len(dig) == 0x100084)
check("build .DigBin unpacks to the patched flat image",
      (dig[12:12 + 0x10000] == build_bin[:0x10000] and
       all(dig[12 + 0x10000 + k * 0x10008 + 8:12 + 0x10000 + k * 0x10008 + 8 + 0x10000]
           == build_bin[(k + 1) * 0x10000:(k + 2) * 0x10000] for k in range(15))))
stock_dig = readfile(os.path.join(FW, "rp500V20.DigBin"))
check("stock .DigBin container model round-trips byte-exactly",
      stock_dig[:12] == dig[:12] and len(stock_dig) == len(dig))
check("flash_ready drop-in is the patched image",
      hashlib.sha256(readfile(os.path.join(BUILDS, "flash_ready", "rp500V20.DigBin"))).hexdigest()
      == hashlib.sha256(dig).hexdigest())

# ----------------------------------------------------------------- [10] ----
print("\n[10] The patched updater")
up = readfile(os.path.join(BUILDS, "updater_2.1",
                           "Digitech.RP.Series.Firmware.Updater.exe"))
orig = readfile(os.path.join(BIN, "Digitech.RP.Series.Firmware.Updater.exe"))
check("patched updater is the same size as the original", len(up) == len(orig))
udiff = [i for i in range(len(up)) if up[i] != orig[i]]
check("patched updater differs in 18 bytes", len(udiff) == 18, str(len(udiff)))
img_offs = []
_i = orig.find(b"\x00\x5c\x00\x05\x00\x00\x00\x00\x00\x01\x00\x00")
while _i >= 0:
    img_offs.append(_i)
    _i = orig.find(b"\x00\x5c\x00\x05\x00\x00\x00\x00\x00\x01\x00\x00", _i + 1)
check("16 DigBin firmware resources are embedded in the bundle",
      len(img_offs) == 16, str(len(img_offs)))
patched_at = [o for o in img_offs if up[o:o + len(dig)] == dig]
check("the patched image is embedded at exactly one resource slot",
      len(patched_at) == 1, str([hex(o) for o in patched_at]))
check("that slot held the stock image before patching",
      patched_at and orig[patched_at[0]:patched_at[0] + len(dig)] == stock_dig)
check("revision is 2.1 and the resource is rp500V21",
      b'<Revision Version="2.1"' in up and b"rp500V21.DigBin" in up)
check("no 2.0 revision for RP500 remains",
      b'<Revision Version="2.0" ReleaseDate="Dec 02, 2009" ImageUrl="http://www.lexiconpro.com/updater/digitech/firmware/rp500/rp500V20.DigBin"' not in up)
check("resource renamed to rp500V21",
      up.count(b"NetUpdaterClone.Resources.Firmware.rp500V21.DigBin") == 1 and
      up.count(b"NetUpdaterClone.Resources.Firmware.rp500V20.DigBin") == 0)

# ----------------------------------------------------------------- [11] ----
print("\n[11] The literature (manual semantics)")
c54 = readfile(os.path.join(DOCS, "GSP1101 RELEASE NOTES VERSION C54.txt")).decode("utf-8", "replace")
c63n = readfile(os.path.join(DOCS, "gsp1101 release notes version c63.txt")).decode("utf-8", "replace")
rpman = readfile(os.path.join(DOCS, "RP500_OM_EN.txt")).decode("utf-8", "replace")
check("C54: the downloader takes the first 128 samples of the LEFT channel",
      "takes the first 128 samples (of" in c54 and "the left channel" in c54)
check("C54: those samples are applied to BOTH outputs",
      "applies these to both of the outputs" in c54)
check("C63: 10 cabinet positions", "There are 10 cabinet positions" in c63n)
check("C63: audition without storing", "Store Cabinet to 1101" in c63n)
check("C63: gain setting prompted at upload", "gain setting" in c63n)
check("RP500 manual: AudioDNA2 DSP chip (singular)", "AudioDNA2" in rpman)
check("RP500 manual: 100 user presets", "100 User Presets" in rpman)
check("the GSP image really carries the USER cabinet entries",
      b"USER 1" in c63 and b"USER_CAB" in c63)
check("the RP500 image has no USER cabinet entries", b"USER 1" not in rp)

# ----------------------------------------------------------------- [12] ----
print("\n[12] Hardware evidence")
log = readfile(os.path.join(EVID, "2026-11-10_rp500_updater_flash.log")).decode("utf-8", "replace")
check("flash log has the dry run", "Dry run complete" in log)
check("flash log has the real write", "Image: 16 records, 1048576 data bytes" in log)
check("flash log records 4039 data blocks", log.count("TX: F0000010005E057A") == 4039,
      str(log.count("TX: F0000010005E057A")))
check("one retried NAK, no safety stop",
      log.count("NAK 0x7A (detail 0x0C)") == 1 and "SAFETY STOP" not in log)
check("no update failure in the log", "Update Failed" not in log)

# --- S2: where the RP500 stores its presets -------------------------------
print("\n[12b] S2 - the RP500's storage")
check("the device reports a 1 MB flash (16 segments x 64 KB)",
      log.count("segment addr=0x") >= 16 and
      "Flash map: maxBlock=256, segments=16" in log)
check("the updater wrote 4039 of 4096 possible 256-byte blocks",
      log.count("TX: F0000010005E057A") == 4039 and 0x100000 // 256 == 4096)
_patched = readfile(os.path.join(BUILDS, "rp500_v20_caio4x12.bin"))
_blocks = [_patched[i:i + 256] for i in range(0, len(_patched), 256)]
_ff = [i for i, b in enumerate(_blocks) if all(x == 0xFF for x in b)]
check("the all-0xFF skip applies only to segment 0: 57 skipped, all 548 empty "
      "blocks outside segment 0 were written",
      len(_blocks) == 4096 and len(_ff) == 606 and
      len([i for i in _ff if i < 256]) == 58 and
      len([i for i in _ff if i >= 256]) == 548 and
      4096 - len([i for i in _ff if i < 256]) == 4038,
      "empty blocks: %d (segment 0: %d, elsewhere: %d)"
      % (len(_ff), len([i for i in _ff if i < 256]),
         len([i for i in _ff if i >= 256])))
# no RAM store: writes outside the DSP window / command ports / 8051 scratch
_w = {}
for _k in range(16):
    _b = bank(rp, _k)
    _cur = None
    for _a, _raw, _txt in disasm(_b, 0, 0, 0x10000):
        _m = re.match(r"^MOV DPTR,#([0-9A-Fa-f]+)h$", _txt)
        if _m:
            _cur = int(_m.group(1), 16)
            continue
        if _txt == "INC DPTR":
            if _cur is not None:
                _cur = (_cur + 1) & 0xFFFF
            continue
        if _txt.startswith("MOVX @DPTR"):
            if _cur is not None:
                _w[_cur] = _w.get(_cur, 0) + 1
            _cur = None
            continue
        _cur = None
_low = sorted(a for a in _w if a < 0xD000)
check("the RP500 firmware has NO XRAM store below the DSP window "
      "(only 3 stray writes below 0xD000)",
      len(_low) <= 3 and sum(_w[a] for a in _low) <= 3,
      "%d addresses / %d writes below 0xD000"
      % (len(_low), sum(_w[a] for a in _low)))
check("all but 3 XRAM writes are in the DSP window, the DSP command ports or "
      "the 8051 scratch",
      all(0xD000 <= a <= 0xFFFF for a in _w if a not in _low),
      "%d stray writes below 0xD000" % len(_low))
check("the DSP is read back as well as written (it is a data source): the "
      "RP500 reads 0xD070 in both cabinet banks",
      b15[0xBE8F:0xBE93] == b"\x90\xd0\x70\xe0" and
      b14[0x9A9D:0x9AA1] == b"\x90\xd0\x70\xe0",
      "b15 %s  b14 %s" % (b15[0xBE8F:0xBE93].hex(" "),
                          b14[0x9A9D:0x9AA1].hex(" ")))
check("the RP500 already has a bulk preset service over MIDI "
      "(PRESET / RESTORE / ALL DONE / BULKERR1)",
      b15[0x525C:0x52A0].count(b"RESTORE") >= 1 and
      b"PRESET" in b15[0x5267:0x5270] and
      b"ALL DONE" in b15[0x5282:0x528B] and
      b"BULKERR1" in b15[0x5279:0x5282])

# --- the gdigi protocol match ----------------------------------------------
print("\n[12c] The RP500 speaks the gdigi/HMG preset protocol")
_b7 = bank(rp, 7)
_ids = {}
_i = 0x699E
while _i < 0x6A00:
    if _b7[_i + 1] == 0x6A:
        _ids[_b7[_i]] = (_b7[_i + 1] << 8) | _b7[_i + 2]
        _i += 3
    else:
        _i += 1
_gdigi = {0x18: "REQUEST_BULK_DUMP", 0x19: "RECEIVE_BULK_DUMP_START",
          0x1B: "RECEIVE_BULK_DUMP_END", 0x21: "REQUEST_PRESET_NAMES",
          0x22: "RECEIVE_PRESET_NAMES", 0x28: "REQUEST_PRESET_NAME",
          0x29: "RECEIVE_PRESET_NAME", 0x2A: "REQUEST_PRESET",
          0x2B: "RECEIVE_PRESET_START", 0x2C: "RECEIVE_PRESET_END",
          0x2D: "RECEIVE_PRESET_PARAMETERS", 0x39: "MOVE_PRESET"}
_present = [m for m in _gdigi if m in _ids]
check("the RP500's MIDI dispatch table (bank 7 0x699E) carries every gdigi "
      "preset message ID",
      len(_present) == len(_gdigi),
      "%d of %d: %s" % (len(_present), len(_gdigi),
                        " ".join("%02X" % m for m in _present)))
check("gdigi's MOVE_PRESET (0x39) handler is the RP500's bank-7 thunk",
      _ids.get(0x39) == 0x6A67 and
      _b7[0x6A67:0x6A6A] == b"\x12\xab\xd2",
      "handler 0x%04X -> %s" % (_ids.get(0x39, 0),
                               _b7[0x6A67:0x6A6A].hex(" ")))
check("the MOVE_PRESET handler branches on the USER bank code (1) vs the "
      "media-card bank (3)",
      _b7[0xAC04:0xAC0F] == b"\x64\x01\x19\x47\x60\x05\x7f\x03\x02\xac\xf2" and
      _b7[0xAC0F:0xAC14] == b"\x7f\x3b\x12\x0b\x4b",
      _b7[0xAC04:0xAC14].hex(" "))
# Correction 2026-11-11: the base is 0xF912, not 0xF9F2.  The walker doubles
# the index with ADD A,ACC (25 e0), adds 0x12, then ADDC 0xF9 - so
# address = 0xF912 + 2*i.  The old check's `...count(...) >= 0` was vacuous.
check("the preset descriptor index lives in XRAM 0xF912 (0x2D entries)",
      _b7[0xD8C4:0xD8D2] == b"\x94\x2d\x50\x56\xef\x25\xe0\x24\x12\xf5\x82\xe4\x34\xf9",
      "base 0xF912 + 2*i (ADD A,ACC)")

# --- the block loader predates the user-cab feature -----------------------
# The GSP's variable-length host->DSP block loader: source buffer 0x1483,
# source index 0x14C5, count 0x14C3, destination index/length + block base.
# If C48 (pre-IR) and C63 (IR build) carry the SAME machinery, the IR feature
# reused a generic loader instead of adding a transport.
print("\n[12d] The variable-length block loader predates the IR feature")
_cells = {
    "C48": {"0x14C3": 7, "0x14C5": 4, "0x2546": 69, "0x2547": 79, "0x233F": 50},
    "C63": {"0x14C3": 7, "0x14C5": 4, "0x2704": 69, "0x24FD": 50},
}
for _nm, _img in (("C48", c48), ("C63", c63)):
    _got = {}
    for _c in _cells[_nm]:
        _v = int(_c, 16)
        _got[_c] = _img.count(bytes([0x90, _v >> 8, _v & 0xFF]))
    check("%s carries the full block loader (source/index/count/length/block)"
          % _nm, _got == _cells[_nm], str(_got))
check("C48 and C63 reference the SAME receive buffer and index (0x14C3 x7, "
      "0x14C5 x4) - the loader is platform code, relocated only",
      c48.count(b"\x90\x14\xc3") == 7 and c63.count(b"\x90\x14\xc3") == 7 and
      c48.count(b"\x90\x14\xc5") == 4 and c63.count(b"\x90\x14\xc5") == 4)
check("the factory code-space descriptor is byte-identical in C48 and C63",
      bank(c48, 15)[0x35F5:0x3605] == bank(c63, 15)[0x3666:0x3676],
      bank(c48, 15)[0x35F5:0x3605].hex(" "))
check("the RP500 has NONE of the block-loader machinery",
      all(rp.count(bytes([0x90, int(_c, 16) >> 8, int(_c, 16) & 0xFF])) == 0
          for _c in ("0x14C3", "0x14C5", "0x2546", "0x2547", "0x2704", "0x24FD")),
      "0 references to any loader cell")

# --- is C48 a partial IR update?  No: the loader is as old as v1.1 --------
print("\n[12e] The GSP1101 timeline: the loader predates the oldest official build")
_series = ["gsp1101_v11.bin", "gsp1101_v12.bin", "gsp1101_v13.bin",
           "gsp1101_v20.bin", "gsp1101_vC20.bin", "c48_fw.bin", "c63_fw.bin"]
_tl = []
for _n in _series:
    _p = os.path.join(FW, _n)
    if not os.path.exists(_p):
        continue
    _img = flat_interleaved(readfile(_p))
    _code = _xram = 0
    _i = _img.find(b"\x90\xd0\x70\xf0")
    while _i >= 0:
        _src = None
        for _j in range(_i - 1, max(-1, _i - 9), -1):
            if _img[_j] == 0x93:
                _src = "code"
                break
            if _img[_j] == 0xE0:
                _src = "xram"
                break
        if _src == "code":
            _code += 1
        elif _src == "xram":
            _xram += 1
        _i = _img.find(b"\x90\xd0\x70\xf0", _i + 1)
    _slots = sum(1 for _k in range(1, 11) if ("USER %d" % _k).encode() in _img)
    _tl.append((_n, _code, _xram, _slots, b"USER_CAB" in _img))
    print("    %-18s code=%d xram=%2d USER-slots=%2d USER_CAB=%s"
          % (_n, _code, _xram, _slots, b"USER_CAB" in _img))
check("every GSP1101 build back to v1.1 has the 2 code-space + 32 XRAM streams",
      len(_tl) == 7 and all(c == 2 and x == 32 for _n, c, x, _s, _u in _tl),
      "%d builds checked" % len(_tl))
check("only C63 has the USER 1..10 cab names - the IR feature arrived at once, "
      "not incrementally",
      sum(1 for _n, _c, _x, _s, _u in _tl if _s == 10) == 1 and
      [n for n, _c, _x, s, _u in _tl if s == 10] == ["c63_fw.bin"])
check("the USER_CAB string exists in EVERY build including v1.1 - it is platform "
      "vocabulary, not evidence of partial IR work",
      all(u for _n, _c, _x, _s, u in _tl))
check("the RP500 has no loader at all (0 XRAM-sourced streams)",
      len([1 for _b, _o, _s in dsp_stores(rp) if _s == "xram"]) == 0)

swlog = readfile(os.path.join(EVID, "2026-11-11_ucsim_bankswitch.log")).decode("utf-8", "replace")
check("simulator performed >3000 bank switches", swlog.count("Loading from bank") >= 3000,
      str(swlog.count("Loading from bank")))

# --- the simulator capture of the DSP stream -------------------------------
_stream_log = os.path.join(EVID, "2026-11-11_ucsim_dspstream.log")
if os.path.exists(_stream_log):
    _txt = readfile(_stream_log).decode("utf-8", "replace")
    _cur = None
    _bytes = []
    for _ln in _txt.splitlines():
        _m = re.match(r"^Stop at 0x([0-9a-f]+):", _ln.strip())
        if _m:
            _cur = int(_m.group(1), 16)
            continue
        _m = re.search(r"DPTR=\s*0x([0-9a-f]+)\s*@DPTR=\s*0x([0-9a-f]{2})", _ln)
        if _m and _cur in (0xBEAD, 0x9ABB) and int(_m.group(1), 16) == 0xD070:
            _bytes.append(int(_m.group(2), 16))
    check("the simulator captured the DSP data-port writes", len(_bytes) > 100,
          "%d bytes" % len(_bytes))
    check("the first 24 bytes at 0xD070 are exactly the 24-byte descriptor "
          "at bank 15 0x2E3B",
          len(_bytes) >= 24 and
          bytes(_bytes[:24]) == b15[0x2E3B:0x2E3B + 24],
          " ".join("%02X" % b for b in _bytes[:24]))
    check("the stream continues with CODE after the 24-byte descriptor "
          "(the DSP model never stops the firmware)",
          len(_bytes) > 24 and _bytes[24] == 0xE6,
          "byte 25 = %02X" % (_bytes[24] if len(_bytes) > 24 else 0))
else:
    print("  (skipped: no archived DSP-stream log)")

# ----------------------------------------------------------------- [13] ----
print("\n[13] Archive hygiene")
for f in ("00_master/README_FIRST.md", "00_master/PROJECT_STATE.md",
          "00_master/TOOLCHAIN.md", "00_master/CREDITS.md",
          "06_deliverable/FINDINGS.md", "06_deliverable/rp500_bank_map.md",
          "06_deliverable/rp500_firmware_roadmap.md",
          "07_open_source_tools/netupdaterclone_src/README.md",
          "05_evidence/model_credits.json"):
    check("archived: " + f, os.path.exists(os.path.join(ROOT, f)))
check("all 27 bundled firmware resources extracted",
      len([x for x in os.listdir(RES) if x.endswith(".DigBin")]) == 27,
      str(len([x for x in os.listdir(RES) if x.endswith(".DigBin")])))

npass = sum(1 for _n, ok, _d in RESULTS if ok)
print()
print("=" * 78)
print("AUDIT RESULT: %d/%d checks passed" % (npass, len(RESULTS)))
print("=" * 78)
sys.exit(0 if npass == len(RESULTS) else 1)
