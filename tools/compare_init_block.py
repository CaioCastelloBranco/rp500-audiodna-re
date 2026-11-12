#!/usr/bin/env python3
"""Byte-compare the 113-byte DSP register-init block across all four images,
plus the 24-byte stream descriptor, and score how much of the DSP-facing
interface is literally shared.
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FW = os.path.join(ROOT, "01_source_firmware")


def load(name):
    with open(os.path.join(FW, name), "rb") as f:
        return f.read()


def blk(img, bank, off, n):
    b = bank * 0x10000
    return img[b + off:b + off + n]


def hexdump(data):
    out = []
    for i in range(0, len(data), 16):
        chunk = data[i:i + 16]
        hx = " ".join(f"{b:02X}" for b in chunk)
        txt = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        out.append(f"  {i:03X}  {hx:<47}  {txt}")
    return "\n".join(out)


def compare(a, b):
    diffs = [(i, x, y) for i, (x, y) in enumerate(zip(a, b)) if x != y]
    return len(diffs), diffs


def main():
    rp = load("rp500_v20.bin")
    g20 = load("gsp1101_v20.bin")
    c48 = load("c48_fw.bin")
    c63 = load("c63_fw.bin")

    print("=" * 78)
    print("113-byte DSP register-init block")
    print("=" * 78)

    init = {
        "RP500 bank14:0x2C80": blk(rp, 14, 0x2C80, 113),
        "RP500 bank15:0x2CBB": blk(rp, 15, 0x2CBB, 113),
        "GSP V20 bank14:0x3100": blk(g20, 14, 0x3100, 113),
        "GSP C48 bank14:0x3160": blk(c48, 14, 0x3160, 113),
        "GSP C63 bank14:0x3170": blk(c63, 14, 0x3170, 113),
    }

    for name, d in init.items():
        print(f"\n{name}")
        print(hexdump(d))

    print("\n" + "=" * 78)
    print("Pairwise comparison against the RP500 block")
    ref = init["RP500 bank15:0x2CBB"]
    for name, d in init.items():
        if name.startswith("RP500"):
            continue
        nd, diffs = compare(ref, d)
        pct = 100.0 * (113 - nd) / 113
        print(f"\n  RP500 vs {name}: {113 - nd}/113 identical ({pct:.1f}%)")
        if diffs:
            print("    differing offsets: " +
                  ", ".join(f"{i:02X}({x:02X}!={y:02X})" for i, x, y in diffs[:40]))
        else:
            print("    BYTE-IDENTICAL")

    print("\n" + "=" * 78)
    print("24-byte flash->DSP stream descriptor")
    print("=" * 78)

    desc = {
        "RP500 bank14:0x2DC2": blk(rp, 14, 0x2DC2, 24),
        "RP500 bank15:0x2E3B": blk(rp, 15, 0x2E3B, 24),
        # GSP stream sources from the loader idiom
        "GSP V20 bank14:0x32F3": blk(g20, 14, 0x32F3, 24),
        "GSP V20 bank15:0x3666": blk(g20, 15, 0x3666, 24),
        "GSP C48 bank14:0x32F3": blk(c48, 14, 0x32F3, 24),
        "GSP C48 bank15:0x3666": blk(c48, 15, 0x3666, 24),
        "GSP C63 bank14:0x32F3": blk(c63, 14, 0x32F3, 24),
        "GSP C63 bank15:0x3666": blk(c63, 15, 0x3666, 24),
    }
    for name, d in desc.items():
        print(f"\n{name}")
        print(hexdump(d))


if __name__ == "__main__":
    main()
