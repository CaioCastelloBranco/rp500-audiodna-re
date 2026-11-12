#!/usr/bin/env python3
"""Two-chip test for the GSP1101 AudioDNA2 pair.

Question: does the GSP1101 firmware address its two AudioDNA2 chips
independently, and does the user-IR path target one of them?

Method (static only):
  1. Enumerate every store to the DSP data port 0xD070 and classify the
     source as code space (MOVC) or XRAM (MOVX).
  2. Show the XRAM sites are 2 interrupt handlers replicated across the
     16 code banks, and dump both handlers' source/index/length cells.
  3. Compare the oldest GSP build (v11) with the IR build (C63).
  4. Check for a chip-select register: 0xFDFC (RP500-only?), 0xE400,
     0xE200, 0xEC40.
  5. Check whether the RP500 has the GSP-only 0xE400/0xEC40 path.
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FW = os.path.join(ROOT, "01_source_firmware")

IMAGES = {
    "GSP v11 (oldest)": ("gsp1101_v11.bin", False),
    "GSP v20": ("gsp1101_v20.bin", False),
    "GSP C48": ("c48_fw.bin", True),
    "GSP C63 (IR)": ("c63_fw.bin", True),
    "RP500 v20": ("rp500_v20.bin", False),
}


def load(name, interleaved):
    with open(os.path.join(FW, name), "rb") as f:
        raw = f.read()
    if interleaved:
        return b"".join(raw[k * 0x10008 + 8:k * 0x10008 + 0x10008] for k in range(16))
    return raw


def find_all(img, pat):
    out, i = [], 0
    while True:
        j = img.find(pat, i)
        if j < 0:
            return out
        out.append(j)
        i = j + 1


def loc(x):
    return "b%d:%04X" % (x >> 16, x & 0xFFFF)


def d070_sites(img):
    """Every MOV DPTR,#D070 ; MOVX @DPTR,A, classified by the last read."""
    sig = bytes([0x90, 0xD0, 0x70, 0xF0])
    rows = []
    for h in find_all(img, sig):
        w = img[max(0, h - 40):h]
        kind = "XRAM" if w.rfind(b"\xe0") > w.rfind(b"\x93") else "CODE"
        rows.append((h, kind))
    return rows


def handler_cells(img, handler_off, n=90):
    """Return the XRAM addresses referenced inside a handler window."""
    seg = img[handler_off:handler_off + n]
    cells = []
    for m in re.finditer(rb"\x90(.)(.)", seg):
        hi, lo = m.group(1)[0], m.group(2)[0]
        if hi in (0x1F, 0x20, 0x21, 0x24, 0x26, 0x27, 0x2B, 0x32):
            cells.append((hi << 8) | lo)
    seen = []
    for c in cells:
        if c not in seen:
            seen.append(c)
    return seen


def main():
    print("=" * 78)
    print("1. Stores to the DSP data port 0xD070")
    print("=" * 78)
    for label, (name, inter) in IMAGES.items():
        img = load(name, inter)
        rows = d070_sites(img)
        code = [x for x, k in rows if k == "CODE"]
        xram = [x for x, k in rows if k == "XRAM"]
        banks = sorted({x >> 16 for x in xram})
        print("%-18s total=%3d  code=%2d  xram=%2d  xram-banks=%s"
              % (label, len(rows), len(code), len(xram),
                 "%d..%d (%d)" % (banks[0], banks[-1], len(banks)) if banks else "-"))
        print("    code sites: %s" % ", ".join(loc(x) for x in code))

    print()
    print("=" * 78)
    print("2. The two XRAM handlers (C63, bank 0) read the SAME stream")
    print("=" * 78)
    c63 = load("c63_fw.bin", True)
    for h in (0x2F10, 0x3070):
        print("  handler at %s references: %s"
              % (loc(h), ", ".join("0x%04X" % c for c in handler_cells(c63, h))))

    print()
    print("=" * 78)
    print("3. Oldest (v11) vs IR build (C63): same transport, new addresses")
    print("=" * 78)
    v11 = load("gsp1101_v11.bin", False)
    for label, img, h in (("v11", v11, 0x26A0), ("C63", c63, 0x2F49)):
        print("  %-4s handler %s references: %s"
              % (label, loc(h), ", ".join("0x%04X" % c for c in handler_cells(img, h - 0x20))))

    print()
    print("=" * 78)
    print("4. Chip-select candidates")
    print("=" * 78)
    probes = {
        "0xFDFC": bytes([0x90, 0xFD, 0xFC]),
        "0xE400": bytes([0x90, 0xE4, 0x00]),
        "0xEC40": bytes([0x90, 0xEC, 0x40]),
        "0xE200": bytes([0x90, 0xE2, 0x00]),
    }
    for label, (name, inter) in IMAGES.items():
        img = load(name, inter)
        parts = []
        for pname, pat in probes.items():
            parts.append("%s=%d" % (pname, len(find_all(img, pat))))
        print("  %-18s %s" % (label, "  ".join(parts)))

    print()
    print("  Immediate values written to 0xE400 (GSP-only two-select):")
    for label, (name, inter) in IMAGES.items():
        img = load(name, inter)
        vals = sorted({m.group(1)[0] for m in re.finditer(
            rb"\x90\xE4\x00\x74(.)\xF0", img)})
        print("    %-18s %s" % (label, ["0x%02X" % v for v in vals] or "none"))

    print()
    print("=" * 78)
    print("5. Does the IR handler touch a chip-select port?")
    print("=" * 78)
    # Window covering both C63 handlers
    seg = c63[0x2F10:0x2F10 + 0x60] + c63[0x3070:0x3070 + 0x60]
    for pname, pat in (("E000", bytes([0x90, 0xE0, 0x00])),
                       ("E200", bytes([0x90, 0xE2, 0x00])),
                       ("E400", bytes([0x90, 0xE4, 0x00])),
                       ("D070", bytes([0x90, 0xD0, 0x70]))):
        print("  %s in the two IR handlers: %d" % (pname, len(find_all(seg, pat))))
    print("  (E000 is used only for the |0x80 / |0x40 flow-control command.)")


if __name__ == "__main__":
    main()
