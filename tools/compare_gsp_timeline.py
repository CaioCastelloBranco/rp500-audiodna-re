#!/usr/bin/env python3
"""Timeline comparison of the DSP-facing interface across every GSP1101 build.

For each image:
  - locate the code-space stream routine (MOVC -> 0xD070) and its source base
  - count XRAM-sourced stores to 0xD070 (the variable-length channel)
  - locate the 113-byte register-init copy loop and its source base
  - dump the 24-byte descriptor and the 113-byte init block
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FW = os.path.join(ROOT, "01_source_firmware")


def load(name):
    with open(os.path.join(FW, name), "rb") as f:
        return f.read()


def payload16(img):
    return b"".join(img[k * 0x10008 + 8:k * 0x10008 + 0x10008] for k in range(16))


def find_all(img, pat):
    out, i = [], 0
    while True:
        j = img.find(pat, i)
        if j < 0:
            return out
        out.append(j)
        i = j + 1


def locs(h, n=10):
    return [f"b{x >> 16}:{x & 0xFFFF:04X}" for x in h[:n]]


def stream_info(img):
    """Return (sites, [(site, base, lo, hi)])."""
    # core: MOVC A,@A+DPTR ; MOV DPTR,#D070 ; MOVX @DPTR,A
    sites = find_all(img, bytes([0x93, 0x90, 0xD0, 0x70, 0xF0]))
    out = []
    for s in sites:
        # look back up to 20 bytes for ADD A,#lo ; MOV DPL,A ; MOV A,#hi ; ADDC A,R6
        win = img[max(0, s - 24):s]
        m = None
        for k in range(len(win) - 8):
            if win[k] == 0x24 and win[k + 1] == 0xF5 and win[k + 2] == 0x82 and win[k + 3] == 0x74:
                hi = win[k + 4]
                if k + 5 < len(win) and win[k + 5] == 0x3E:
                    m = (win[k + 1], hi)
        if m:
            lo, hi = m
            out.append((s, (hi << 8) | lo, lo, hi))
        else:
            out.append((s, None, None, None))
    return sites, out


def xram_count(img):
    sig = bytes([0x90, 0xD0, 0x70, 0xF0])
    hits = find_all(img, sig)
    code = xram = 0
    for h in hits:
        w = img[max(0, h - 30):h]
        if w.rfind(b"\x93") > w.rfind(b"\xe0"):
            code += 1
        else:
            xram += 1
    return len(hits), code, xram


def init_block(img):
    """Locate the 0xD000+index copy loop and return (site, base)."""
    # C3 94 71 ... 64 59 4E ... 90 <lo> <hi> 93
    for m in re.finditer(rb"\xC3\x94\x71", img):
        o = m.start()
        win = img[o:o + 60]
        if b"\x64\x59\x4e" not in win:
            continue
        # find MOV DPTR,#xxxx after the skip test
        mm = re.search(rb"\x90(.)(.)\x93", win)
        if mm:
            base = (mm.group(2)[0] << 8) | mm.group(1)[0]
            return o, base
    return None, None


def main():
    images = [
        ("GSP v11  (oldest)", "gsp1101_v11.bin", False),
        ("GSP v12", "gsp1101_v12.bin", False),
        ("GSP v13", "gsp1101_v13.bin", False),
        ("GSP v20", "gsp1101_v20.bin", False),
        ("GSP vC20", "gsp1101_vC20.bin", False),
        ("GSP C48", "c48_fw.bin", True),
        ("GSP C63  (IR build)", "c63_fw.bin", True),
        ("RP500 v20", "rp500_v20.bin", False),
    ]

    print("=" * 96)
    print("DSP-facing interface across the GSP1101 timeline (oldest first)")
    print("=" * 96)

    rows = []
    for label, name, interleaved in images:
        raw = load(name)
        img = payload16(raw) if interleaved else raw
        sites, info = stream_info(img)
        total, code, xram = xram_count(img)
        isite, ibase = init_block(img)
        rows.append((label, name, img, sites, info, total, code, xram, isite, ibase))

        print(f"\n{label}  ({name})")
        print(f"  code-space stream sites: {locs(sites)}")
        for s, base, lo, hi in info:
            if base is not None:
                print(f"    {locs([s])[0]}  base=0x{base:04X}  (lo=0x{lo:02X} hi=0x{hi:02X})")
        print(f"  0xD070 stores: total={total}  code-space={code}  XRAM={xram}")
        if isite is not None:
            print(f"  init copy loop: b{isite >> 16}:{isite & 0xFFFF:04X}  source base=0x{ibase:04X}")
        else:
            print("  init copy loop: NOT FOUND")

    print("\n" + "=" * 96)
    print("Summary table")
    print("=" * 96)
    print(f"{'build':22s} {'stream base':12s} {'XRAM':5s} {'init base':10s}")
    for label, name, img, sites, info, total, code, xram, isite, ibase in rows:
        bases = ",".join(f"0x{b:04X}" for _, b, _, _ in info if b is not None)
        ib = f"0x{ibase:04X}" if ibase is not None else "-"
        print(f"{label:22s} {bases:12s} {xram:<5d} {ib:10s}")

    # descriptor + init dumps for the oldest build
    print("\n" + "=" * 96)
    print("Oldest build (v11) vs RP500: descriptor and init block")
    print("=" * 96)

    def blk(img, base, n):
        return img[base:base + n]

    v11 = load("gsp1101_v11.bin")
    rp = load("rp500_v20.bin")

    _, info11 = stream_info(v11)
    bases11 = [b for _, b, _, _ in info11 if b is not None]
    print("\nv11 stream bases:", [f"0x{b:04X}" for b in bases11])
    for b in bases11[:2]:
        d = blk(v11, b, 24)
        print(f"  v11 0x{b:04X}: " + " ".join(f"{x:02X}" for x in d))
    rd = blk(rp, 15 * 0x10000 + 0x2E3B, 24)
    print("  RP500      : " + " ".join(f"{x:02X}" for x in rd))

    isite11, ibase11 = init_block(v11)
    print(f"\nv11 init base: 0x{ibase11:04X}")
    if ibase11:
        d = blk(v11, ibase11, 113)
        print("  v11 init  : " + " ".join(f"{x:02X}" for x in d))
    ri = blk(rp, 15 * 0x10000 + 0x2CBB, 113)
    print("  RP500 init: " + " ".join(f"{x:02X}" for x in ri))


if __name__ == "__main__":
    main()
