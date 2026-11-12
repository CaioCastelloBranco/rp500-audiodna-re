#!/usr/bin/env python3
"""S3b - cabinet-conditional IR gate, proved in uCsim.  NO HARDWARE.

The gate hooks the stock byte-send entry (bank 15 0xBE97) and, on the first
byte of a stream, scans the edit buffer 0xF6AA for the 3-byte cab value
00 02 49 (585 = CAIO4X12).

  * found     -> source = IR table 0xE200, length 512, terminator 0xF5
  * not found -> source = stock descriptor 0x2E3B, length 24, no terminator

At boot the edit buffer is zero, so the gate cannot fire.  The user's
GSP2101 Clean Tube / Sat Tube forces cab 585, which is the only way to arm it.

Usage:
    python s3b_cab_trigger.py [--runs 3000]
"""
import argparse
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rp500_ucsim_run import to_ihex
from s3a_loader_stub import mov_sites, S51, SDCC_BIN

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FW = os.path.join(ROOT, "01_source_firmware", "rp500_v20.bin")
ASM = os.path.join(ROOT, "04_analysis_scripts")
BANK, NBANKS, PREFIX = 0x10000, 16, 0x2C80

GATE_AT, SOURCE_AT, TABLE_AT = 0xE095, 0xE800, 0xE200
HOOK_ENTRY, HOOK_SOURCE = 0xBE97, 0xBE9E
N_BYTES = 512
DESCRIPTOR_AT = 0x2E3B
CAB_CELL = 0xF6AA
CAB_VALUE = b"\x00\x02\x49"          # 585 = CAIO4X12
SRC_CELL, LEN_CELL, FLAG_CELL = 0xF8E0, 0xF8E2, 0xF8E4


def assemble(name):
    tmp = os.path.join(os.environ.get("TEMP", "."), "opencode", "s3b_asm")
    os.makedirs(tmp, exist_ok=True)
    src = os.path.join(ASM, name + ".asm")
    rel = os.path.join(tmp, name + ".rel")
    ihx = os.path.join(tmp, name + ".ihx")
    for p in (rel, ihx):
        if os.path.exists(p):
            os.remove(p)
    subprocess.run([os.path.join(SDCC_BIN, "sdas8051.exe"), "-o", rel, src],
                   check=True, cwd=tmp, stdout=subprocess.DEVNULL)
    subprocess.run([os.path.join(SDCC_BIN, "sdld.exe"), "-i", ihx, rel],
                   check=True, cwd=tmp, stdout=subprocess.DEVNULL)
    mem = {}
    for line in open(ihx):
        line = line.strip()
        if not line.startswith(":"):
            continue
        b = bytes.fromhex(line[1:])
        n, addr, typ = b[0], (b[1] << 8) | b[2], b[3]
        if typ == 0:
            for i, v in enumerate(b[4:4 + n]):
                mem[addr + i] = v
    if not mem:
        raise RuntimeError("empty object: %s" % ihx)
    lo, hi = min(mem), max(mem)
    return bytes(mem.get(i, 0xFF) for i in range(lo, hi + 1))


def build(img_cab, gate_name="s3b_gate", table=None):
    gate = assemble(gate_name)
    source = assemble("s3b_source")
    assert len(gate) <= TABLE_AT - GATE_AT, "gate too large: %d" % len(gate)
    assert len(source) <= 0x10000 - SOURCE_AT, "source too large"

    out = bytearray(img_cab)
    base = 15 * BANK
    free = out[base + GATE_AT:base + TABLE_AT + N_BYTES]
    assert all(b == 0xFF for b in free), "gate/table region is not free"
    free2 = out[base + SOURCE_AT:base + SOURCE_AT + len(source)]
    assert all(b == 0xFF for b in free2), "source region is not free"

    # entry hook and source-base hook
    assert out[base + HOOK_ENTRY:base + HOOK_ENTRY + 3] == bytes([0x90, 0xFF, 0x24])
    out[base + HOOK_ENTRY:base + HOOK_ENTRY + 3] = bytes(
        [0x02, GATE_AT >> 8, GATE_AT & 0xFF])
    assert out[base + HOOK_SOURCE:base + HOOK_SOURCE + 9] == bytes(
        [0x24, 0x3B, 0xF5, 0x82, 0x74, 0x2E, 0x3E, 0xF5, 0x83])
    out[base + HOOK_SOURCE:base + HOOK_SOURCE + 9] = bytes(
        [0x02, SOURCE_AT >> 8, SOURCE_AT & 0xFF]) + b"\xFF" * 6

    out[base + GATE_AT:base + GATE_AT + len(gate)] = gate
    out[base + SOURCE_AT:base + SOURCE_AT + len(source)] = source

    if table is None:
        vals = [b for b in range(256) if b != 0xF5]
        table = bytes(vals[i % len(vals)] for i in range(N_BYTES))
    if len(table) != N_BYTES:
        raise ValueError("IR table must be %d bytes, got %d" % (N_BYTES, len(table)))
    out[base + TABLE_AT:base + TABLE_AT + N_BYTES] = table

    # find the gate's terminator store: 90 D0 70 74 F5 F0
    seq = bytes([0x90, 0xD0, 0x70, 0x74, 0xF5, 0xF0])
    pos = gate.find(seq)
    assert pos >= 0, "gate terminator store not found"
    f5_pc = GATE_AT + pos + len(seq)
    return bytes(out), table, f5_pc, len(gate), len(source)


def run_case(patched, target, runs, tag, outdir, f5_pc):
    os.makedirs(outdir, exist_ok=True)
    bodies = [patched[k * BANK:(k + 1) * BANK] for k in range(NBANKS)]
    hexfiles = []
    for k in range(NBANKS):
        p = os.path.join(outdir, "bank%02d.hex" % k)
        open(p, "w").write(to_ihex(bodies[k]))
        hexfiles.append(p)

    sites = {}
    for k in range(NBANKS):
        for addr, imm in mov_sites(bodies[k], 0, PREFIX):
            sites[addr] = imm & 0x0F
        for addr, imm in mov_sites(bodies[k], PREFIX, BANK):
            sites[addr] = imm & 0x0F

    lines, n = [], 0
    for addr in sorted(sites):
        n += 1
        lines.append("break 0x%04X" % (addr + 3))
        lines.append("commands %d file \"%s\"" % (n, os.path.basename(hexfiles[sites[addr]])))

    DSP_STATUS, DSP_DATA, DSP_CMD, READY = 0xD06E, 0xD070, 0xE000, 0xD0FF
    status = "expression xram[0x%04x]=(xram[0x%04x]^4)|8" % (DSP_STATUS, DSP_STATUS)
    for port in (DSP_CMD, DSP_DATA):
        n += 1
        lines.append("break xram w 0x%04x" % port)
        lines.append("commands %d %s" % (n, status))
    lines.insert(0, "fill xram 0x%04x 0x%04x 0x01" % (READY, READY))


    # ready-flag reads -> scratch cell (simulator-only)
    for k, off in ((15, 0xBE57), (14, 0x9A65)):
        at = k * BANK + off
        assert patched[at:at + 3] == bytes([0x90, 0xD0, 0x70]), hex(at)
        bodies[k] = bodies[k][:off] + bytes([0x90, READY >> 8, READY & 0xFF]) + \
            bodies[k][off + 3:]
        open(hexfiles[k], "w").write(to_ihex(bodies[k]))

    n += 1
    lines.append("break 0x%04X" % 0xBEAD)
    lines.append("commands %d dx 0x%04x 0x%04x" % (n, DSP_DATA, DSP_DATA))
    n += 1
    lines.append("break 0x%04X" % f5_pc)
    lines.append("commands %d dx 0x%04x 0x%04x" % (n, DSP_DATA, DSP_DATA))
    n += 1
    lines.append("break 0x%04X" % 0xBEB0)
    lines.append("commands %d dx 0x%04x 0x%04x" % (n, 0xFF24, 0xFF25))
    lines += ["run"] * runs

    script = os.path.join(outdir, "s3b.cmd")
    open(script, "w").write("\n".join(lines) + "\n")
    log_path = os.path.join(outdir, "s3b_out.txt")
    env = dict(os.environ)
    env["PATH"] = SDCC_BIN + os.pathsep + env.get("PATH", "")
    with open(script) as fin, open(log_path, "w") as fout:
        subprocess.run([S51, "-t", "52", "-X", "12M", "bank00.hex"],
                       cwd=outdir, env=env, stdin=fin, stdout=fout,
                       stderr=subprocess.STDOUT, timeout=3600)

    log = open(log_path, "rb").read().decode("utf-8", "replace")
    stream, exits, cur = [], [], None
    for ln in log.splitlines():
        s = ln.strip()
        m = re.match(r"^Stop at 0x([0-9a-f]+):", s)
        if m:
            cur = int(m.group(1), 16)
            continue
        m = re.match(r"^0xff24\s+([0-9a-f]{2})\s+([0-9a-f]{2})", s)
        if m:
            exits.append((int(m.group(1), 16), int(m.group(2), 16)))
            continue
        m = re.search(r"DPTR=\s*0x([0-9a-f]+)\s*@DPTR=\s*0x([0-9a-f]{2})", s)
        if m and cur in (0xBEAD, f5_pc) and int(m.group(1), 16) == DSP_DATA:
            stream.append(int(m.group(2), 16))
    return stream, exits, log_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=3000)
    ap.add_argument("--case", choices=("all", "scan", "negative", "stock"),
                    default="all")
    ap.add_argument("--base-image", default=FW,
                    help="flat 1 MB base (default: stock rp500_v20.bin)")
    ap.add_argument("--ir-table", default=os.path.join(ROOT, "IR", "impulse128.bin"),
                    help="512-byte IR table (default: the 128-tap impulse)")
    args = ap.parse_args()
    if not os.path.exists(S51):
        print("FAIL: uCsim not found at", S51)
        return 1

    img = open(args.base_image, "rb").read()
    ir = open(args.ir_table, "rb").read() if os.path.exists(args.ir_table) else None
    prod = build(img, "s3b_gate", table=ir)
    scan = build(img, "s3b_gate_scan_test", table=ir)
    neg = build(img, "s3b_gate_scan_neg", table=ir)
    print("gates: prod %d B, scan %d B, neg %d B, source %d B, table %d B"
          % (prod[3], scan[3], neg[3], prod[4], len(prod[1])))
    print("terminator pcs: prod 0x%04X, scan 0x%04X, neg 0x%04X"
          % (prod[2], scan[2], neg[2]))

    out = os.path.join(os.environ.get("TEMP", "."), "opencode", "rp500_s3b")
    desc = img[15 * BANK + DESCRIPTOR_AT:15 * BANK + DESCRIPTOR_AT + 24]

    ok = True
    for case, gate_build, target, tag, expect_len, expect_term in (
            ("scan", scan, True,
             "scan finds 585 (production scan + impulse)", N_BYTES, True),
            ("negative", neg, False,
             "scan rejects 584 (negative control)", 24, False),
            ("stock", prod, False,
             "no cab value (stock path)", 24, False)):
        if args.case not in ("all", case):
            continue
        print("\n=== %s ===" % tag)
        patched, table, f5_pc, glen, slen = gate_build
        stream, exits, log_path = run_case(
            patched, target, args.runs, tag,
            os.path.join(out, case), f5_pc)
        print("  bytes at 0xD070: %d, exits: %d" % (len(stream), len(exits)))
        if not stream:
            print("  FAIL: no bytes captured")
            print("  log:", log_path)
            ok = False
            continue
        # split passes by the expected length (+ terminator)
        unit = expect_len + (1 if expect_term else 0)
        npass = len(stream) // unit
        first = stream[:expect_len]
        expected = list(table) if target else list(desc)
        payload_ok = first == expected
        term_ok = (not expect_term) or (len(stream) > expect_len and stream[expect_len] == 0xF5)
        counter_ok = bool(exits) and exits[0] == (
            (expect_len >> 8) & 0xFF, expect_len & 0xFF)
        print("  first %d bytes %s: %s"
              % (expect_len, "are the IR table" if target else "are the descriptor",
                 payload_ok))
        print("  terminator %s: %s"
              % ("0xF5" if expect_term else "absent",
                 term_ok))
        print("  counter at exit %s: %s"
              % (hex(expect_len), counter_ok))
        print("  complete passes: %d" % npass)
        if not (payload_ok and term_ok and counter_ok and npass >= 1):
            ok = False

    print("\nS3b host-logic: %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
