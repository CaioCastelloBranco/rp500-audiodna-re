#!/usr/bin/env python3
"""Structure-aware firmware diff: reports inserted / deleted / replaced regions
rather than raw differing bytes, so a global code shift does not swamp the result.

Usage:
    python struct_diff.py A.bin B.bin [--gsp-container] [--chunk 8] [--min 16]

Method: split both 1 MB images into 16 x 64 KB banks, then into fixed-size
chunks. Run difflib.SequenceMatcher over the chunk lists per bank. Chunk
insertions in B = code/data that exists only in B (the new feature); deletions
= content that exists only in A.
"""
import argparse
import difflib
import sys

BANK = 0x10000


def flatten_gsp(data: bytes) -> bytes:
    if len(data) != 0x100080:
        raise SystemExit(f"not a 0x100080 container: {len(data):#x}")
    out = bytearray(data[:BANK])
    for k in range(1, 16):
        start = BANK + (k - 1) * (BANK + 8) + 8
        out += data[start:start + BANK]
    return bytes(out)


def printable(data: bytes, minlen=6):
    out, cur, start = [], bytearray(), 0
    for i, ch in enumerate(data):
        if 32 <= ch < 127:
            if not cur:
                start = i
            cur.append(ch)
        else:
            if len(cur) >= minlen:
                out.append((start, cur.decode("ascii")))
            cur = bytearray()
    if len(cur) >= minlen:
        out.append((start, cur.decode("ascii")))
    return out


def looks_like_code(b: bytes) -> str:
    """Very rough 8051 opcode hints."""
    hits = []
    if b"\x90" in b:
        hits.append("MOV DPTR")
    if b"\xe0" in b or b"\xf0" in b:
        hits.append("MOVX")
    if b"\x12" in b or b"\x02" in b:
        hits.append("LCALL/LJMP")
    if b"\x75" in b:
        hits.append("MOV direct")
    return ",".join(hits)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--gsp-container", action="store_true")
    ap.add_argument("--chunk", type=int, default=8)
    ap.add_argument("--min", type=int, default=16)
    ap.add_argument("--bank", type=int, default=-1, help="only this bank")
    args = ap.parse_args()

    a = open(args.a, "rb").read()
    b = open(args.b, "rb").read()
    if args.gsp_container:
        a, b = flatten_gsp(a), flatten_gsp(b)

    C = args.chunk
    total_new = total_del = total_rep = 0
    print(f"{args.a}  ->  {args.b}   chunk={C} min={args.min}\n")

    for bank in range(16):
        if args.bank >= 0 and bank != args.bank:
            continue
        A = a[bank * BANK:(bank + 1) * BANK]
        B = b[bank * BANK:(bank + 1) * BANK]
        ca = [A[i:i + C] for i in range(0, len(A), C)]
        cb = [B[i:i + C] for i in range(0, len(B), C)]
        sm = difflib.SequenceMatcher(None, ca, cb, autojunk=False)
        ins = dele = rep = 0
        rows = []
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "insert":
                ins += (j2 - j1) * C
                rows.append(("INS", i1 * C, j1 * C, (j2 - j1) * C, B[j1 * C:j2 * C]))
            elif tag == "delete":
                dele += (i2 - i1) * C
                rows.append(("DEL", i1 * C, j1 * C, (i2 - i1) * C, A[i1 * C:i2 * C]))
            elif tag == "replace":
                rep += (i2 - i1) * C
                rows.append(("REP", i1 * C, j1 * C, (i2 - i1) * C, B[j1 * C:j2 * C]))
        total_new += ins
        total_del += dele
        total_rep += rep
        if not rows:
            continue
        print(f"=== bank {bank:02d}   new={ins}  deleted={dele}  replaced={rep}")
        for tag, ao, bo, n, data in rows:
            if n < args.min:
                continue
            flat = bank * BANK + bo
            hint = looks_like_code(data) if tag in ("INS", "REP") else ""
            print(f"  {tag}  A+0x{ao:04X} -> B+0x{bo:04X}  len {n}"
                  f"  flat 0x{flat:05X}  {hint}")
            print(f"      {data[:32].hex(' ')}")
            for off, text in printable(data)[:4]:
                print(f"      str: {text!r}")

    print(f"\nTOTAL new={total_new}  deleted={total_del}  replaced={total_rep}")


if __name__ == "__main__":
    sys.exit(main())
