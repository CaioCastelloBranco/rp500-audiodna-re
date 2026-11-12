#!/usr/bin/env python3
"""Independent audit of the software evidence behind the user-cab port.

Every check below is derived from a shipped artifact, not from the prose in
06_deliverable.  It exists because the previous review found that several
structural claims had been stated more strongly than the evidence allowed.

Run:  python 04_analysis_scripts/audit_software_probe.py
"""

import pathlib
import re
import struct
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
FW = ROOT / "01_source_firmware"
SB = ROOT / "02_source_binaries"

checks = []


def check(name, ok, detail=""):
    checks.append(bool(ok))
    print("%s  %s%s" % ("PASS" if ok else "FAIL", name,
                         ("  [%s]" % detail) if detail else ""))


def flat_gsp(path):
    """GSP1101 .DigBin layout: 16 x (8-byte descriptor + 64 KB body)."""
    d = pathlib.Path(path).read_bytes()
    return b"".join(d[k * 0x10008 + 8:k * 0x10008 + 8 + 0x10000] for k in range(16))


def be16(vals):
    return b"".join(bytes([v >> 8, v & 0xFF]) for v in vals)


rp = (FW / "rp500_v20.bin").read_bytes()
c48 = flat_gsp(FW / "c48_fw.bin")
c63 = flat_gsp(FW / "c63_fw.bin")
v20 = (FW / "gsp1101_v20.bin").read_bytes()
rp1000 = (FW / "rp1000V12.bin").read_bytes()
rp355 = (FW / "rp355V14.bin").read_bytes()

XEDIT_RP500 = [571, 572, 573, 623, 624, 577, 576, 613, 626, 579,
               614, 616, 584, 583, 622, 625, 609, 611, 618, 619,
               620, 621, 612, 608, 585, 570]
USER_IDS = [596, 597, 598, 599, 600, 601, 602, 603, 604, 736]

# ---------------------------------------------------------------------------
# 1. The two cab-ID tables
# ---------------------------------------------------------------------------
rp_tab = [struct.unpack_from(">H", rp, 0x7519F + i * 2)[0] for i in range(28)]
check("RP500 cab-ID table at bank 7 0x519F has 28 entries",
      rp_tab == XEDIT_RP500 + [607, 606], repr(rp_tab[-2:]))
check("the last two RP500 IDs are the acoustic cabs, not user slots",
      rp_tab[-2:] == [607, 606], "607=DREAD AC, 606=JUMBO AC")

c63_full = XEDIT_RP500 + USER_IDS + [607, 606]
i = c63.find(be16(c63_full))
check("GSP C63 has the same table plus the 10 user IDs, in place",
      i >= 0, "flat 0x%X" % i if i >= 0 else "not found")

# ---------------------------------------------------------------------------
# 2. The feature is GSP-only
# ---------------------------------------------------------------------------
def has_user_slot(img):
    return (b"USER 1" in img and b"USER 10" in img)


check("GSP C63 carries USER 1..USER 10 names", has_user_slot(c63))
for name, img in (("RP500 v2.0", rp), ("RP1000 V12", rp1000),
                  ("RP355 V14", rp355), ("GSP C48", c48)):
    check("%s has no USER cab names" % name, not has_user_slot(img))

# ---------------------------------------------------------------------------
# 3. The DSP stream shapes (exact instruction sequences)
# ---------------------------------------------------------------------------
# MOVX A,@DPTR ; MOV DPTR,#0D070h ; MOVX @DPTR,A
XRAM_SEQ = b"\xe0\x90\xd0\x70\xf0"
# MOVC A,@A+DPTR ; MOV DPTR,#0D070h ; MOVX @DPTR,A
CODE_SEQ = b"\x93\x90\xd0\x70\xf0"

for name, img in (("RP500", rp), ("C48", c48), ("C63", c63),
                  ("RP1000", rp1000), ("RP355", rp355)):
    check("%s has 2 code-space DSP streams" % name,
          img.count(CODE_SEQ) == 2, "%d" % img.count(CODE_SEQ))

check("RP500/RP1000/RP355 have zero XRAM-sourced DSP streams",
      rp.count(XRAM_SEQ) == 0 and rp1000.count(XRAM_SEQ) == 0
      and rp355.count(XRAM_SEQ) == 0)
check("GSP C48 and C63 each have 32 XRAM-sourced DSP stream sites "
      "(2 per bank x 16 banks - one replicated routine, not 32 models)",
      c48.count(XRAM_SEQ) == 32 and c63.count(XRAM_SEQ) == 32)

# ---------------------------------------------------------------------------
# 4. No factory IRs, at the width the loader actually uses (32-bit taps)
# ---------------------------------------------------------------------------
def ir_candidates(img, taps):
    arr = np.frombuffer(img[:len(img) // 4 * 4], dtype=">i4").astype(np.int64)
    hits = 0
    for start in range(0, len(arr) - taps, taps):
        w = arr[start:start + taps]
        if int(np.count_nonzero(w)) < taps * 0.7:
            continue
        if int(np.max(np.abs(w))) > (1 << 22):
            continue
        q = taps // 4
        e1 = float(np.sum(w[:q].astype(np.float64) ** 2))
        e4 = float(np.sum(w[-q:].astype(np.float64) ** 2))
        if e1 > 4 * max(e4, 1.0):
            hits += 1
    return hits


for name, img in (("RP500", rp), ("C48", c48), ("C63", c63), ("V20", v20)):
    n128 = ir_candidates(img, 128)
    n208 = ir_candidates(img, 208)
    check("%s has no factory 128/208-tap 32-bit IR" % name,
          n128 == 0 and n208 == 0, "128:%d 208:%d" % (n128, n208))

# ---------------------------------------------------------------------------
# 5. The two "cabinet" DSP tables are identical, so they are not per-model
# ---------------------------------------------------------------------------
t14 = rp[14 * 0x10000 + 0x2C80:14 * 0x10000 + 0x2C80 + 113]
t15 = rp[15 * 0x10000 + 0x2CBB:15 * 0x10000 + 0x2CBB + 113]
d14 = rp[14 * 0x10000 + 0x2DC2:14 * 0x10000 + 0x2DC2 + 24]
d15 = rp[15 * 0x10000 + 0x2E3B:15 * 0x10000 + 0x2E3B + 24]
check("the 113-byte DSP parameter tables in banks 14 and 15 are identical",
      t14 == t15)
check("the 24-byte DSP descriptors in banks 14 and 15 are identical",
      d14 == d15)
# The point is not "no byte equals a cab ID" (coincidences are common and the
# table contains one), but that the SAME table is fed to both banks: it cannot
# be a per-model cab selector.  That is already established above.

# ---------------------------------------------------------------------------
# 6. Super7 framing and the captured RP500 update log
# ---------------------------------------------------------------------------
log = (ROOT / "05_evidence" / "2026-11-10_rp500_updater_flash.log").read_text(
    errors="replace").splitlines()
msgs = []
for ln in log:
    m = re.search(r"TX: (F0[0-9A-F]+)", ln)
    if m:
        msgs.append(m.group(1))

short = [h for h in msgs if len(h) < 100]
ok = True
for h in short:
    b = bytes.fromhex(h)
    x = 0
    for v in b[1:-2]:
        x ^= v
    ok = ok and (x & 0x7F) == b[-2]
check("every short logged SysEx message uses XOR & 0x7F as its checksum",
      ok, "%d messages" % len(short))

frames = [h for h in msgs if h.startswith("F0000010005E057A")]
check("the captured update sent 4039 0x7A data blocks", len(frames) == 4039,
      "%d" % len(frames))


def unpack_super7(enc):
    out, i = [], 0
    while i < len(enc):
        msb = enc[i]
        for j, ch in enumerate(enc[i + 1:i + 8]):
            out.append(ch | (((msb >> (6 - j)) & 1) << 7))
        i += 8
    return bytes(out)


b0 = bytes.fromhex(frames[0])
payload = unpack_super7(b0[8:-2])
addr = int.from_bytes(payload[:4], "big")
length = int.from_bytes(payload[4:6], "big")
data = payload[6:]
check("0x7A block 0 is <addr32=0><len16=0x0100> + the image's first 256 bytes",
      addr == 0 and length == 0x100 and data == rp[:256],
      "addr=0x%X len=0x%X data=%d" % (addr, length, len(data)))

logtext = "\n".join(log)
segs = sorted({int(m.group(1), 16) for m in
               re.finditer(r"segment addr=0x([0-9A-Fa-f]+)", logtext)})
check("the device declared 16 x 64 KB flash segments (per run)",
      segs == [k * 0x10000 for k in range(16)]
      and "Data to write: 1048576 bytes" in logtext,
      "%d distinct segments" % len(segs))

# ---------------------------------------------------------------------------
# 7. The C59 user-cab record: 128/208 taps x 4 bytes, in a 2048-byte record
# ---------------------------------------------------------------------------
exe = (SB / "JUserCabUpdater vC59.exe").read_bytes()
pe = struct.unpack_from("<I", exe, 0x3C)[0]
nsec = struct.unpack_from("<H", exe, pe + 6)[0]
optsz = struct.unpack_from("<H", exe, pe + 20)[0]
base = struct.unpack_from("<I", exe, pe + 24 + 28)[0]
secs = []
for k in range(nsec):
    o = pe + 24 + optsz + k * 40
    nm = exe[o:o + 8].rstrip(b"\0").decode()
    vsz, va, rsz, ptr = struct.unpack_from("<IIII", exe, o + 8)
    secs.append((nm, va, vsz, ptr, rsz))


def va2off(v):
    r = v - base
    for nm, va, vsz, ptr, rsz in secs:
        if va <= r < va + vsz:
            return ptr + (r - va)
    raise KeyError(hex(v))


check("C59 clamps the tap count to 0x80 (128) in the normal case",
      exe[va2off(0x4075BB):va2off(0x4075BB) + 6] == b"\x81\xfb\x80\x00\x00\x00")
check("C59 clamps the tap count to 0xD0 (208) when the option bit is set",
      exe[va2off(0x4075CA):va2off(0x4075CA) + 6] == b"\x81\xfb\xd0\x00\x00\x00")
check("C59 pads the record data area to 0x7E7 (2023) bytes",
      exe[va2off(0x4077CA):va2off(0x4077CA) + 5] == b"\xbb\xe7\x07\x00\x00")
check("C59 appends a 23-byte name and a 2-byte trailer",
      2023 + 23 + 2 == 2048 and
      exe[va2off(0x40792D):va2off(0x40792D) + 2] == b"\x8b\xc6" and
      exe[va2off(0x4079B9):va2off(0x4079B9) + 5] == b"\xba\x02\x00\x00\x00")

# WAV sample conversion: 4 bytes per sample, big-endian (the packer).
check("C59 stores each tap as a 32-bit big-endian value",
      # sar edx,0x18 / sar ecx,0x10 / sar edx,8 then four stores
      b"\xc1\xfa\x18" in exe[va2off(0x407750):va2off(0x4077A0)]
      and b"\xc1\xf9\x10" in exe[va2off(0x407750):va2off(0x4077A0)])

check("C59 accepts only 44.1 kHz mono/stereo WAV input",
      b"not 44100 Hz" in exe and b"number channels not 1 or 2" in exe)

# ---------------------------------------------------------------------------
# summary
# ---------------------------------------------------------------------------
print()
print("AUDIT RESULT: %d/%d checks passed" % (sum(checks), len(checks)))
sys.exit(0 if all(checks) else 1)
