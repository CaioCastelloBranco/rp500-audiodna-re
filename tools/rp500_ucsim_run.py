#!/usr/bin/env python3
"""Run the real RP500 firmware in the uCsim 8051 simulator.

We have a CPU-accurate 8051 core (uCsim `s51`, shipped with SDCC) but none
of the RP500's peripherals: no P1 bank switching, no external AudioDNA2T
DSP over the host ports, no flash banking, no USB.

That is still useful: the reset path of the stock firmware is plain 8051
code, so we can execute it and find out exactly where it stops without
hardware. That location is the first hardware dependency, and the walk from
there to the bank switch is the bank map in executable form.

Usage:
    python rp500_ucsim_run.py [--bank 0] [--steps 200000] [--image FILE]
"""
import argparse
import os
import struct
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SDCC_BIN = r"C:\Program Files\SDCC\bin"
S51 = os.path.join(SDCC_BIN, "s51.exe")

BANK = 0x10000


def to_ihex(data: bytes, base: int = 0) -> str:
    """Minimal Intel HEX writer (16 bytes per record)."""
    lines = []
    for i in range(0, len(data), 16):
        chunk = data[i:i + 16]
        addr = (base + i) & 0xFFFF
        rec = [len(chunk), (addr >> 8) & 0xFF, addr & 0xFF, 0x00] + list(chunk)
        csum = (-sum(rec)) & 0xFF
        lines.append(":" + "".join("%02X" % b for b in rec) + "%02X" % csum)
    lines.append(":00000001FF")
    return "\n".join(lines) + "\n"


def run(ihx: str, steps: int, timeout: int = 45, extra: str = "") -> str:
    seq = 'step %d; quit' % steps if not extra else 'step %d; %s; quit' % (steps, extra)
    cmd = [S51, '-t', '52', '-X', '12M', '-e', seq, os.path.basename(ihx)]
    env = dict(os.environ)
    env['PATH'] = SDCC_BIN + os.pathsep + env.get('PATH', '')
    # uCsim executes the -e commands and then drops into its console; with
    # stdin closed it keeps the console open, so the run is stopped once the
    # output has been collected.
    p = subprocess.Popen(cmd, cwd=os.path.dirname(ihx) or '.', env=env,
                         stdin=subprocess.DEVNULL,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True)
    try:
        out, _ = p.communicate(timeout=timeout)
        return out
    except subprocess.TimeoutExpired:
        p.kill()
        out, _ = p.communicate()
        return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", default=os.path.join(ROOT, "01_source_firmware",
                                                    "rp500_v20.bin"))
    ap.add_argument("--bank", type=int, default=0)
    ap.add_argument("--skip", type=int, default=0,
                    help="bytes to skip before the bank body "
                         "(GSP images carry an 8-byte descriptor per bank)")
    ap.add_argument("--steps", type=int, default=200000)
    ap.add_argument("--extra", default="", help="extra uCsim commands, e.g. ds")
    args = ap.parse_args()

    if not os.path.exists(S51):
        print("FAIL: uCsim not found at %s (winget install SDCC.SDCC)" % S51)
        return 1

    img = open(args.image, "rb").read()
    start = args.bank * BANK + args.skip
    body = img[start:start + BANK]
    if len(body) != BANK:
        print("FAIL: bank %d out of range" % args.bank)
        return 1
    print("image    : %s bank %d (64 KB, skip %d)"
          % (os.path.basename(args.image), args.bank, args.skip))

    with tempfile.TemporaryDirectory() as td:
        ihx = os.path.join(td, "rp500_bank.bin.hex")
        open(ihx, "w").write(to_ihex(body))
        print("steps    : %d" % args.steps)
        out = run(ihx, args.steps, extra=args.extra)

    print()
    print(out[-1800:] if out else "(no simulator output)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
