#!/usr/bin/env python3
"""Bank map for the RP500 firmware image.

Answers the Phase 0 question "how does the 8051 select a bank?" and produces
the code/data map that Phase 1 needs.

Findings (all re-derived by this script):

  * The 1 MB image is 16 x 64 KB banks.
  * Every bank starts with the SAME 0x2C80-byte prefix: the reset/entry
    trampoline and the bank-select machinery, replicated by the build.
  * The bank-select table sits at 0x0200..0x027B: 16 entries of 8 bytes,

        MOV P1,#(0xF0+bank)   ; 3 bytes   75 90 xx
        RET                   ; 1 byte    22
        FF FF FF FF           ; 4 bytes   padding

    so **P1 low nibble = bank number** (0xF0 = bank 0 ... 0xFF = bank 15).
    Each entry is callable: LCALL 0x0200+8*bank selects the bank and returns.
  * 0x00BF reads P1 back, masks the nibble and publishes it to an external
    register at 0xFDA2 (MOVX), i.e. the active bank is also reported outward.
  * 0x0204..0x027B hold 0xFF padding, which is why the at51 code/data map
    marks that region as "no jumps".

Optional: `at51 stat` (https://github.com/8051Enthusiast/at51) gives a
per-512-byte-block code/data classification, used here when the binary is
present.

Usage:
    python bank_map.py [image.bin ...]
"""
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "04_analysis_scripts"))

BANK = 0x10000
NBANKS = 16
AT51 = os.path.join(ROOT, "07_open_source_tools", "at51", "at51.exe")

# Bank-select table (identical in every bank of every build examined).
TABLE_START = 0x0200
TABLE_ENTRIES = 16
TABLE_STRIDE = 8


def common_prefix(seqs):
    n = min(len(s) for s in seqs)
    i = 0
    while i < n and len(set(s[i] for s in seqs)) == 1:
        i += 1
    return i


def common_suffix(seqs):
    return common_prefix([s[::-1] for s in seqs])


def decode_bank_select(bank: bytes):
    """Decode the 16-entry bank-select table; returns list of (addr, value)."""
    out = []
    for b in range(TABLE_ENTRIES):
        off = TABLE_START + b * TABLE_STRIDE
        entry = bank[off:off + TABLE_STRIDE]
        if len(entry) != TABLE_STRIDE:
            raise SystemExit(f"bank-select table truncated at bank {b}")
        if entry[0:3] != bytes([0x75, 0x90, 0xF0 + b]):
            raise SystemExit(f"unexpected bank-select entry {b}: {entry[:3].hex(' ')}")
        if entry[3] != 0x22:
            raise SystemExit(f"bank-select entry {b} does not end in RET")
        out.append((off, 0xF0 + b))
    return out


def free_runs(bank: bytes, min_run=256):
    """Contiguous runs of 0xFF of at least min_run bytes."""
    runs = []
    start = None
    for i, b in enumerate(bank):
        if b == 0xFF:
            if start is None:
                start = i
        else:
            if start is not None and i - start >= min_run:
                runs.append((start, i))
            start = None
    if start is not None and len(bank) - start >= min_run:
        runs.append((start, len(bank)))
    return runs


def code_data_map(bank_bytes, tmpdir, tag):
    """Run `at51 stat` on one bank; returns list of 'C'/'M'/'D' per 512 bytes."""
    if not os.path.exists(AT51):
        return None
    f = os.path.join(tmpdir, f"{tag}.bin")
    open(f, "wb").write(bank_bytes)
    out = subprocess.run([AT51, "stat", "-j", f], capture_output=True, text=True)
    txt = out.stdout.strip()
    if not txt:
        return None
    import json
    try:
        rows = json.loads(txt)
    except Exception:
        return None
    res = []
    for r in rows:
        v = r[0] if isinstance(r, (list, tuple)) else r
        if v is None:
            res.append("D")     # no jumps at all -> data / straight line
        elif v == 0:
            res.append("C")     # all jumps aligned -> pure 8051 code
        else:
            res.append("M")     # mixed: code with embedded tables/data
    return res


def report(path):
    img = open(path, "rb").read()
    name = os.path.basename(path)
    print("=" * 78)
    print(f"{name}   {len(img):#x} bytes")
    print("=" * 78)
    if len(img) != NBANKS * BANK:
        print(f"  not a {NBANKS * BANK:#x}-byte image, skipping")
        return

    banks = [img[k * BANK:(k + 1) * BANK] for k in range(NBANKS)]
    cp = common_prefix(banks)
    cs = common_suffix(banks)
    print(f"  identical prefix across all 16 banks : 0x{cp:04X} ({cp} bytes)")
    print(f"  identical suffix across all 16 banks : 0x{cs:04X} ({cs} bytes)")

    sel = decode_bank_select(banks[0])
    print(f"  bank-select table @0x{TABLE_START:04X} : "
          f"{len(sel)} entries x {TABLE_STRIDE} bytes "
          f"('MOV P1,#(F0+n)' + RET + 4x FF)")
    print(f"    entry 0  @0x{sel[0][0]:04X} -> P1 = 0x{sel[0][1]:02X}")
    print(f"    entry 15 @0x{sel[-1][0]:04X} -> P1 = 0x{sel[-1][1]:02X}")

    # every bank must carry the same table
    same = all(decode_bank_select(b) == sel for b in banks)
    print(f"  bank-select table identical in every bank: {same}")

    with tempfile.TemporaryDirectory() as td:
        print()
        print("  bank  code  mixed  data   largest 0xFF run")
        for k in range(NBANKS):
            cm = code_data_map(banks[k], td, f"b{k}")
            runs = free_runs(banks[k])
            biggest = max((e - s for s, e in runs), default=0)
            if cm:
                c = cm.count("C")
                m = cm.count("M")
                d = cm.count("D")
                print(f"   {k:2d}  {c:4d}  {m:5d}  {d:4d}   {biggest:#8x} "
                      f"@ {max(runs, key=lambda r: r[1]-r[0])[0]:#06x}"
                      if runs else
                      f"   {k:2d}  {c:4d}  {m:5d}  {d:4d}   none")
            else:
                print(f"   {k:2d}    -     -     -   {biggest:#8x} "
                      f"(at51 not available)")
    print()


def main(argv):
    paths = argv[1:] or [
        os.path.join(ROOT, "01_source_firmware", "rp500_v20.bin"),
        os.path.join(ROOT, "01_source_firmware", "rp500_v14.bin"),
        os.path.join(ROOT, "01_source_firmware", "rp500_v12.bin"),
    ]
    for p in paths:
        if os.path.exists(p):
            report(p)
        else:
            print(f"(missing: {p})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
