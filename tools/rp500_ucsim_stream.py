#!/usr/bin/env python3
"""Observe the RP500's real DSP byte stream in uCsim.

The static analysis says the RP500 writes the DSP data port 0xD070 from three
places:

  1. a **per-cabinet parameter table** (113 bytes, bank 14 @0x2C80 / bank 15
     @0x2CBB) copied byte-wise into DSP registers 0xD000..0xD070 - its last
     byte lands on 0xD070;
  2. a **24-byte parameter descriptor** streamed sequentially from code space
     (bank 14 0x9ABA, bank 15 0xBEAC), read with MOVC from 0x2DC2 / 0x2E3B.

This bench reproduces the DSP handshake so the firmware leaves its poll loop,
and captures the bytes that reach 0xD070.

The firmware's handshake (bank 15):

    BE13  MOV  DPTR,#0D06Eh
    BE16  MOVX A,@DPTR        ; read the DSP status
    BE17  MOV  2Fh,A
    BE20  MOV  DPTR,#0E000h   ; send the command
    BE23  MOVX @DPTR,A
    BE24  MOV  30h,2Fh
    BE44  MOV  DPTR,#0D06Eh
    BE47  MOVX A,@DPTR        ; read the status again
    BE48  MOV  2Fh,A
    BE29  MOV  A,30h
    BE2B  XRL  A,2Fh
    BE2D  JB   E2h,BE4C       ; wait until the status *changes* (bit 2)
    BE57  MOV  DPTR,#0D070h
    BE5A  MOVX A,@DPTR        ; the DSP's "byte accepted" flag is bit 0
    BE63  ...                 ; bump the 16-bit counter at XRAM 0xFF24/0xFF25
    BE97  ...                 ; MOVC from code space -> 0xD070

Two modelling problems, and how they are solved here:

  * **Status.** The firmware waits for bit 2 of the status to *change* between
    two reads. A real DSP flips it when it is handed a command or when it
    consumes a byte. So the model toggles bit 2 (and forces bit 3 on) whenever
    the host writes 0xE000 (a command) or 0xD070 (a byte).

  * **The data port is read and written.** In the real DSP, reading 0xD070
    returns a status byte while writing it sends data - two different
    registers. A flat XRAM cell cannot be both, so the simulator's *copy* of
    the image has its two "read the ready flag" sites pointed at a scratch cell
    (0xD0FF) that the model holds at 1. That patch touches **only the
    simulator's copy** and only the DPTR immediate of the two read sites
    (3 bytes each, same length); the stream logic under test is untouched.

uCsim keeps exactly one command per breakpoint, so each breakpoint below
carries exactly one command.

Usage:
    python rp500_ucsim_stream.py [--runs 3000] [--verbose]
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

DSP_STATUS = 0xD06E
DSP_DATA = 0xD070
DSP_CMD = 0xE000
READY_CELL = 0xD0FF          # scratch cell the model keeps at 1

# Per-bank addresses inside the stream routine (identical layout in both banks).
# READ_FLAG  = the "MOV DPTR,#0D070h" that precedes the ready-flag read
# AFTER_STORE = the instruction right after the descriptor byte is stored
# EXIT      = the loop exit, after the cap compare
READ_FLAG = {14: 0x9A65, 15: 0xBE57}
AFTER_STORE = {14: 0x9ABB, 15: 0xBEAD}
EXIT = {14: 0x9ABE, 15: 0xBEB0}


def mov_sites(body, lo, hi):
    return [(i, body[i + 2]) for i in range(lo, hi - 2)
            if body[i] == 0x75 and body[i + 1] == 0x90]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", default=FW)
    ap.add_argument("--runs", type=int, default=3000)
    ap.add_argument("--workdir", default=os.path.join(
        os.environ.get("TEMP", "."), "opencode", "rp500_banks"))
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(S51):
        print("FAIL: uCsim not found at", S51)
        return 1
    os.makedirs(args.workdir, exist_ok=True)

    img = bytearray(open(args.image, "rb").read())
    for bankno, off in READ_FLAG.items():
        at = bankno * BANK + off
        assert img[at:at + 3] == b"\x90\xd0\x70", "unexpected bytes at %06X" % at
        img[at:at + 3] = bytes([0x90, READY_CELL >> 8, READY_CELL & 0xFF])
    bodies = [bytes(img[k * BANK:(k + 1) * BANK]) for k in range(NBANKS)]
    hexfiles = []
    for k in range(NBANKS):
        p = os.path.join(args.workdir, "bank%02d.hex" % k)
        open(p, "w").write(to_ihex(bodies[k]))
        hexfiles.append(p)
    print("simulator-only patch: the ready-flag read now comes from 0x%04X"
          % READY_CELL)

    # --- bank switch breakpoints -------------------------------------------
    sites = {}
    for k in range(NBANKS):
        for addr, imm in mov_sites(bodies[k], 0, PREFIX):
            sites[addr] = imm & 0x0F
        for addr, imm in mov_sites(bodies[k], PREFIX, BANK):
            sites[addr] = imm & 0x0F

    lines = []
    n = 0
    for addr in sorted(sites):
        target = sites[addr]
        n += 1
        lines.append("break 0x%04X" % (addr + 3))
        lines.append('commands %d file "%s"' % (n, os.path.basename(hexfiles[target])))

    # --- the DSP model, one command per breakpoint -------------------------
    status_expr = ("expression xram[0x%04x]=(xram[0x%04x]^4)|8"
                   % (DSP_STATUS, DSP_STATUS))
    for port in (DSP_CMD, DSP_DATA):
        n += 1
        lines.append("break xram w 0x%04x" % port)
        lines.append("commands %d %s" % (n, status_expr))

    # the ready flag always reads as "byte accepted"
    lines.insert(0, "fill xram 0x%04x 0x%04x 0x01" % (READY_CELL, READY_CELL))

    # --- capture -----------------------------------------------------------
    # The store sites are shadowed by the 0xD070 write event (same address),
    # but uCsim's stop banner already prints the byte that was just written
    # ("DPTR= 0xd070 @DPTR= 0xNN"), so the stream is read back from the log.
    for bankno, addr in EXIT.items():
        n += 1
        lines.append("break 0x%04X" % addr)
        lines.append("commands %d dx 0xff24 0xff25" % n)

    lines += ["run"] * args.runs

    script_path = os.path.join(args.workdir, "stream.cmd")
    open(script_path, "w").write("\n".join(lines) + "\n")
    print("breakpoints: %d, script: %d lines -> %s" % (n, len(lines), script_path))

    log_path = os.path.join(args.workdir, "stream_out.txt")
    env = dict(os.environ)
    env["PATH"] = SDCC_BIN + os.pathsep + env.get("PATH", "")
    with open(script_path) as fin, open(log_path, "w") as fout:
        subprocess.run([S51, "-t", "52", "-X", "12M", "bank00.hex"],
                       cwd=args.workdir, env=env, stdin=fin, stdout=fout,
                       stderr=subprocess.STDOUT, timeout=3600)

    log = open(log_path, "rb").read().decode("utf-8", "replace")

    # --- parse -------------------------------------------------------------
    # Every stop is a block: "Stop at 0xPC: (...)" followed by the register
    # dump, which contains "DPTR= 0xd070 @DPTR= 0xNN" when the byte that was
    # just written to the DSP data port is still in the data register.
    stream = []
    counters = []
    cur = None
    for ln in log.splitlines():
        m = re.match(r"^Stop at 0x([0-9a-f]+):", ln.strip())
        if m:
            cur = int(m.group(1), 16)
            continue
        m = re.match(r"^0x([0-9a-f]+)\s+([0-9a-f]{2})\s", ln.strip())
        if m:
            addr, val = m.group(1), int(m.group(2), 16)
            if addr in ("ff24", "ff25"):
                counters.append((addr, val))
            continue
        m = re.search(r"DPTR=\s*0x([0-9a-f]+)\s*@DPTR=\s*0x([0-9a-f]{2})", ln)
        if m and cur in AFTER_STORE.values():
            if int(m.group(1), 16) == DSP_DATA:
                stream.append(int(m.group(2), 16))

    print("\nbytes captured at the DSP data port 0xD070: %d" % len(stream))
    if stream:
        print("  first 32:", " ".join("%02X" % b for b in stream[:32]))
        print("  last  16:", " ".join("%02X" % b for b in stream[-16:]))
    if counters:
        print("byte counter reads (XRAM 0xFF24 / 0xFF25):",
              [(a, "%02X" % v) for a, v in counters[:8]])

    blob = bodies[15][0x2E3B:0x2E3B + 24]
    n_cmp = min(len(stream), 24)
    same = stream[:n_cmp] == list(blob[:n_cmp]) if n_cmp else False
    print("\nstream == the 24-byte descriptor at bank 15 0x2E3B: %s" % same)
    print("  expected:", " ".join("%02X" % b for b in blob))
    print("  observed:", " ".join("%02X" % b for b in stream[:24]))
    if args.verbose:
        print("\n--- log tail ---")
        print("\n".join(log.splitlines()[-30:]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
