#!/usr/bin/env python3
"""Stage A.2 - model the AudioDNA2T host ports so the firmware stops polling.

Stage A.1 gave us a faithful multi-bank 8051 simulation, and it exposed the
next problem: the firmware writes a command to the DSP control port and then
polls the DSP status register until it *changes* (bank 15, `0xBE13`-`0xBE4A`):

    BE13  MOV  DPTR,#0D06Eh
    BE16  MOVX A,@DPTR        ; read DSP status
    BE17  MOV  2Fh,A
    ...
    BE44  MOV  DPTR,#0D06Eh
    BE47  MOVX A,@DPTR        ; read again
    BE48  MOV  2Fh,A
    BE4A  SJMP BE29          ; loop until the status changes

With no DSP present the status never changes, so the firmware spins in that
loop forever (2,999 of 3,000 breakpoint stops were the bank-15 table entry).

The real DSP acknowledges a host command by *changing* the status register.
So the model is: whenever the firmware writes to a DSP command port, bump the
status register. uCsim can do that from a breakpoint-attached command:

    break  xram w 0xe000
    commands <nr> expression xram[0xd06e]=xram[0xd06e]+1

This script builds the whole command script (bank switches + DSP model) and
runs it, reporting what the firmware does next.
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

# DSP command ports the firmware writes to (from the disassembly of bank 15)
DSP_CMD_PORTS = [0xE000, 0xFDFC]
DSP_STATUS = 0xD06E


def mov_sites(body, lo, hi):
    return [(i, body[i + 2]) for i in range(lo, hi - 2)
            if body[i] == 0x75 and body[i + 1] == 0x90]


def build(args, hexfiles):
    """Return (script lines, breakpoint-number map)."""
    lines = []
    n = 0
    for addr in sorted(args["sites"]):
        target = args["sites"][addr][0]
        n += 1
        lines.append("break 0x%04X" % (addr + 3))
        lines.append('commands %d file "%s"' % (n, os.path.basename(hexfiles[target])))
    for port in DSP_CMD_PORTS:
        n += 1
        lines.append("break xram w 0x%04x" % port)
        if args.get("model"):
            lines.append("commands %d expression xram[0x%04x]=xram[0x%04x]+1"
                         % (n, DSP_STATUS, DSP_STATUS))
    return lines, n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", default=FW)
    ap.add_argument("--runs", type=int, default=2000)
    ap.add_argument("--workdir", default=os.path.join(
        os.environ.get("TEMP", "."), "opencode", "rp500_banks"))
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--no-model", dest="model", action="store_false",
                    help="keep the DSP event breakpoints but do not acknowledge them")
    ap.set_defaults(model=True)
    args = ap.parse_args()

    if not os.path.exists(S51):
        print("FAIL: uCsim not found at", S51)
        return 1
    os.makedirs(args.workdir, exist_ok=True)

    img = open(args.image, "rb").read()
    bodies = [img[k * BANK:(k + 1) * BANK] for k in range(NBANKS)]
    hexfiles = []
    for k in range(NBANKS):
        p = os.path.join(args.workdir, "bank%02d.hex" % k)
        open(p, "w").write(to_ihex(bodies[k]))
        hexfiles.append(p)

    sites = {}
    for k in range(NBANKS):
        for addr, imm in mov_sites(bodies[k], 0, PREFIX):
            sites[addr] = (imm & 0x0F,)
        for addr, imm in mov_sites(bodies[k], PREFIX, BANK):
            sites[addr] = (imm & 0x0F,)

    lines, nbp = build({"sites": sites, "model": args.model}, hexfiles)
    lines += ["run"] * args.runs
    script_path = os.path.join(args.workdir, "dsp_model.cmd")
    open(script_path, "w").write("\n".join(lines) + "\n")
    print(f"breakpoints: {nbp} ({len(sites)} bank-switch + "
          f"{len(DSP_CMD_PORTS)} DSP-ack)")
    print(f"script: {len(lines)} lines -> {script_path}")

    log_path = os.path.join(args.workdir, "dsp_model_out.txt")
    env = dict(os.environ)
    env["PATH"] = SDCC_BIN + os.pathsep + env.get("PATH", "")
    with open(script_path) as fin, open(log_path, "w") as fout:
        subprocess.run([S51, "-t", "52", "-X", "12M", "bank00.hex"],
                       cwd=args.workdir, env=env, stdin=fin, stdout=fout,
                       stderr=subprocess.STDOUT, timeout=900)

    log = open(log_path, "rb").read().decode("utf-8", "replace")
    fix = re.findall(r"Stop at 0x([0-9a-f]+): \(104\) Breakpoint", log, re.I)
    ev = re.findall(r"Stop at 0x([0-9a-f]+): \(112\) Event break", log, re.I)
    loads = re.findall(r"Loading from (bank\d\d)\.hex", log)
    print(f"\nbank switches : {len(loads)}")
    print(f"fix stops     : {len(fix)}")
    print(f"event stops   : {len(ev)}")
    if loads:
        seq = [int(b[4:6]) for b in loads]
        print(f"banks visited : {len(set(seq))} -> {sorted(set(seq))}")
    hist = {}
    for a in fix:
        hist[a] = hist.get(a, 0) + 1
    top = sorted(hist.items(), key=lambda kv: -kv[1])[:8]
    print("busiest fix-stop PCs:")
    for a, c in top:
        print(f"   0x{a}  x{c}")
    if args.verbose:
        print("\n--- log tail ---")
        print("\n".join(log.splitlines()[-20:]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
