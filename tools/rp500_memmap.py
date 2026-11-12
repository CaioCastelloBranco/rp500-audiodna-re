#!/usr/bin/env python3
"""Map the memory the RP500 firmware actually touches.

S2 (roadmap): find where the RP500 stores its 100 user presets.

The firmware has flash-subsystem strings ("FLERR", "BUSY ", "ERASE ",
"FACT RST"), so it drives some kind of non-volatile store itself.  This script
maps *what* it touches, to answer the question from the firmware's own
behaviour rather than from guesswork:

  * every XDATA address loaded into DPTR, split by whether the next
    instruction READS or WRITES it;
  * the DSP window (0xD000-0xDFFF) separately, since that is the AudioDNA2;
  * the code-space (MOVC) address ranges that are read as data.

Usage:
    python rp500_memmap.py [--bank N]
"""
import argparse
import collections
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FW = os.path.join(ROOT, "01_source_firmware", "rp500_v20.bin")
sys.path.insert(0, HERE)
from d51 import disasm  # noqa: E402

BANK = 0x10000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bank", type=int, default=None,
                    help="only this bank (default: all 16)")
    args = ap.parse_args()

    img = open(FW, "rb").read()
    banks = range(16) if args.bank is None else [args.bank]

    dptr_loads = collections.Counter()      # address -> how often loaded
    writes = collections.Counter()           # address -> how often written
    reads = collections.Counter()
    movc_ranges = collections.defaultdict(list)

    for k in banks:
        b = img[k * BANK:(k + 1) * BANK]
        ins = disasm(b, 0, 0, BANK)
        # track the address currently in DPTR
        cur = None
        for addr, raw, txt in ins:
            m = re.match(r"^MOV DPTR,#([0-9A-Fa-f]+)h$", txt)
            if m:
                cur = int(m.group(1), 16)
                dptr_loads[cur] += 1
                continue
            if txt == "INC DPTR":
                if cur is not None:
                    cur = (cur + 1) & 0xFFFF
                continue
            if txt.startswith("MOVX @DPTR"):
                if cur is not None:
                    writes[cur] += 1
                cur = None
                continue
            if txt.startswith("MOVX A,@DPTR"):
                if cur is not None:
                    reads[cur] += 1
                cur = None
                continue
            if txt.startswith("MOVC"):
                if cur is not None:
                    movc_ranges[k].append((cur, addr))
                cur = None
                continue
            cur = None

    def band(lo, hi):
        return sum(v for a, v in writes.items() if lo <= a <= hi)

    print("=" * 78)
    print("RP500 XDATA WRITE MAP  (writes to XDATA @DPTR)")
    print("=" * 78)
    print("total distinct DPTR targets written : %d" % len(writes))
    print("total writes                       : %d" % sum(writes.values()))
    print()
    buckets = [(0x0000, 0x0FFF, "0x0000-0x0FFF"),
               (0x1000, 0x1FFF, "0x1000-0x1FFF"),
               (0x2000, 0x2FFF, "0x2000-0x2FFF"),
               (0x3000, 0x3FFF, "0x3000-0x3FFF"),
               (0x4000, 0x4FFF, "0x4000-0x4FFF"),
               (0x5000, 0x5FFF, "0x5000-0x5FFF"),
               (0x6000, 0x6FFF, "0x6000-0x6FFF"),
               (0x7000, 0x7FFF, "0x7000-0x7FFF"),
               (0x8000, 0x8FFF, "0x8000-0x8FFF"),
               (0x9000, 0x9FFF, "0x9000-0x9FFF"),
               (0xA000, 0xAFFF, "0xA000-0xAFFF"),
               (0xB000, 0xBFFF, "0xB000-0xBFFF"),
               (0xC000, 0xCFFF, "0xC000-0xCFFF"),
               (0xD000, 0xDFFF, "0xD000-0xDFFF  (DSP window)"),
               (0xE000, 0xEFFF, "0xE000-0xEFFF"),
               (0xF000, 0xFFFF, "0xF000-0xFFFF")]
    for lo, hi, lbl in buckets:
        w = band(lo, hi)
        r = sum(v for a, v in reads.items() if lo <= a <= hi)
        print("  %-30s writes=%-6d reads=%-6d" % (lbl, w, r))

    print()
    print("=" * 78)
    print("MOST-WRITTEN XDATA ADDRESSES")
    print("=" * 78)
    for a, n in writes.most_common(30):
        print("  0x%04X  x%d" % (a, n))

    print()
    print("=" * 78)
    print("MOST-READ XDATA ADDRESSES")
    print("=" * 78)
    for a, n in reads.most_common(20):
        print("  0x%04X  x%d" % (a, n))

    print()
    print("=" * 78)
    print("CODE-SPACE (MOVC) SOURCE RANGES PER BANK")
    print("=" * 78)
    for k in sorted(movc_ranges):
        vals = sorted(set(a for a, _ in movc_ranges[k]))
        if not vals:
            continue
        runs = []
        s = p = vals[0]
        for v in vals[1:]:
            if v == p + 1:
                p = v
                continue
            runs.append((s, p))
            s = p = v
        runs.append((s, p))
        big = [r for r in runs if r[1] - r[0] >= 256]
        print("  bank %-2d  %d distinct MOVC bases; ranges >=256 bytes:" % (k, len(vals)))
        for a, b in big[:12]:
            print("       0x%04X..0x%04X  (%d bytes)" % (a, b, b - a + 1))


if __name__ == "__main__":
    main()
