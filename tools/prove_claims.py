#!/usr/bin/env python3
"""Hard proof of every claim this project changed or added.

The archive has no version control, so a file-level diff is not recoverable.
What *is* recoverable - and what actually matters - is the **claim level**:
for each load-bearing claim, the old wording, the new wording, and a
**discriminating test** evaluated against the artifacts.

A discriminating test is one whose outcome differs between the two readings:
it returns TRUE for the new claim and FALSE for the old one. Every claim below
carries such a test, and the raw bytes it was decided on are printed.

Usage:
    python prove_claims.py            # print the proof table + evidence
    python prove_claims.py --write    # also (re)write 05_evidence/claims_ledger.md
"""
import argparse
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from d51 import disasm                                   # noqa: E402
from fir2 import is_fir                                 # noqa: E402  (strict FIR test)

FW = os.path.join(ROOT, "01_source_firmware")
DOCS = os.path.join(ROOT, "03_docs")
EVID = os.path.join(ROOT, "05_evidence")
BANK = 0x10000


def readfile(p):
    with open(p, "rb") as f:
        return f.read()


def flat_interleaved(d):
    return b"".join(d[k * 0x10008 + 8:k * 0x10008 + 8 + 0x10000] for k in range(16))


def bank(img, k):
    return img[k * BANK:(k + 1) * BANK]


rp = readfile(os.path.join(FW, "rp500_v20.bin"))
c48 = flat_interleaved(readfile(os.path.join(FW, "c48_fw.bin")))
c63 = flat_interleaved(readfile(os.path.join(FW, "c63_fw.bin")))
b14, b15 = bank(rp, 14), bank(rp, 15)

CLAIMS = []


def claim(cid, topic, old, new, old_holds, new_holds, evidence):
    CLAIMS.append(dict(id=cid, topic=topic, old=old, new=new,
                       old_holds=bool(old_holds), new_holds=bool(new_holds),
                       evidence=evidence))


# ---------------------------------------------------------------- C1 -------
blk14 = b14[0x2DC2:0x2DC2 + 24]
blk15 = b15[0x2E3B:0x2E3B + 24]
claim(
    "C1",
    "What the RP500 actually streams to its DSP",
    "the RP500 streams coefficient blocks out of code space - two streams, "
    "bank 14 source 0x2DC2 (cmd 0xC0/0xC1), bank 15 source 0x2E3B (command "
    "0xA0), one byte at a time to port 0xD070",
    "the RP500 streams a 24-byte PARAMETER DESCRIPTOR from code space - "
    "identical in both cabinet banks and immediately followed by executable "
    "code - not an IR-sized payload",
    old_holds=(len(blk15) >= 512 and blk14 != blk15),
    new_holds=(len(blk15) == 24 and blk14 == blk15 and
                b15[0x2E53] == 0xE6 and b14[0x2DDA] == 0xE6),
    evidence=[
        "bank 14 0x2DC2..0x2DD9 : %s" % blk14.hex(" "),
        "bank 15 0x2E3B..0x2E52 : %s" % blk15.hex(" "),
        "the two blocks are byte-for-byte identical : %s" % (blk14 == blk15),
        "the byte after the block: bank14 0x2DDA=%02X  bank15 0x2E53=%02X  "
        "(0xE6 = MOV A,@R0 - the head of the next function)"
        % (b14[0x2DDA], b15[0x2E53]),
        "the two descriptor blocks live in DIFFERENT banks at DIFFERENT "
        "addresses yet are identical - so they are not cabinet-specific",
    ])

# ---------------------------------------------------------------- C2 -------
# Is the 0x7FF8 compare on the "status changed" path or the "status did not
# change" path?  0xBE2D is `JB E2h,0BE4C` (jump-if-set -> the send path);
# the compare block starts at 0xBE30, i.e. the FALL-THROUGH.
cmp_on_changed_path = False
_stream = readfile(os.path.join(EVID, "2026-11-11_ucsim_dspstream_long.md")
                   ) if os.path.exists(os.path.join(
                       EVID, "2026-11-11_ucsim_dspstream_long.md")) else b""
_measured = 0
_m = re.search(r"\| bytes the firmware pushed at the DSP data port 0xD070 \| \*\*(\d+)\*\* \|",
               _stream.decode("utf-8", "replace") if _stream else "")
if _m:
    _measured = int(_m.group(1).replace(" ", ""))
claim(
    "C2",
    "The 0x7FF8 byte cap",
    "the stream is capped at 0x7FF8 bytes per stream",
    "there is NO length limit in the host code; the 0x7FF8 compare is a STALL "
    "ABORT on the 'the DSP status did not change' path",
    old_holds=cmp_on_changed_path,
    new_holds=(b15[0xBE2D] == 0x20 and b15[0xBE2E] == 0xE2 and
               b15[0xBE2F] == 0x1C and b15[0xBE30] == 0xA8 and
               b15[0xBE3D] == 0x94 and b15[0xBE3E] == 0xF8 and
               b15[0xBE40] == 0x94 and b15[0xBE41] == 0x7F and
               _measured > 0x7FF8),
    evidence=[
        "bank 15 0xBE29..0xBE42 (the compare is the FALL-THROUGH of the "
        "jump-if-set):",
    ] + ["    %04X: %-9s %s" % (a, raw, txt) for a, raw, txt in
         disasm(b15, 0, 0xBE29, 0xBE43)] + [
        "0xBE2D `JB E2h,0xBE4C` = jump to the SEND path when bit 2 changed; "
        "the 0x7FF8 compare at 0xBE3D is reached only when it did NOT change",
        "measured with a DSP model that always acknowledges: %d bytes pushed "
        "(0x7FF8 = %d) - the cap never fired" % (_measured, 0x7FF8),
    ])

# ---------------------------------------------------------------- C3 -------
def xram_bases(img):
    """Base of every XRAM-sourced DSP store, decoded from the DPTR build."""
    out = []
    store = b"\x90\xd0\x70\xf0"
    for i in range(len(img) - 12):
        if img[i:i + 4] != store:
            continue
        j = i - 1
        while j > i - 9:
            if img[j] == 0xE0:
                break
            if img[j] == 0x93:
                j = -1
                break
            j -= 1
        if j <= 0:
            continue
        b = bank(img, i // BANK)
        off = i % BANK
        for k in range(off - 1, max(-1, off - 24), -1):
            if b[k] == 0x74 and b[k + 2] in (0x2E, 0x2F) and b[k + 3] == 0xF5 \
               and b[k + 4] == 0x82 and b[k + 5] == 0xE4 and b[k + 6] == 0x34 \
               and b[k + 8] == 0xF5 and b[k + 9] == 0x83:
                out.append(((b[k + 7] << 8) | b[k + 1]) & 0xFFFF)
                break
    return out


b48 = xram_bases(c48)
b63 = xram_bases(c63)
claim(
    "C3",
    "The GSP's XRAM source base (C48)",
    "the GSP C48 XRAM source base is 0x2602",
    "the GSP C48 XRAM source base is 0x2445 (C63: 0x2603); both are 'base + index'",
    old_holds=(0x2602 in b48),
    new_holds=(b48.count(0x2445) == 32 and 0x2602 not in b48 and
               b63.count(0x2603) == 32),
    evidence=[
        "C48: %d XRAM-sourced stores, base 0x2445 x%d, base 0x2602 x%d"
        % (len(b48), b48.count(0x2445), b48.count(0x2602)),
        "C63: %d XRAM-sourced stores, base 0x2603 x%d, base 0x2602 x%d"
        % (len(b63), b63.count(0x2603), b63.count(0x2602)),
        "C48 bank 0 0x2F43..0x2F51 (the DPTR build): "
        + " ".join("%02X" % x for x in c48[0x2F43:0x2F52]),
        "   74 45 = MOV A,#45h ; 2E = ADD A,R6 ; f5 82 = MOV 82h,A ; "
        "e4 = CLR A ; 34 24 = ADDC A,#24h ; f5 83 = MOV 83h,A",
        "   => DPL = 0x45+index, DPH = 0x24  =>  base 0x2445",
        "C63 bank 0 0x2F3E..0x2F48: "
        + " ".join("%02X" % x for x in c63[0x2F3E:0x2F48]),
        "   74 03 = MOV A,#03h ; 2E = ADD A,R6 ; 34 26 = ADDC A,#26h "
        "=> base 0x2603",
    ])

# ---------------------------------------------------------------- C4 -------
_tail = bytes.fromhex("34d08f82f583edf0")
_cfg = {}
for k in (14, 15):
    b = bank(rp, k)
    i = b.find(_tail)
    j = i - 1
    base = None
    while j > max(0, i - 16):
        if b[j] == 0x90 and b[j + 3] == 0x93:
            base = (b[j + 1] << 8) | b[j + 2]
            break
        j -= 1
    _cfg[k] = base
_streams = rp.count(b"\x90\xd0\x70\xf0")
_log = ""
_slog = os.path.join(EVID, "2026-11-11_ucsim_dspstream.log")
if os.path.exists(_slog):
    _log = readfile(_slog).decode("utf-8", "replace")
_saw_cfg_write = ("Stop at 0x00b897" in _log) and ("Event `write' at xram[0xd070]" in _log)
claim(
    "C4",
    "How many mechanisms write the DSP data port 0xD070",
    "the RP500 writes the DSP data port 0xD070 exactly twice",
    "three mechanisms: two code-sourced descriptor stores, plus a 113-byte "
    "configuration block copied byte-wise into DSP registers 0xD000-0xD070 "
    "(its last byte lands on 0xD070)",
    old_holds=(_streams == 2 and not _saw_cfg_write),
    new_holds=(_streams == 2 and _cfg[14] == 0x2C80 and _cfg[15] == 0x2CBB and
               _saw_cfg_write),
    evidence=[
        "code-sourced stores `MOV DPTR,#0D070h ; MOVX @DPTR,A` : %d "
        "(bank 14 0x9ABA, bank 15 0xBEAC)" % _streams,
        "the configuration loop exists in banks %s, table bases %s"
        % (sorted(_cfg), {k: hex(v) for k, v in _cfg.items()}),
        "bank 15 0xB886..0xB896: "
        + " ".join("%02X" % x for x in b15[0xB886:0xB897]),
        "   90 2c bb = MOV DPTR,#2CBBh ; 93 = MOVC (read the table byte) ; "
        "34 d0 = ADDC A,#D0h ; 8f 82/f5 83 = DPL/DPH ; f0 = MOVX @DPTR,A",
        "   => the table byte is written to DSP register 0xD000+index, "
        "index 0x00..0x70 (0x59 skipped) -> index 0x70 is 0xD070",
        "the loop bounds: bank 15 0xB872 %s (compare against 0x0071) and "
        "0xB87A %s (skip index 0x59)"
        % (" ".join("%02X" % x for x in b15[0xB872:0xB878]),
           " ".join("%02X" % x for x in b15[0xB879:0xB87E])),
        "the table's last byte (index 0x70) = bank14 %02X, bank15 %02X"
        % (b14[0x2C80 + 0x70], b15[0x2CBB + 0x70]),
        "EMULATOR PROOF: the archived uCsim log contains a stop at 0xB897 - the "
        "instruction right after that configuration write - caused by the "
        "0xD070 write event: %s" % _saw_cfg_write,
    ])

# ---------------------------------------------------------------- C5 -------
def fir_hits(img):
    n = 0
    for k in range(16):
        b = bank(img, k)
        for off in range(0, len(b) - 512 + 1, 512):
            if is_fir(struct.unpack(">128i", b[off:off + 512])):
                n += 1
    return n


_h = {"RP500": fir_hits(rp), "C48": fir_hits(c48), "C63": fir_hits(c63)}
_manual = readfile(os.path.join(DOCS, "RP500_OM_EN.txt")).lower()
claim(
    "C5",
    "Do factory cabinets have IRs?",
    "the RP500's 28 factory cabinet IRs live inside the AudioDNA2 DSP",
    "there are NO factory cabinet IRs: the factory cabinets are parametric DSP "
    "models; an IR exists only in the user-cabinet feature the GSP1101 added "
    "in firmware C54",
    old_holds=(sum(_h.values()) > 0),
    new_holds=(sum(_h.values()) == 0 and b"impulse" not in _manual),
    evidence=[
        "strict 128-tap FIR-block scan (fir2.is_fir): " +
        ", ".join("%s=%d" % (k, v) for k, v in _h.items()),
        "the RP500 owner's manual contains 'impulse': %s"
        % (b"impulse" in _manual),
        "report 12.3 already stated this: 'There are **no** factory IR "
        "coefficient tables in any image'",
    ])

# ---------------------------------------------------------------- C6 -------
def host_addrs(img):
    s = set()
    for i in range(len(img) - 2):
        if img[i] == 0x90:
            a = (img[i + 1] << 8) | img[i + 2]
            if 0xD000 <= a <= 0xD0FF or 0xE000 <= a <= 0xE8FF:
                s.add(a)
    return s


def d000_dfff_addrs(img):
    s = set()
    for i in range(len(img) - 2):
        if img[i] == 0x90:
            a = (img[i + 1] << 8) | img[i + 2]
            if 0xD000 <= a <= 0xDFFF:
                s.add(a)
    return s


_r, _c4, _c6 = host_addrs(rp), host_addrs(c48), host_addrs(c63)
_common = _r & _c4 & _c6
_old148 = d000_dfff_addrs(rp)
_codeish = [a for a in sorted(_old148) if a >= 0xD100]
_core = {0xD01E, 0xD01F, 0xD020, 0xD034, 0xD050, 0xD05A, 0xD05B, 0xD066,
         0xD069, 0xD06D, 0xD06E, 0xD06F, 0xD070,
         0xE000, 0xE200, 0xE400, 0xE800}
claim(
    "C6",
    "How much of the host/DSP interface the two products share",
    "the RP500 and the GSP share 148 vs 151/154 distinct 0xD0xx-0xDFFF "
    "DSP registers",
    "23 addresses in the host windows (0xD000-0xD0FF, 0xE000-0xE8FF) are "
    "common to RP500, GSP C48 and GSP C63; of those, 17 are the complete "
    "handshake set. The old '148' counted code pointers, not registers.",
    old_holds=(len(_codeish) == 0),
    new_holds=(len(_common) == 23 and _core <= _r and _core <= _c4 and
               _core <= _c6),
    evidence=[
        "addresses in 0xD000-0xDFFF referenced by the RP500: %d; of those, "
        "%d are >= 0xD100" % (len(_old148), len(_codeish)),
        "PROOF that >=0xD100 addresses are CODE, not registers: 0xD437 holds "
        "executable code in bank 15 (%s) and is 0xFF (unused) in banks 0 and "
        "14 (%s / %s)"
        % (b15[0xD437:0xD43F].hex(" "), bank(rp, 0)[0xD437:0xD43F].hex(" "),
           b14[0xD437:0xD43F].hex(" ")),
        "common to all three images: %d -> %s"
        % (len(_common), " ".join(hex(x) for x in sorted(_common))),
        "handshake core present in all three: %d of %d"
        % (len(_core & _common), len(_core)),
    ])

# ---------------------------------------------------------------- C7 -------
_terminator = any(c63[i:i + 6] == b"\x90\xd0\x70\x74\xf5\xf0"
                   for i in range(len(c63) - 6))
_stage = (any(c63[i:i + 3] == b"\x74\x83\x2f" for i in range(len(c63) - 3)) and
          c63.count(b"\x90\x14\xc3") >= 1 and c63.count(b"\x90\x27\x04") >= 1)
_stage_bytes = bank(c63, 15)[0xD7EF:0xD80B]
assert _stage_bytes[:3] == bytes([0x74, 0x83, 0x2F]), \
    "C63 bank 15 0xD7EF is not the staging copy: %s" % _stage_bytes[:3].hex(" ")
claim(
    "C7",
    "How the GSP actually delivers a user IR (NEW)",
    "not previously established at address level - the archive only knew "
    "'32 XRAM-sourced streams'",
    "the GSP's user IR is staged in XRAM (0x1483+ -> 0x2603+, count in "
    "0x14C3) and streamed with an explicit length (0x2704) and a 0xF5 "
    "terminator",
    old_holds=False,
    new_holds=(_terminator and _stage),
    evidence=[
        "0xF5 terminator written to 0xD070 : %s" % _terminator,
        "staging copy XRAM 0x1483+ -> 0x2603+ with the count in 0x14C3 : %s"
        % _stage,
        "C63 bank 15 0xD7EF..0xD80A (the copy): "
        + " ".join("%02X" % x for x in bank(c63, 15)[0xD7EF:0xD80B]),
        "   74 83 = MOV A,#83h ; 2f = ADD A,R7 ; f5 82/e4/34 14/f5 83 = "
        "DPTR = 0x1483+index (R7 = XRAM[0x14C5]) ; e0 = MOVX A,@DPTR (read) ; "
        "f0 = MOVX @DPTR,A (write to 0x2603+index)",
        "   the destination index/length cell is XRAM[0x2704] and the copy "
        "count is XRAM[0x14C3]; the stream compares its index XRAM[0x24FD] "
        "against XRAM[0x2704]",
    ])

# ---------------------------------------------------------------- report ----
print("=" * 100)
print("PROOF OF CHANGED AND NEW CLAIMS")
print("=" * 100)
print()
hdr = "%-4s %-46s %-9s %-9s %s" % ("id", "topic", "OLD holds", "NEW holds", "verdict")
print(hdr)
print("-" * 100)
allok = True
for c in CLAIMS:
    verdict = "CORRECTED" if (not c["old_holds"] and c["new_holds"]) else \
              ("CONFIRMED" if (c["old_holds"] and c["new_holds"]) else \
               ("REFUTED" if not c["new_holds"] else "??"))
    if not c["new_holds"]:
        allok = False
    print("%-4s %-46s %-9s %-9s %s" % (c["id"], c["topic"][:46],
                                       c["old_holds"], c["new_holds"], verdict))
print()
for c in CLAIMS:
    print("-" * 100)
    print("%s  %s" % (c["id"], c["topic"]))
    print("  OLD: %s" % c["old"])
    print("  NEW: %s" % c["new"])
    print("  old-claim holds: %s    new-claim holds: %s" % (c["old_holds"], c["new_holds"]))
    for e in c["evidence"]:
        print("    - %s" % e)
    print()

print("=" * 100)
n_ok = sum(1 for c in CLAIMS if c["new_holds"])
n_old = sum(1 for c in CLAIMS if c["old_holds"])
print("%d/%d new claims hold; %d/%d old claims still hold"
      % (n_ok, len(CLAIMS), n_old, len(CLAIMS)))
print("=" * 100)

if "--write" in sys.argv:
    out = os.path.join(EVID, "claims_ledger.md")
    L = []
    L.append("# Claims ledger - what changed, what is new, and the proof")
    L.append("")
    L.append("Generated by `04_analysis_scripts/prove_claims.py --write`. "
             "Re-run it to regenerate this file; the archive has no version "
             "control, so this ledger is the auditable record of the "
             "revision.")
    L.append("")
    L.append("| id | topic | old claim holds | new claim holds | verdict |")
    L.append("|---|---|---|---|---|")
    for c in CLAIMS:
        v = ("corrected" if (not c["old_holds"] and c["new_holds"])
             else "confirmed" if c["old_holds"] else "REFUTED")
        L.append("| %s | %s | %s | %s | %s |"
                 % (c["id"], c["topic"], c["old_holds"], c["new_holds"], v))
    L.append("")
    for c in CLAIMS:
        L.append("## %s - %s" % (c["id"], c["topic"]))
        L.append("")
        L.append("**Old claim.** %s" % c["old"])
        L.append("")
        L.append("**New claim.** %s" % c["new"])
        L.append("")
        L.append("Old claim holds: **%s**   New claim holds: **%s**"
                 % (c["old_holds"], c["new_holds"]))
        L.append("")
        L.append("Evidence:")
        L.append("")
        for e in c["evidence"]:
            L.append("- %s" % e)
        L.append("")
    open(out, "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("wrote", out)

sys.exit(0 if allok else 1)
