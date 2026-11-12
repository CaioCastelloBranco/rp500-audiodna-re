#!/usr/bin/env python3
"""Cluster-level firmware diff.

Usage:
    python diff_clusters.py A.bin B.bin [--gsp-container] [--gap N] [--top N]

--gsp-container : inputs are 0x100080-byte updater images (body0 + 15 x [8-byte
                  descriptor + body] + 8-byte trailer). They are flattened to
                  16 x 64 KB before comparison.
--gap           : merge differing runs separated by <= N equal bytes (default 16)
--top           : number of clusters to print (default 40)

A cluster is a maximal differing run on the *union* of both images; equal bytes
between two clusters are counted as "gap" and merged into one cluster.
"""
import argparse
import sys

BANK = 0x10000


def flatten_gsp(data: bytes) -> bytes:
    if len(data) != 0x100080:
        raise SystemExit(f"not a 0x100080 container: {len(data):#x}")
    out = bytearray(BANK)
    out[:BANK] = data[:BANK]
    for k in range(1, 16):
        start = BANK + (k - 1) * (BANK + 8) + 8
        out += data[start:start + BANK]
    if len(out) != 16 * BANK:
        raise SystemExit(f"flatten produced {len(out):#x}")
    return bytes(out)


def clusters(a: bytes, b: bytes, gap: int):
    n = min(len(a), len(b))
    runs = []
    i = 0
    while i < n:
        if a[i] == b[i]:
            i += 1
            continue
        start = i
        last_diff = i
        i += 1
        while i < n and (a[i] != b[i] or i - last_diff <= gap):
            if a[i] != b[i]:
                last_diff = i
            i += 1
        runs.append((start, last_diff + 1))
    if len(a) != len(b):
        runs.append((n, max(len(a), len(b))))
    return runs


def printable(data: bytes, minlen=6):
    out = []
    cur = bytearray()
    start = 0
    for idx, ch in enumerate(data):
        if 32 <= ch < 127:
            if not cur:
                start = idx
            cur.append(ch)
        else:
            if len(cur) >= minlen:
                out.append((start, cur.decode("ascii")))
            cur = bytearray()
    if len(cur) >= minlen:
        out.append((start, cur.decode("ascii")))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--gsp-container", action="store_true")
    ap.add_argument("--gap", type=int, default=16)
    ap.add_argument("--top", type=int, default=40)
    args = ap.parse_args()

    a = open(args.a, "rb").read()
    b = open(args.b, "rb").read()
    if args.gsp_container:
        a = flatten_gsp(a)
        b = flatten_gsp(b)
    if len(a) != len(b):
        print(f"WARNING: size mismatch {len(a):#x} vs {len(b):#x}")

    runs = clusters(a, b, args.gap)
    diff_bytes = sum(e - s for s, e in runs)
    print(f"{args.a}  vs  {args.b}")
    print(f"image {len(a):#x}   differing bytes {diff_bytes} "
          f"({100.0 * diff_bytes / len(a):.2f}%)   clusters {len(runs)} (gap<={args.gap})")

    per_bank = {}
    for s, e in runs:
        for bank in range(s // BANK, (e - 1) // BANK + 1):
            lo = max(s, bank * BANK)
            hi = min(e, (bank + 1) * BANK)
            per_bank[bank] = per_bank.get(bank, 0) + (hi - lo)
    print("\nper-bank differing bytes:")
    for bank in range(16):
        if bank in per_bank:
            print(f"  bank {bank:02d}  {per_bank[bank]:7d}  ({100.0 * per_bank[bank] / BANK:5.2f}%)")

    print(f"\ntop {args.top} clusters:")
    for s, e in sorted(runs, key=lambda r: r[1] - r[0], reverse=True)[:args.top]:
        bank = s // BANK
        print(f"\n  bank {bank:02d}  off 0x{s % BANK:04X}  len {e - s}"
              f"  flat 0x{s:05X}-0x{e:05X}")
        for off, text in printable(a[s:e] + b"\x00" + b[s:e])[:6]:
            print(f"      A/B str: {text!r}")
        print(f"      A: {a[s:min(e, s + 24)].hex(' ')}")
        print(f"      B: {b[s:min(e, s + 24)].hex(' ')}")


if __name__ == "__main__":
    sys.exit(main())
