#!/usr/bin/env python3
"""Definitive comparison of the DSP-facing flash blocks.

True stream sources (from the MOVC source constant in each image's stream loop):
  RP500  bank14 0x2DC2   bank15 0x2E3B
  V20    bank14 0x317D   bank15 0x3588
  C48    bank14 0x31E3   bank15 0x35F5
  C63    bank14 0x31F3   bank15 0x3666

113-byte register-init sources (from the 0xD000..0xD070 copy loop):
  RP500  bank14 0x2C80   bank15 0x2CBB
  V20    bank14 0x3100
  C48    bank14 0x3160   (needs payload16 extraction)
  C63    bank14 0x3170   (needs payload16 extraction)
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FW = os.path.join(ROOT, "01_source_firmware")


def load(name):
    with open(os.path.join(FW, name), "rb") as f:
        return f.read()


def payload16(img):
    return b"".join(img[k * 0x10008 + 8:k * 0x10008 + 0x10008] for k in range(16))


def blk(img, bank, off, n):
    b = bank * 0x10000
    return img[b + off:b + off + n]


def hexdump(data):
    out = []
    for i in range(0, len(data), 16):
        c = data[i:i + 16]
        out.append(f"  {i:03X}  " + " ".join(f"{b:02X}" for b in c).ljust(47) +
                   "  " + "".join(chr(b) if 32 <= b < 127 else "." for b in c))
    return "\n".join(out)


def cmp(a, b):
    d = [(i, x, y) for i, (x, y) in enumerate(zip(a, b)) if x != y]
    return len(a) - len(d), d


def main():
    rp = load("rp500_v20.bin")
    g20 = load("gsp1101_v20.bin")
    c48 = payload16(load("c48_fw.bin"))
    c63 = payload16(load("c63_fw.bin"))

    print("=" * 78)
    print("A. 24-byte flash->DSP stream descriptor (the cabinet-adjacent block)")
    print("=" * 78)

    streams = {
        "RP500 bank14:0x2DC2": blk(rp, 14, 0x2DC2, 24),
        "RP500 bank15:0x2E3B": blk(rp, 15, 0x2E3B, 24),
        "V20   bank14:0x317D": blk(g20, 14, 0x317D, 24),
        "V20   bank15:0x3588": blk(g20, 15, 0x3588, 24),
        "C48   bank14:0x31E3": blk(c48, 14, 0x31E3, 24),
        "C48   bank15:0x35F5": blk(c48, 15, 0x35F5, 24),
        "C63   bank14:0x31F3": blk(c63, 14, 0x31F3, 24),
        "C63   bank15:0x3666": blk(c63, 15, 0x3666, 24),
    }
    for n, d in streams.items():
        print(f"\n{n}")
        print(hexdump(d))

    print("\n" + "-" * 78)
    print("Pairwise vs RP500 bank15:0x2E3B")
    ref = streams["RP500 bank15:0x2E3B"]
    for n, d in streams.items():
        if n.startswith("RP500"):
            continue
        same, diffs = cmp(ref, d)
        print(f"  {n}: {same}/24 identical" +
              ("" if not diffs else "  diffs: " +
               ", ".join(f"{i:02X}({x:02X}!={y:02X})" for i, x, y in diffs)))

    print("\n" + "=" * 78)
    print("B. 113-byte DSP register-init block (0xD000..0xD070, skip 0xD059)")
    print("=" * 78)

    inits = {
        "RP500 bank14:0x2C80": blk(rp, 14, 0x2C80, 113),
        "RP500 bank15:0x2CBB": blk(rp, 15, 0x2CBB, 113),
        "V20   bank14:0x3100": blk(g20, 14, 0x3100, 113),
        "C48   bank14:0x3160": blk(c48, 14, 0x3160, 113),
        "C63   bank14:0x3170": blk(c63, 14, 0x3170, 113),
    }
    for n, d in inits.items():
        print(f"\n{n}")
        print(hexdump(d))

    print("\n" + "-" * 78)
    print("Pairwise vs RP500 bank15:0x2CBB")
    ref = inits["RP500 bank15:0x2CBB"]
    for n, d in inits.items():
        if n.startswith("RP500"):
            continue
        same, diffs = cmp(ref, d)
        print(f"\n  {n}: {same}/113 identical ({100.0 * same / 113:.1f}%)")
        if diffs:
            print("    diffs: " + ", ".join(f"{i:02X}" for i, _, _ in diffs))
        else:
            print("    BYTE-IDENTICAL")

    print("\n" + "=" * 78)
    print("C. Are the init blocks identical *within* each GSP generation?")
    print("=" * 78)
    print(f"  V20 0x3100 vs C48 0x3160: {cmp(inits['V20   bank14:0x3100'], inits['C48   bank14:0x3160'])[0]}/113")
    print(f"  C48 0x3160 vs C63 0x3170: {cmp(inits['C48   bank14:0x3160'], inits['C63   bank14:0x3170'])[0]}/113")
    print(f"  V20 0x3100 vs C63 0x3170: {cmp(inits['V20   bank14:0x3100'], inits['C63   bank14:0x3170'])[0]}/113")


if __name__ == "__main__":
    main()
