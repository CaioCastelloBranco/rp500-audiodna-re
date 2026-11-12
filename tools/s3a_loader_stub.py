#!/usr/bin/env python3
"""S3a - prove the host half of the IR path in the simulator.  NO HARDWARE.

The port needs to do what the GSP does: push a length-bounded block of bytes
to the DSP and then the 0xF5 terminator.  This script builds that on top of
the *stock* RP500 firmware and proves, under uCsim, that the bytes leave in
the right order and the right number.

Design: reuse the stock stream routine's handshake rather than writing a new
one, so the only new code is a 26-byte gate.

  * Patch the stream's source base (`ADD A,#lo` / `MOV A,#hi`) from the
    24-byte descriptor at 0x2E3B to a 512-byte table in bank 15's free run.
    Two 2-byte edits, same length.
  * Redirect the byte-send entry (0xBE97) into the gate with a 3-byte LJMP.
  * The gate lets the stock loop run until the 16-bit counter reaches 512,
    then writes 0xF5 and exits through the stock epilogue (0xBEB0).

So the stock handshake, the stock setup helper and the stock exit are all
unchanged; only the source and the termination are ours.

Expected at 0xD070: 512 table bytes in order, then 0xF5, then nothing.

Usage:
    python s3a_loader_stub.py [--runs 3000] [--verbose]
"""
import argparse
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rp500_ucsim_run import to_ihex  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FW = os.path.join(ROOT, "01_source_firmware", "rp500_v20.bin")
SDCC_BIN = r"C:\Program Files\SDCC\bin"
S51 = os.path.join(SDCC_BIN, "s51.exe")

BANK = 0x10000
NBANKS = 16
PREFIX = 0x2C80

# --- the build ------------------------------------------------------------
HOOK_BANK = 15
HOOK_AT = 0xBE97          # MOV DPTR,#0FF24h  (the byte-send entry)
STUB_AT = 0xE095          # bank 15 free run
TABLE_AT = 0xE100         # right after the stub
N_BYTES = 512

# The gate.  Layout (26 bytes):
#   E095  MOV DPTR,#FF24h      ; counter high
#   E098  MOVX A,@DPTR
#   E099  CJNE A,#02h,+4       ; high != 2 -> stock path
#   E09C  INC DPTR
#   E09D  MOVX A,@DPTR         ; counter low
#   E09E  JZ +6                ; high==2 and low==0 -> counter == 0x0200
#   E0A0  MOV DPTR,#FF24h      ; stock path: restore DPTR, rejoin the routine
#   E0A3  LJMP 0BE9Ah
#   E0A6  MOV DPTR,#0D070h     ; terminate
#   E0A9  MOV A,#0F5h
#   E0AB  MOVX @DPTR,A
#   E0AC  LJMP 0BEB0h          ; the stock epilogue (INC 38h x2 ; RET)
STUB = bytes.fromhex(
    "90ff24" "e0" "b40204" "a3" "e0" "6006"
    "90ff24" "02be9a" "90d070" "74f5" "f0" "02beb0")

DESCRIPTOR_AT = 0x2E3B     # the source the stock routine reads from


def build_patched(img):
    """Return (patched image, table bytes)."""
    assert len(img) == 0x100000
    out = bytearray(img)
    base = HOOK_BANK * BANK

    # the free run must really be empty where we are about to write
    free = out[base + STUB_AT:base + TABLE_AT + N_BYTES]
    assert all(b == 0xFF for b in free), "free run is not empty at 0x%04X" % STUB_AT

    # 1. source base -> our table
    at_lo = base + 0xBE9E
    at_hi = base + 0xBEA2
    assert out[at_lo:at_lo + 2] == bytes([0x24, 0x3B]), out[at_lo:at_lo + 2].hex(" ")
    assert out[at_hi:at_hi + 2] == bytes([0x74, 0x2E]), out[at_hi:at_hi + 2].hex(" ")
    lo, hi = TABLE_AT & 0xFF, (TABLE_AT >> 8) & 0xFF
    out[at_lo + 1] = lo
    out[at_hi + 1] = hi

    # 2. byte-send entry -> the gate
    at_hook = base + HOOK_AT
    assert out[at_hook:at_hook + 3] == bytes([0x90, 0xFF, 0x24])
    out[at_hook:at_hook + 3] = bytes([0x02, STUB_AT >> 8, STUB_AT & 0xFF])

    # 3. the gate and the table
    out[base + STUB_AT:base + STUB_AT + len(STUB)] = STUB
    # a pattern that never contains 0xF5, so the terminator is unambiguous
    vals = [b for b in range(256) if b != 0xF5]
    table = bytes(vals[i % len(vals)] for i in range(N_BYTES))
    out[base + TABLE_AT:base + TABLE_AT + N_BYTES] = table
    return bytes(out), table


def mov_sites(body, lo, hi):
    return [(i, body[i + 2]) for i in range(lo, hi - 2)
            if body[i] == 0x75 and body[i + 1] == 0x90]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=3000)
    ap.add_argument("--image", default=FW)
    ap.add_argument("--out", default=os.path.join(
        os.environ.get("TEMP", "."), "opencode", "rp500_s3a"))
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(S51):
        print("FAIL: uCsim not found at", S51)
        return 1
    os.makedirs(args.out, exist_ok=True)

    img = open(args.image, "rb").read()
    patched, table = build_patched(img)
    patched_path = os.path.join(args.out, "rp500_s3a.bin")
    open(patched_path, "wb").write(patched)
    diff = [i for i in range(len(img)) if img[i] != patched[i]]
    print("patched image: %s" % patched_path)
    print("  %d bytes changed, at %s" % (len(diff), " ".join(hex(d) for d in diff[:6])))
    print("  stub 0x%04X (%d bytes), table 0x%04X (%d bytes)"
          % (STUB_AT, len(STUB), TABLE_AT, N_BYTES))

    bodies = [patched[k * BANK:(k + 1) * BANK] for k in range(NBANKS)]
    hexfiles = []
    for k in range(NBANKS):
        p = os.path.join(args.out, "bank%02d.hex" % k)
        open(p, "w").write(to_ihex(bodies[k]))
        hexfiles.append(p)

    # bank switch breakpoints
    sites = {}
    for k in range(NBANKS):
        for addr, imm in mov_sites(bodies[k], 0, PREFIX):
            sites[addr] = imm & 0x0F
        for addr, imm in mov_sites(bodies[k], PREFIX, BANK):
            sites[addr] = imm & 0x0F

    lines = []
    n = 0
    for addr in sorted(sites):
        n += 1
        lines.append("break 0x%04X" % (addr + 3))
        lines.append('commands %d file "%s"' % (n, os.path.basename(hexfiles[sites[addr]])))

    # the DSP model (same as rp500_ucsim_stream.py)
    DSP_STATUS, DSP_DATA, DSP_CMD, READY = 0xD06E, 0xD070, 0xE000, 0xD0FF
    status = ("expression xram[0x%04x]=(xram[0x%04x]^4)|8"
              % (DSP_STATUS, DSP_STATUS))
    for port in (DSP_CMD, DSP_DATA):
        n += 1
        lines.append("break xram w 0x%04x" % port)
        lines.append("commands %d %s" % (n, status))
    lines.insert(0, "fill xram 0x%04x 0x%04x 0x01" % (READY, READY))
    # the ready-flag reads (bank 15 0xBE57, bank 14 0x9A65) point at 0xD070;
    # the bench patches them to the scratch cell
    for k, off in ((15, 0xBE57), (14, 0x9A65)):
        at = k * BANK + off
        assert patched[at:at + 3] == bytes([0x90, 0xD0, 0x70]), hex(at)
        bodies[k] = bodies[k][:off] + bytes([0x90, READY >> 8, READY & 0xFF]) + \
            bodies[k][off + 3:]
        open(hexfiles[k], "w").write(to_ihex(bodies[k]))

    # capture: the stock byte store, and the stub's terminator store
    n += 1
    lines.append("break 0x%04X" % 0xBEAD)
    lines.append("commands %d dx 0x%04x 0x%04x" % (n, DSP_DATA, DSP_DATA))
    n += 1
    lines.append("break 0x%04X" % 0xE0AC)          # the instruction after the stub's 0xF5 write
    lines.append("commands %d dx 0x%04x 0x%04x" % (n, DSP_DATA, DSP_DATA))
    # exit: the stock epilogue the stub jumps to
    n += 1
    lines.append("break 0x%04X" % 0xBEB0)
    lines.append("commands %d dx 0x%04x 0x%04x" % (n, 0xFF24, 0xFF25))

    lines += ["run"] * args.runs
    script = os.path.join(args.out, "s3a.cmd")
    open(script, "w").write("\n".join(lines) + "\n")

    log_path = os.path.join(args.out, "s3a_out.txt")
    env = dict(os.environ)
    env["PATH"] = SDCC_BIN + os.pathsep + env.get("PATH", "")
    with open(script) as fin, open(log_path, "w") as fout:
        subprocess.run([S51, "-t", "52", "-X", "12M", "bank00.hex"],
                       cwd=args.out, env=env, stdin=fin, stdout=fout,
                       stderr=subprocess.STDOUT, timeout=3600)

    log = open(log_path, "rb").read().decode("utf-8", "replace")
    stream, exits = [], []
    cur = None
    CAPTURE_PCS = (0xBEAD, 0xE0AC)
    for ln in log.splitlines():
        s = ln.strip()
        m = re.match(r"^Stop at 0x([0-9a-f]+):", s)
        if m:
            cur = int(m.group(1), 16)
            continue
        # `dx 0xff24 0xff25` prints: "0xff24 HH LL .."
        m = re.match(r"^0xff24\s+([0-9a-f]{2})\s+([0-9a-f]{2})", s)
        if m:
            exits.append((int(m.group(1), 16), int(m.group(2), 16)))
            continue
        m = re.search(r"DPTR=\s*0x([0-9a-f]+)\s*@DPTR=\s*0x([0-9a-f]{2})", s)
        if m and cur in CAPTURE_PCS and int(m.group(1), 16) == DSP_DATA:
            stream.append(int(m.group(2), 16))

    n_passes = len(stream) // (N_BYTES + 1)
    print("\nbytes captured at 0xD070: %d  (%d complete pass%s of %d + 0xF5)"
          % (len(stream), n_passes, "" if n_passes == 1 else "es", N_BYTES))
    print("  first 16:", " ".join("%02X" % b for b in stream[:16]))
    print("  expected:", " ".join("%02X" % b for b in table[:16]))
    ok_payload = stream[:N_BYTES] == list(table)
    has_term = len(stream) > N_BYTES and stream[N_BYTES] == 0xF5
    ok_counter = bool(exits) and exits[0] == (0x02, 0x00)
    print("  first %d bytes are the table, in order : %s" % (N_BYTES, ok_payload))
    print("  byte %d is 0xF5 (the terminator)       : %s" % (N_BYTES + 1, has_term))
    print("  0xF5 appears only as a terminator      : %s"
          % (stream.count(0xF5) == n_passes and n_passes > 0))
    print("  counter at exit was 0x0200 (= %d)      : %s"
          % (N_BYTES, ok_counter))
    print("  exit through the stock epilogue 0xBEB0 : %s" % (len(exits) > 0))
    if args.verbose:
        print("\n--- log tail ---")
        print("\n".join(log.splitlines()[-20:]))
    ok = ok_payload and has_term and ok_counter and stream.count(0xF5) == n_passes
    print("\nS3a: %s" % ("PASS - the host half is byte-correct" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
