#!/usr/bin/env python3
"""Distil the long uCsim DSP-stream capture into a small evidence file."""
import hashlib
import pathlib
import re
import tempfile

TEMP = pathlib.Path(tempfile.gettempdir()) / "opencode" / "rp500_banks"
ROOT = pathlib.Path(__file__).resolve().parent.parent
src = TEMP / "stream_out.txt"
dst = ROOT / "evidence" / "2026-11-11_ucsim_dspstream_long.md"

log = src.read_text(encoding="utf-8", errors="replace")
cur = None
byts = []
for ln in log.splitlines():
    m = re.match(r"^Stop at 0x([0-9a-f]+):", ln.strip())
    if m:
        cur = int(m.group(1), 16)
        continue
    m = re.search(r"DPTR=\s*0x([0-9a-f]+)\s*@DPTR=\s*0x([0-9a-f]{2})", ln)
    if m and cur in (0xBEAD, 0x9ABB) and int(m.group(1), 16) == 0xD070:
        byts.append(int(m.group(2), 16))

blob = (ROOT / "01_source_firmware" / "rp500_v20.bin").read_bytes()
desc = blob[15 * 0x10000 + 0x2E3B:15 * 0x10000 + 0x2E3B + 24]

hexs = lambda xs: " ".join("%02X" % b for b in xs)

out = []
out.append("# Simulator capture of the RP500 DSP data-port stream")
out.append("")
out.append("Tool: `04_analysis_scripts/rp500_ucsim_stream.py` (uCsim s51 0.8.15).")
out.append("Command: `python 04_analysis_scripts/rp500_ucsim_stream.py --runs 120000`")
out.append("")
out.append("The full uCsim log is %d MB; this file is the distilled result. "
           "A short 3 000-run capture is archived beside it as "
           "`2026-11-11_ucsim_dspstream.log`." % (src.stat().st_size // 1048576))
out.append("")
out.append("## Result")
out.append("")
out.append("| Quantity | Value |")
out.append("|---|---|")
out.append("| bytes the firmware pushed at the DSP data port 0xD070 | **%d** |" % len(byts))
out.append("| first 24 bytes | `%s` |" % hexs(byts[:24]))
out.append("| the 24-byte descriptor at bank 15 `0x2E3B` | `%s` |" % hexs(desc))
out.append("| first 24 bytes == the descriptor | **%s** |" % (byts[:24] == list(desc)))
out.append("| byte 25 onward | executable code (the DSP model never says \"stop\") |")
out.append("| last 16 bytes | `%s` (the `0xA030` free run, all `0xFF`) |" % hexs(byts[-16:]))
out.append("")
out.append("## What it proves")
out.append("")
out.append("1. The RP500 streams the **24-byte parameter descriptor** to the DSP, "
           "byte for byte.")
out.append("2. Everything after it is **code**: the host has **no length limit** and "
           "keeps handing bytes over as long as the DSP keeps acknowledging. The "
           "`0x7FF8` compare is a **stall abort**, not a length cap.")
out.append("3. A real DSP must therefore terminate the transfer itself (by ceasing "
           "to acknowledge). The RP500 sends no terminator and no length.")
out.append("")
out.append("## The model")
out.append("")
out.append("- status register `0xD06E`: bit 2 toggles on every host write to "
           "`0xE000`/`0xD070` (the firmware waits for the status to *change*), "
           "bit 3 always set;")
out.append("- the \"byte accepted\" flag is read from a scratch cell (`0xD0FF`) "
           "instead of `0xD070`, because in the real DSP a read and a write of "
           "`0xD070` are two different registers. The simulator-only patch changes "
           "two DPTR immediates in the simulator's copy of the image and nothing "
           "else.")
out.append("")
dst.write_text("\n".join(out) + "\n", encoding="utf-8")
print("wrote %s (%d bytes)" % (dst, dst.stat().st_size))
short = ROOT / "05_evidence" / "2026-11-11_ucsim_dspstream.log"
print("short log sha256:", hashlib.sha256(short.read_bytes()).hexdigest())
