#!/usr/bin/env python3
"""Run the RP500 firmware in uCsim with a faithful, self-driven bank switch.

Stage A.1 of the roadmap. The RP500 selects a flash bank by writing the bank
number into the low nibble of port P1 (see 06_deliverable/rp500_bank_map.md).
uCsim has no memory-write hook, but it can attach a command to a breakpoint
(`commands <nr> file "bankNN.hex"`), and the bank-select table lives in the
prefix that is byte-identical in all 16 banks. So the *simulator* can perform
the switch itself:

  * every `MOV P1,#imm` site becomes a breakpoint on the instruction *after*
    the MOV - so the write has already happened, exactly like real hardware,
    where the bank flips the moment P1 is written;
  * the command attached to that breakpoint loads that bank's 64 KB into ROM;
  * execution continues in the newly mapped bank.

Each site writes a fixed value, so the attached command can be static:

  * 20 sites in the replicated prefix (0x006B, 0x007C, 0x0093 and the
    16-entry table at 0x0200) - identical in every bank;
  * 7 bank-specific sites, each at an address used by exactly one bank.

The whole experiment is handed to uCsim as a command script on stdin, so the
simulator drives itself and nothing depends on interactive timing.

Usage:
    python rp500_ucsim_banks.py [--runs 200] [--image FILE] [--verbose]
"""
import argparse
import collections
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


def mov_sites(body, lo, hi):
    """Addresses of `MOV P1,#imm` (75 90 xx) inside [lo, hi)."""
    return [(i, body[i + 2]) for i in range(lo, hi - 2)
            if body[i] == 0x75 and body[i + 1] == 0x90]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", default=FW)
    ap.add_argument("--runs", type=int, default=200,
                    help="how many times the simulator is allowed to run "
                         "until the next bank switch")
    ap.add_argument("--workdir", default=os.path.join(
        os.environ.get("TEMP", "."), "opencode", "rp500_banks"))
    ap.add_argument("--verbose", action="store_true")
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

    # breakpoint sites: address -> (bank it selects, kind, owning bank)
    sites = {}
    conflicts = []
    for k in range(NBANKS):
        for addr, imm in mov_sites(bodies[k], 0, PREFIX):
            if addr in sites and sites[addr][0] != (imm & 0x0F):
                conflicts.append(addr)
            sites[addr] = (imm & 0x0F, "prefix", k)
        for addr, imm in mov_sites(bodies[k], PREFIX, BANK):
            if addr in sites and sites[addr][0] != (imm & 0x0F):
                conflicts.append(addr)
            sites[addr] = (imm & 0x0F, "bank%d" % k, k)
    if conflicts:
        print("WARNING: P1 sites with conflicting targets:",
              [hex(a) for a in sorted(set(conflicts))])

    npref = sum(1 for v in sites.values() if v[1] == "prefix")
    print(f"P1 write sites: {len(sites)} ({npref} in the replicated prefix, "
          f"{len(sites) - npref} bank-specific)")

    # --- build the uCsim command script -----------------------------------
    script = []
    n = 0
    for addr in sorted(sites):
        target = sites[addr][0]
        n += 1
        script.append("break 0x%04X" % (addr + 3))
        script.append('commands %d file "%s"' % (n, os.path.basename(hexfiles[target])))
    script += ["run"] * args.runs
    script_path = os.path.join(args.workdir, "switches.cmd")
    open(script_path, "w").write("\n".join(script) + "\n")
    print(f"command script: {len(script)} lines -> {script_path}")

    # --- run it -----------------------------------------------------------
    log_path = os.path.join(args.workdir, "sim_out.txt")
    env = dict(os.environ)
    env["PATH"] = SDCC_BIN + os.pathsep + env.get("PATH", "")
    with open(script_path) as fin, open(log_path, "w") as fout:
        subprocess.run([S51, "-t", "52", "-X", "12M", "bank00.hex"],
                       cwd=args.workdir, env=env, stdin=fin, stdout=fout,
                       stderr=subprocess.STDOUT, timeout=600)

    log = open(log_path, "rb").read().decode("utf-8", "replace")
    stops = re.findall(r"Stop at 0x([0-9a-f]+): \(104\) Breakpoint", log, re.I)
    loads = re.findall(r"Loading from (bank\d\d)\.hex", log)
    print(f"\nbank switches executed by the simulator: {len(loads)}")
    if loads:
        seq = [int(b[4:6]) for b in loads]
        print("  sequence:", " ".join(str(x) for x in seq[:30]),
              "..." if len(seq) > 30 else "")
        print("  distinct banks visited:", len(set(seq)),
              sorted(set(seq)))
    print(f"breakpoint stops: {len(stops)}")

    # --- faithfulness check ------------------------------------------------
    # For every stop, the site that was hit must really be a P1 write in the
    # bank that was mapped at the time; otherwise the breakpoint fired
    # spuriously (the same address means different code in another bank).
    bad = []
    cur = 0
    li = 0
    for line in log.splitlines():
        m = re.search(r"Loading from bank(\d\d)\.hex", line)
        if m:
            cur = int(m.group(1))
        m = re.search(r"Stop at 0x([0-9a-f]+): \(104\) Breakpoint", line, re.I)
        if m:
            addr = int(m.group(1), 16)
            site = addr - 3
            if cur in range(NBANKS):
                b = bodies[cur]
                if not (site + 2 < BANK and b[site] == 0x75 and b[site + 1] == 0x90):
                    bad.append((hex(addr), cur))
    print(f"spurious hits (address was not a P1 write in the mapped bank): {len(bad)}")
    if bad:
        print("  ", bad[:8])
    if args.verbose:
        print("\n--- log tail ---")
        print("\n".join(log.splitlines()[-25:]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
