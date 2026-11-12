#!/usr/bin/env python3
"""Dump the RP500 edit buffer at the DSP stream, under uCsim.  NO HARDWARE.

The parameter store routine at bank 7 0xB8DA writes each preset parameter to
XRAM 0xF6AA + index*3 (three bytes per parameter).  The 86-record name table
at bank 6 0xC551 has CAB_TYPE at index 26 and AMP_TYPE at index 20, so the
working hypothesis is:

    amp  = 0xF6AA + 20*3
    cab  = 0xF6AA + 26*3

This script boots the *stock* image (the S3a stub does not touch the preset),
stops at the stock stream entry 0xBE97, and dumps 0xF6AA..0xF7DA.  It then
prints the 3-byte record for every index and flags any record whose first two
bytes look like a cab ID (571..626).

Usage: python editbuf_probe.py [--runs 3000]
"""
import argparse
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rp500_ucsim_run import to_ihex
from s3a_loader_stub import build_patched, mov_sites, S51, SDCC_BIN

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FW = os.path.join(ROOT, "01_source_firmware", "rp500_v20.bin")
BANK, NBANKS, PREFIX = 0x10000, 16, 0x2C80
EDIT, N_PARAM = 0xF6AA, 100
STREAM_ENTRY = 0xBE97


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=3000)
    ap.add_argument("--out", default=os.path.join(
        os.environ.get("TEMP", "."), "opencode", "rp500_editbuf"))
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    img = open(FW, "rb").read()
    patched, _ = build_patched(img)
    bodies = [patched[k * BANK:(k + 1) * BANK] for k in range(NBANKS)]
    hexfiles = []
    for k in range(NBANKS):
        p = os.path.join(args.out, "bank%02d.hex" % k)
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
        lines.append('commands %d file "%s"' % (n, os.path.basename(hexfiles[sites[addr]])))

    DSP_STATUS, DSP_DATA, DSP_CMD, READY = 0xD06E, 0xD070, 0xE000, 0xD0FF
    status = ("expression xram[0x%04x]=(xram[0x%04x]^4)|8"
              % (DSP_STATUS, DSP_STATUS))
    for port in (DSP_CMD, DSP_DATA):
        n += 1
        lines.append("break xram w 0x%04x" % port)
        lines.append("commands %d %s" % (n, status))
    lines.insert(0, "fill xram 0x%04x 0x%04x 0x01" % (READY, READY))

    # the ready-flag reads point at 0xD070; patch them to the scratch cell
    for k, off in ((15, 0xBE57), (14, 0x9A65)):
        at = k * BANK + off
        assert patched[at:at + 3] == bytes([0x90, 0xD0, 0x70]), hex(at)
        bodies[k] = bodies[k][:off] + bytes([0x90, READY >> 8, READY & 0xFF]) + \
            bodies[k][off + 3:]
        open(hexfiles[k], "w").write(to_ihex(bodies[k]))

    n += 1
    lines.append("break 0x%04X" % STREAM_ENTRY)
    lines.append("commands %d dx 0x%04x 0x%04x" % (n, EDIT, EDIT + N_PARAM * 3))
    lines += ["run"] * args.runs

    script = os.path.join(args.out, "editbuf.cmd")
    open(script, "w").write("\n".join(lines) + "\n")
    log_path = os.path.join(args.out, "editbuf_out.txt")
    env = dict(os.environ)
    env["PATH"] = SDCC_BIN + os.pathsep + env.get("PATH", "")
    with open(script) as fin, open(log_path, "w") as fout:
        subprocess.run([S51, "-t", "52", "-X", "12M", "bank00.hex"],
                       cwd=args.out, env=env, stdin=fin, stdout=fout,
                       stderr=subprocess.STDOUT, timeout=3600)

    log = open(log_path, "rb").read().decode("utf-8", "replace")
    data = {}
    for ln in log.splitlines():
        s = ln.strip()
        m = re.match(r"^0x([0-9a-f]{4})\s+([0-9a-f ]+)$", s)
        if not m:
            continue
        addr = int(m.group(1), 16)
        vals = [int(x, 16) for x in m.group(2).split()]
        for i, v in enumerate(vals):
            data[addr + i] = v

    print("edit-buffer dump: %d bytes captured from 0x%04X" % (len(data), EDIT))
    if not data:
        print("FAIL: no dump (uCsim did not reach 0x%04X)" % STREAM_ENTRY)
        return 1

    buf = bytes(data.get(EDIT + i, 0) for i in range(N_PARAM * 3))
    print("\nindex  address   bytes      word")
    for i in range(N_PARAM):
        rec = buf[i * 3:(i + 1) * 3]
        word = (rec[0] << 8) | rec[1]
        flag = "  <-- cab-like" if 571 <= word <= 626 else ""
        if any(rec) or flag:
            print("  %3d   0x%04X   %s   %5d%s"
                  % (i, EDIT + i * 3, rec.hex(" "), word, flag))
    print("\nAMP_TYPE index 20: %s" % buf[20 * 3:21 * 3].hex(" "))
    print("CAB_TYPE index 26: %s" % buf[26 * 3:27 * 3].hex(" "))
    return 0


if __name__ == "__main__":
    sys.exit(main())
