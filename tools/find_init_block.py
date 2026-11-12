#!/usr/bin/env python3
"""Locate the DSP register-init copy loop (writes 0xD000..0xD070) in each
image and report the flash source base it copies from.
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FW = os.path.join(ROOT, "01_source_firmware")


def load(name):
    with open(os.path.join(FW, name), "rb") as f:
        return f.read()


def find_all(img, pat):
    out, i = [], 0
    while True:
        j = img.find(pat, i)
        if j < 0:
            return out
        out.append(j)
        i = j + 1


def locs(hits, n=20):
    return [f"b{h >> 16}:{h & 0xFFFF:04X}" for h in hits[:n]]


def main():
    imgs = {
        "rp500_v20": load("rp500_v20.bin"),
        "gsp1101_v20": load("gsp1101_v20.bin"),
        "c48_fw": load("c48_fw.bin"),
        "c63_fw": load("c63_fw.bin"),
    }

    print("=" * 78)
    print("MOV DPTR,#D000  (90 D0 00)  and  MOV DPTR,#D059 (90 D0 59)")
    for name, img in imgs.items():
        print(f"\n  {name}")
        for target, pat in (("D000", bytes([0x90, 0xD0, 0x00])),
                            ("D059", bytes([0x90, 0xD0, 0x59])),
                            ("D058", bytes([0x90, 0xD0, 0x58])),
                            ("D05A", bytes([0x90, 0xD0, 0x5A]))):
            h = find_all(img, pat)
            print(f"    {target}: n={len(h):3d}  {locs(h, 12)}")

    print("=" * 78)
    print("RP500: code referencing source 0x2C80 / 0x2CBB (MOV DPTR,#2C80 / 2CBB)")
    rp = imgs["rp500_v20"]
    for pat, label in ((bytes([0x90, 0x2C, 0x80]), "DPTR,#2C80"),
                       (bytes([0x90, 0x2C, 0xBB]), "DPTR,#2CBB"),
                       (bytes([0x90, 0x2C, 0x7F]), "DPTR,#2C7F"),
                       (bytes([0x90, 0x2C, 0xBA]), "DPTR,#2CBA")):
        h = find_all(rp, pat)
        print(f"  {label}: n={len(h)}  {locs(h)}")

    print("=" * 78)
    print("RP500: any 16-bit immediate equal to 0x2C80 or 0x2CBB")
    for val in (0x2C80, 0x2CBB):
        lo, hi = val & 0xFF, val >> 8
        for order, lab in ((bytes([hi, lo]), "BE"), (bytes([lo, hi]), "LE")):
            h = find_all(rp, order)
            print(f"  0x{val:04X} {lab}: n={len(h)}  {locs(h, 10)}")


if __name__ == "__main__":
    main()
