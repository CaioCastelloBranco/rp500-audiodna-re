#!/usr/bin/env python3
"""Survey the other AudioDNA2 firmwares bundled in the updater.

The updater carries 27 firmware images. Six of them are for siblings of the
RP500 — three RP1000 (1 MB, same shape as the RP500) and three RP355
(720 KB) — and they run the same platform code on the same AudioDNA2 DSP.

This script unpacks them and asks the questions that matter for the port:

  1. what is the bank layout (is the P1 bank-select table present)?
  2. which DSP host ports does the firmware use?
  3. where do the coefficient streams read their bytes from?
     - MOVC A,@A+DPTR  -> the source is CODE SPACE (the factory IRs)
     - MOVX A,@DPTR    -> the source is EXTERNAL RAM / flash
     A firmware that streams coefficients from *flash* would be a ready-made
     reference implementation of the "source swap" the RP500 port needs.
  4. does it mention user cabs at all?

Usage:
    python platform_survey.py [image.DigBin ...]
"""
import argparse
import os
import re
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FW = os.path.join(ROOT, "01_source_firmware")
RES = os.path.join(ROOT, "07_open_source_tools", "netupdaterclone_src")

DSP_PORTS = [0xE000, 0xEE00, 0xE200, 0xE400, 0xE800, 0xD01E, 0xD01F,
              0xD020, 0xD05A, 0xD05B, 0xD066, 0xD06D, 0xD06E, 0xD070]


def unpack_digbin(path):
    raw = open(path, "rb").read()
    if len(raw) < 16 or struct.unpack_from(">I", raw, 0)[0] not in (0x005C0005, 0x05005C00):
        raise ValueError("%s: not a DigBin container" % path)
    out = bytearray()
    off = 12
    while off < len(raw):
        addr, ln = struct.unpack_from(">II", raw, off)
        off += 8
        out += raw[off:off + ln]
        off += ln
    return bytes(out)


def banks_of(img, size=0x10000):
    return [img[k * size:(k + 1) * size] for k in range(len(img) // size)]


def p1_table(bank):
    """Detect the 16-entry 'MOV P1,#(0xF0+n) ; RET' table at 0x0200."""
    ok = 0
    for n in range(16):
        off = 0x0200 + n * 8
        if bank[off:off + 4] == bytes([0x75, 0x90, 0xF0 + n, 0x22]):
            ok += 1
    return ok


def stream_sites(img, bank_size=0x10000):
    """Find coefficient-stream *stores* to the DSP data port 0xD070 and
    classify where the byte came from.

    A site is the 4-byte sequence  90 D0 70 F0  (MOV DPTR,#0D070h ; MOVX @DPTR,A).
    The source is the nearest preceding load into A:
      0x93  MOVC A,@A+DPTR  -> code space (the factory IRs)
      0xE0  MOVX A,@DPTR    -> external RAM / flash
    """
    sites = []
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
        sites.append((i // bank_size, i % bank_size, src or "?"))
    return sites


def stream_source_base(img, bank_size=0x10000, bank=None, off=None):
    """Recover the code-space base a stream reads from (e.g. 0x2E3B),
    searching only the bytes immediately before the site."""
    b = img[bank * bank_size:(bank + 1) * bank_size]
    lo = max(0, off - 24)
    for i in range(off - 1, lo, -1):
        if b[i] == 0x24 and b[i + 2] == 0xF5 and b[i + 3] == 0x82 and \
           b[i + 4] == 0x74 and b[i + 6] == 0x3E and b[i + 7] == 0xF5 and \
           b[i + 8] == 0x83:
            return ((b[i + 5] << 8) | b[i + 1]) & 0xFFFF
    return None


def load_image(path):
    """Accept a .DigBin container, a flat .bin, or an interleaved GSP image.

    The GSP images are stored as 16 x (8-byte descriptor + 64 KB body); the
    bank body of bank k starts at k*0x10008 + 8.
    """
    if path.lower().endswith(".digbin"):
        return unpack_digbin(path)
    raw = open(path, "rb").read()
    if len(raw) == 16 * 0x10008:
        return b"".join(raw[k * 0x10008 + 8:k * 0x10008 + 8 + 0x10000]
                        for k in range(16))
    return raw


def survey(path, name):
    img = load_image(path)
    nb = len(img) // 0x10000
    banks = banks_of(img)
    print("=" * 76)
    print("%-12s  %8d bytes  %2d banks" % (name, len(img), nb))
    print("=" * 76)
    tbl = [p1_table(b) for b in banks]
    print("  P1 bank-select table (0x0200): %d/%d banks have all 16 entries"
          % (sum(1 for t in tbl if t == 16), nb))
    # code-space vs xram coefficient streams
    sites = stream_sites(img)
    by_src = {}
    for b, o, s in sites:
        by_src.setdefault(s, []).append((b, o))
    for s, lst in sorted(by_src.items()):
        print("  stream source %-5s : %d site(s)" % (s, len(lst)))
        for b, o in lst[:6]:
            base = stream_source_base(img, bank=b, off=o) if s == "code" else None
            print("        bank %2d  offset 0x%04X%s" % (
                b, o, ("  base 0x%04X" % base) if base else ""))
    # DSP port usage
    counts = {}
    for p in DSP_PORTS:
        n = img.count(struct.pack(">BH", 0x90, p))
        if n:
            counts[p] = n
    print("  DSP ports: " + "  ".join("0x%04X x%d" % (p, n)
                                       for p, n in sorted(counts.items())))
    # strings of interest
    for pat in (b"USER_CAB", b"USER 1", b"IMPULSE", b"Jcabinet"):
        offs = []
        i = img.find(pat)
        while i >= 0 and len(offs) < 5:
            offs.append(i)
            i = img.find(pat, i + 1)
        if offs:
            print("  %-10s at %s" % (pat.decode(), [hex(o) for o in offs]))
    # free space
    free = []
    for k, b in enumerate(banks):
        run = 0
        best = 0
        for x in b:
            run = run + 1 if x == 0xFF else 0
            best = max(best, run)
        free.append(best)
    print("  largest 0xFF run per bank: " +
          " ".join("%d:%#X" % (k, v) for k, v in enumerate(free)))
    print()
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("images", nargs="*")
    args = ap.parse_args()

    targets = args.images or []
    if not targets:
        for n in ("rp1000V10", "rp1000V11", "rp1000V12",
                  "rp355V11", "rp355V13", "rp355V14"):
            p = os.path.join(RES, "NetUpdaterClone.Resources.Firmware.%s.DigBin" % n)
            if os.path.exists(p):
                targets.append(p)
    for p in targets:
        name = os.path.basename(p).split("Firmware.")[-1].replace(".DigBin", "").replace(".bin", "")
        try:
            survey(p, name)
        except Exception as e:
            print("%s: ERROR %s" % (name, e))
    return 0


if __name__ == "__main__":
    sys.exit(main())
