#!/usr/bin/env python3
"""S1 — find what selects the coefficient blob (bank 14's 0x2DC2 vs bank 15's 0x2E3B).

The RP500 has two coefficient streams, one per bank:

    bank 14  source 0x2DC2 + n   (command byte 0xC0 / 0xC1)
    bank 15  source 0x2E3B + n   (command byte 0xA0)

The source base is a constant inside each routine; the *offset* comes from a
counter in XRAM.  So the "which blob" decision is made by the **caller** —
the code that runs one routine or the other.

Because every bank carries the same replicated 0x2C80-byte prefix, a call can
only reach another bank's routine through the bank-switch mechanism, so the
selector has to name both the bank and the address.

This script:
  * locates the two stream routines (by their source-base construction),
  * finds every LCALL / LJMP that targets them,
  * prints the caller's context so the deciding branch can be read.

Usage:
    python find_blob_selector.py [--image FILE] [--context 24]
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from d51 import disasm  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANK = 0x10000


def banks_of(img):
    return [img[k * BANK:(k + 1) * BANK] for k in range(len(img) // BANK)]


def find_streams(bank_bytes):
    """Find 'ADD A,#lo ; MOV 82h,A ; MOV A,#hi ; ADDC A,Rn ; MOV 83h,A'
    followed by a MOVC read and a store to the DSP data port 0xD070.
    Returns [(offset, source_base)]."""
    out = []
    for i in range(len(bank_bytes) - 16):
        if bank_bytes[i] != 0x24 or bank_bytes[i + 2] != 0xF5 or \
           bank_bytes[i + 3] != 0x82 or bank_bytes[i + 4] != 0x74 or \
           bank_bytes[i + 6] != 0x3E or bank_bytes[i + 7] != 0xF5 or \
           bank_bytes[i + 8] != 0x83:
            continue
        # a MOVC read and a store to 0xD070 within the next 12 bytes
        win = bank_bytes[i + 9:i + 22]
        if 0x93 in win and b"\x90\xd0\x70\xf0" in win:
            out.append((i, ((bank_bytes[i + 5] << 8) | bank_bytes[i + 1]) & 0xFFFF))
    return out


def callers(bank_bytes, targets, codes=("12", "02")):
    """Find LCALL/LJMP instructions pointing at any of the target addresses."""
    hits = []
    for i in range(len(bank_bytes) - 2):
        if bank_bytes[i] == 0x12:      # LCALL
            dest = (bank_bytes[i + 1] << 8) | bank_bytes[i + 2]
        elif bank_bytes[i] == 0x02:    # LJMP
            dest = (bank_bytes[i + 1] << 8) | bank_bytes[i + 2]
        else:
            continue
        if dest in targets:
            hits.append((i, dest, "LCALL" if bank_bytes[i] == 0x12 else "LJMP"))
    return hits


def show(bank_bytes, bank_no, addr, context=28):
    ins = disasm(bank_bytes, base=0, start=0)
    lo = max(0, addr - context)
    hi = addr + context
    print("   --- context around 0x%04X (bank %d) ---" % (addr, bank_no))
    for a, by, c in ins:
        if lo <= a < hi:
            mark = ">>" if a == addr else "  "
            print("   %s %04X  %-12s %s" % (mark, a, by, c))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", default=os.path.join(ROOT, "01_source_firmware",
                                                    "rp500_v20.bin"))
    ap.add_argument("--context", type=int, default=28)
    args = ap.parse_args()

    img = open(args.image, "rb").read()
    banks = banks_of(img)
    print("image: %s  (%d banks)" % (os.path.basename(args.image), len(banks)))

    for bno, b in enumerate(banks):
        streams = find_streams(b)
        if not streams:
            continue
        for off, base in streams:
            print("\nbank %2d  stream at 0x%04X  source base 0x%04X" %
                  (bno, off, base))

    # For each stream, look for callers of the routine it lives in.  The
    # routine entry is the nearest preceding RET (or the start of the bank).
    print("\n=== callers of each stream routine ===")
    for bno, b in enumerate(banks):
        streams = find_streams(b)
        for off, base in streams:
            # find the function prologue: scan back for a RET (0x22)
            entry = 0
            for j in range(off - 1, max(-1, off - 400), -1):
                if b[j] == 0x22:      # RET
                    entry = j + 1
                    break
            hits = callers(b, {entry})
            print("\nbank %2d  routine entry 0x%04X (source 0x%04X): %d direct caller(s)"
                  % (bno, entry, base, len(hits)))
            for at, dest, kind in hits[:8]:
                print("   %s at 0x%04X -> 0x%04X" % (kind, at, dest))
                show(b, bno, at, args.context)


if __name__ == "__main__":
    sys.exit(main())
