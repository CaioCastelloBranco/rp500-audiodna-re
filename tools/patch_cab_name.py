#!/usr/bin/env python3
"""Rename an RP500 cabinet model in the firmware image and emit a .DigBin.

The RP500 cab list is a 28-entry pointer table at bank 4:0x478E pointing at
9-byte records (8 characters + NUL) starting at bank 4:0x3486. The record *is*
the name shown in the menu; there is no separate long-name table in the RP500
image, so patching the record is sufficient.

Usage:
    python patch_cab_name.py --old DIGISPKR --new CAIO4X12 \
        [--image 01_source_firmware/rp500_v20.bin] \
        [--outdir 09_builds] [--dry-run]
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from digbin_pack import pack  # noqa: E402

BANK = 0x10000
CAB_BANK = 4
POINTER_TABLE = 0x478E
NAME_AREA = 0x3486
COUNT = 28
RECLEN = 9


def load_names(bank: bytes):
    names = []
    for i in range(COUNT):
        p = (bank[POINTER_TABLE + 2 * i] << 8) | bank[POINTER_TABLE + 2 * i + 1]
        rec = bank[p:p + RECLEN]
        if len(rec) != RECLEN:
            raise SystemExit(f"record {i} at 0x{p:04X} runs past bank end")
        names.append((i, p, rec))
    return names


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--image", default="01_source_firmware/rp500_v20.bin")
    ap.add_argument("--outdir", default="09_builds")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    old = args.old.encode("ascii")
    new = args.new.encode("ascii")
    if len(old) > 8 or len(new) > 8:
        raise SystemExit("names must be at most 8 characters (9-byte record incl. NUL)")

    raw = open(args.image, "rb").read()
    if len(raw) != 16 * BANK:
        raise SystemExit(f"expected a 16 x 64 KB flat image, got {len(raw):#x}")

    bank = bytearray(raw[CAB_BANK * BANK:(CAB_BANK + 1) * BANK])
    names = load_names(bank)

    hits = [n for n in names if n[2].rstrip(b"\x00") == old]
    if len(hits) != 1:
        raise SystemExit(f"expected exactly one cab named {args.old!r}, found {len(hits)}")
    idx, off, rec = hits[0]

    # Guard: the name bytes must be unique in the whole image, so the patch
    # cannot silently hit code or a duplicate table.
    occurrences = raw.count(old)
    if occurrences != 1:
        raise SystemExit(f"name {args.old!r} occurs {occurrences} times in the image; "
                         "refusing to patch blindly")

    patch = new.ljust(8, b" ")[:8] + b"\x00"
    assert len(patch) == RECLEN

    flat = bytearray(raw)
    base = CAB_BANK * BANK + off
    before = bytes(flat[base:base + RECLEN])
    flat[base:base + RECLEN] = patch

    print(f"cab index {idx}  bank {CAB_BANK} off 0x{off:04X}  flat 0x{base:05X}")
    print(f"  before: {before}")
    print(f"  after : {patch}")
    print(f"  pointer table entry {idx} unchanged: "
          f"{(bank[POINTER_TABLE + 2*idx] << 8) | bank[POINTER_TABLE + 2*idx + 1]:#06x}")

    changed = sum(1 for a, b in zip(raw, bytes(flat)) if a != b)
    diff_offsets = [i for i, (a, b) in enumerate(zip(raw, bytes(flat))) if a != b]
    print(f"  bytes changed in image: {changed} at {[hex(o) for o in diff_offsets]}")

    os.makedirs(args.outdir, exist_ok=True)
    stem = f"rp500_v20_{new.decode('ascii').strip().lower().replace(' ', '_')}"
    bin_path = os.path.join(args.outdir, stem + ".bin")
    digbin_path = os.path.join(args.outdir, stem + ".DigBin")

    if args.dry_run:
        print("dry run: nothing written")
        return 0

    open(bin_path, "wb").write(bytes(flat))
    open(digbin_path, "wb").write(pack(bytes(flat)))
    print(f"wrote {bin_path} ({len(flat)} bytes)")
    print(f"wrote {digbin_path} ({os.path.getsize(digbin_path)} bytes)")

    # Sanity: the packed container must round-trip to the patched flat image.
    from digbin_pack import unpack
    if unpack(open(digbin_path, "rb").read()) != bytes(flat):
        raise SystemExit("FAIL: container does not round-trip")
    print("round-trip check: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
