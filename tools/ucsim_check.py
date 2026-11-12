#!/usr/bin/env python3
"""Run an 8051 test program under the uCsim simulator and check the result.

This is the Phase 1 test bench. It proves the whole toolchain end to end:

    usercab_wire.c  --sdcc-->  8051 object  --sdld-->  .ihx  --s51-->  verdict

It also cross-checks the 8051 result against an independent Python reference,
which is the "compile twice, test once" idea: the logic is written once in C,
the 8051 build is executed by the simulator, and the same numbers are
recomputed in Python.

Usage:
    python ucsim_check.py                     # run the default test
    python ucsim_check.py --asm wire_8051.asm --expect 0x31
"""
import argparse
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "04_analysis_scripts")

SDCC_BIN = r"C:\Program Files\SDCC\bin"
S51 = os.path.join(SDCC_BIN, "s51.exe")
SDAS = os.path.join(SDCC_BIN, "sdas8051.exe")
SDLD = os.path.join(SDCC_BIN, "sdld.exe")

# The reference message and the checksum the 8051 build must produce.
MESSAGE = bytes([0xF0, 0x00, 0x00, 0x10, 0x00, 0x5E, 0x05, 0x7A])


def python_reference() -> int:
    """Checksum the way the firmware protocol defines it."""
    x = 0
    for b in MESSAGE[1:]:
        x ^= b
    return x & 0x7F


def run_s51(ihx: str, timeout: int = 45) -> str:
    """Execute the image under uCsim and return its output.

    uCsim prints the final register state, then drops into its interactive
    console; the console is closed by killing the process once the output
    has been captured.
    """
    cmd = [S51, '-t', '52', '-X', '12M', '-e',
           'step 5000; quit', os.path.basename(ihx)]
    env = dict(os.environ)
    env['PATH'] = SDCC_BIN + os.pathsep + env.get('PATH', '')
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


def parse_state(out: str):
    """Parse the final 'R0 R1 ... R7' register dump uCsim prints at exit."""
    m = re.search(r"Stop at 0x([0-9a-f]+):.*?\n\s*R0 R1 R2 R3 R4 R5 R6 R7\s*\n\s*"
                   r"([0-9a-f]{2}(?:\s+[0-9a-f]{2}){7})", out, re.S)
    if not m:
        return None, None
    regs = [int(x, 16) for x in m.group(2).split()]
    return int(m.group(1), 16), regs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--asm", default=os.path.join(SCRIPTS, "wire_8051.asm"))
    ap.add_argument("--expect", type=lambda s: int(s, 0), default=None)
    args = ap.parse_args()

    if not os.path.exists(S51):
        print(f"FAIL: uCsim not found at {S51}")
        print("      install with: winget install SDCC.SDCC")
        return 1

    expect = args.expect if args.expect is not None else python_reference()
    print(f"reference message : {MESSAGE.hex(' ')}")
    print(f"python checksum   : 0x{expect:02X}")

    with tempfile.TemporaryDirectory() as td:
        asm = os.path.join(td, "wire_8051.asm")
        with open(args.asm) as f:
            open(asm, "w").write(f.read())
        rel = os.path.join(td, "wire.rel")
        ihx = os.path.join(td, "wire.ihx")

        env = dict(os.environ)
        env['PATH'] = SDCC_BIN + os.pathsep + env.get('PATH', '')
        r = subprocess.run([SDAS, '-o', rel, asm], cwd=td, env=env,
                           capture_output=True, text=True)
        if r.returncode != 0 or not os.path.exists(rel):
            print("FAIL: assembler failed\n" + r.stdout + r.stderr)
            return 1
        r = subprocess.run([SDLD, '-i', ihx, rel], cwd=td, env=env,
                           capture_output=True, text=True)
        if r.returncode != 0 or not os.path.exists(ihx):
            print("FAIL: linker failed\n" + r.stdout + r.stderr)
            return 1
        size = os.path.getsize(ihx)
        print(f"assembled + linked: {size} bytes (Intel HEX)")

        out = run_s51(ihx)
        pc, regs = parse_state(out)
        if regs is None:
            print("FAIL: no final register state in simulator output")
            print(out[-2000:])
            return 1

        r3, r4, r7 = regs[3], regs[4], regs[7]
        print(f"simulator PC      : 0x{pc:04X}")
        print(f"simulator R3      : 0x{r3:02X}  (computed checksum)")
        print(f"simulator R4      : 0x{r4:02X}  (expected value in the image)")
        print(f"simulator R7      : 0x{r7:02X}  (verdict: A5 pass / 5A fail)")

        ok = (r3 == expect) and (r4 == expect) and (r7 == 0xA5)
        print()
        print("PASS: 8051 code under uCsim agrees with the Python reference"
              if ok else
              "FAIL: 8051 result differs from the Python reference")
        return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
