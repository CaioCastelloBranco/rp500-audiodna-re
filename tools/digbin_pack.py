#!/usr/bin/env python3
"""Pack / unpack the DigiTech .DigBin firmware container.

Layout (both RP500 and GSP1101, 1 MB images):
    12-byte file header  00 5C 00 05 00 00 00 00 00 01 00 00
    bank 0               64 KB
    for k = 1..15:
        8-byte descriptor  00 kk 00 00 00 01 00 00
        64 KB bank body
Total 0x100084 bytes. No checksum, no signature.

Usage:
    python digbin_pack.py verify  ORIGINAL.DigBin
    python digbin_pack.py unpack  IN.DigBin OUT.bin
    python digbin_pack.py pack    IN.bin OUT.DigBin
"""
import sys

BANK = 0x10000
HEADER = bytes.fromhex("005c00050000000000010000")


def _desc(k: int) -> bytes:
    return bytes([0x00, k, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00])


def unpack(data: bytes) -> bytes:
    if len(data) != 0x100084:
        raise ValueError(f"not a 0x100084 container: {len(data):#x}")
    out = bytearray(data[12:12 + BANK])
    for k in range(1, 16):
        start = 12 + BANK + (k - 1) * (BANK + 8) + 8
        out += data[start:start + BANK]
    if len(out) != 16 * BANK:
        raise ValueError(f"unpack produced {len(out):#x}")
    return bytes(out)


def pack(flat: bytes) -> bytes:
    if len(flat) != 16 * BANK:
        raise ValueError(f"flat image must be 0x100000 bytes, got {len(flat):#x}")
    out = bytearray(HEADER)
    out += flat[:BANK]
    for k in range(1, 16):
        out += _desc(k)
        out += flat[k * BANK:(k + 1) * BANK]
    if len(out) != 0x100084:
        raise ValueError(f"pack produced {len(out):#x}")
    return bytes(out)


def verify(path: str) -> None:
    raw = open(path, "rb").read()
    flat = unpack(raw)
    if pack(flat) != raw:
        raise SystemExit("FAIL: repack is not byte-identical")
    if HEADER != raw[:12]:
        raise SystemExit("FAIL: unexpected header")
    for k in range(1, 16):
        off = 12 + BANK + (k - 1) * (BANK + 8)
        if raw[off:off + 8] != _desc(k):
            raise SystemExit(f"FAIL: descriptor {k} mismatch")
    print(f"PASS: {path} unpacks and repacks byte-identically "
          f"({len(raw):#x} bytes, 16 banks)")


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    cmd = argv[1]
    if cmd == "verify":
        verify(argv[2])
        return 0
    if cmd == "unpack":
        open(argv[3], "wb").write(unpack(open(argv[2], "rb").read()))
        print(f"wrote {argv[3]}")
        return 0
    if cmd == "pack":
        open(argv[3], "wb").write(pack(open(argv[2], "rb").read()))
        print(f"wrote {argv[3]}")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
