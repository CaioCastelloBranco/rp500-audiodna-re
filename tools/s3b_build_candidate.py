#!/usr/bin/env python3
"""Build the S3b hardware candidate.

Base: the last known-good image (cab 24 = CAIO4X12).
Adds: the production gate (scan 0xF6AA for 00 02 49 = 585), the source block,
      and the 128-tap unit-impulse IR table (512 bytes) at 0xE200.

No test gate: the hardware builds the production scan only.  The stock path
(Direct, and every cab other than 585) is unchanged.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "04_analysis_scripts"))
from s3b_cab_trigger import build, N_BYTES, TABLE_AT
from digbin_pack import pack, unpack

BASE = ROOT / "09_builds" / "rp500_v20_caio4x12.bin"
TABLE = ROOT / "IR" / "impulse128.bin"
OUT_BIN = ROOT / "09_builds" / "rp500_v20_s3b_impulse.bin"
OUT_DIG = ROOT / "09_builds" / "rp500_v20_s3b_impulse.DigBin"

base = BASE.read_bytes()
table = TABLE.read_bytes()
assert len(base) == 0x100000, len(base)
assert len(table) == N_BYTES, len(table)
assert b"CAIO4X12" in base, "base is not the CAIO4X12 image"

patched, table2, f5_pc, glen, slen = build(base, "s3b_gate", table=table)
assert len(patched) == 0x100000
assert patched == bytes(patched)
assert patched[15 * 0x10000 + TABLE_AT:15 * 0x10000 + TABLE_AT + N_BYTES] == table
assert patched[15 * 0x10000 + 0xBE97:15 * 0x10000 + 0xBE9A] == bytes([0x02, 0xE0, 0x95])
assert patched[15 * 0x10000 + 0xBE9E:15 * 0x10000 + 0xBEA1] == bytes([0x02, 0xE8, 0x00])
assert b"CAIO4X12" in patched, "cab name lost"

diff = [i for i in range(len(base)) if base[i] != patched[i]]
banks = sorted({i // 0x10000 for i in diff})
print("gate %d B, source %d B, table %d B, f5 pc 0x%04X" % (glen, slen, N_BYTES, f5_pc))
print("delta from CAIO4X12 base: %d bytes, banks %s" % (len(diff), banks))
if banks != [15]:
    print("WARNING: delta outside bank 15:", banks)

OUT_BIN.write_bytes(patched)
dig = pack(patched)
assert len(dig) == 0x100084
assert unpack(dig) == patched
OUT_DIG.write_bytes(dig)
print("wrote", OUT_BIN.relative_to(ROOT), len(patched))
print("wrote", OUT_DIG.relative_to(ROOT), len(dig))
print("first impulse tap:", table[:4].hex(" "))
