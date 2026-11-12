# Simulator capture of the RP500 DSP data-port stream

Tool: `04_analysis_scripts/rp500_ucsim_stream.py` (uCsim s51 0.8.15).
Command: `python 04_analysis_scripts/rp500_ucsim_stream.py --runs 120000`

The full uCsim log is 51 MB; this file is the distilled result. A short 3 000-run capture is archived beside it as `2026-11-11_ucsim_dspstream.log`.

## Result

| Quantity | Value |
|---|---|
| bytes the firmware pushed at the DSP data port 0xD070 | **118650** |
| first 24 bytes | `C9 12 12 34 12 10 00 09 01 01 0C 50 0A 20 01 00 12 AB 02 0A ED 02 00 1F` |
| the 24-byte descriptor at bank 15 `0x2E3B` | `C9 12 12 34 12 10 00 09 01 01 0C 50 0A 20 01 00 12 AB 02 0A ED 02 00 1F` |
| first 24 bytes == the descriptor | **True** |
| byte 25 onward | executable code (the DSP model never says "stop") |
| last 16 bytes | `FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF` (the `0xA030` free run, all `0xFF`) |

## What it proves

1. The RP500 streams the **24-byte parameter descriptor** to the DSP, byte for byte.
2. Everything after it is **code**: the host has **no length limit** and keeps handing bytes over as long as the DSP keeps acknowledging. The `0x7FF8` compare is a **stall abort**, not a length cap.
3. A real DSP must therefore terminate the transfer itself (by ceasing to acknowledge). The RP500 sends no terminator and no length.

## The model

- status register `0xD06E`: bit 2 toggles on every host write to `0xE000`/`0xD070` (the firmware waits for the status to *change*), bit 3 always set;
- the "byte accepted" flag is read from a scratch cell (`0xD0FF`) instead of `0xD070`, because in the real DSP a read and a write of `0xD070` are two different registers. The simulator-only patch changes two DPTR immediates in the simulator's copy of the image and nothing else.

