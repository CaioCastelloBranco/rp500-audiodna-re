# S3b — cabinet-conditional IR gate, proved in uCsim (no hardware)

**Result: PASS.** With the production gate (real 0xF6AA scan), the boot stream
still sends the **exact 24-byte descriptor** and nothing else. With the
simulator-only test gate that hard-codes the IR source, the same stream sends
**512 bytes of the IR table, in order, then 0xF5**, and the counter exits at
**0x0200** — twice, one per cabinet bank. Reproduce:

```
python 04_analysis_scripts/s3b_cab_trigger.py --runs 16000
```

## The build

Hooks in bank 15:

| Address | Stock | Patch |
|---|---|---|
| `0xBE97` (byte-send entry) | `MOV DPTR,#FF24` | `LJMP 0xE095` |
| `0xBE9E` (source base) | `ADD A,#3B; MOV 82h,A; MOV A,#2E; ADDC A,R6; MOV 83h,A` | `LJMP 0xE800` + 6×`FF` |

Code/data in the bank-15 free run:

| Address | Size | What |
|---|---|---|
| `0xE095` | 140 B | production gate (scan / stock / terminate) |
| `0xE800` | 26 B | source-base block (reads the RAM source cell) |
| `0xE200` | 512 B | IR table (test pattern in this build) |

State cells (free XRAM): `0xF8E0/1` source base, `0xF8E2/3` length,
`0xF8E4` terminator flag.

## What the gate does

At the **first byte** of a stream (counter == 0) it scans the 100 3-byte cells
at `0xF6AA` for `00 02 49` (585 = CAIO4X12):

* **found** → source `0xE200`, length 512, terminator `0xF5`
* **not found** → source `0x2E3B`, length 24, no terminator (the stock path)

At the length it writes `0xF5` only if the flag is set, then exits through the
stock epilogue `0xBEB0`. At boot the edit-buffer table is zero, so the
production gate cannot fire.

## What the simulator showed

| Case | Bytes at 0xD070 | First payload | Terminator | Counter | Passes |
|---|---|---|---|---|---|
| production gate, no cab value | 48 | exact 24-byte descriptor | absent | 0x0018 | 2 |
| test gate, IR source | 1026 | 512-byte table, in order | `0xF5` at 513 | 0x0200 | 2 |

The test gate (`s3b_gate_test.asm`) is **simulator-only**: it hard-codes the
IR cells so the downstream path can be exercised. The production gate
(`s3b_gate.asm`) contains the real scan and is what a hardware candidate uses.

## What is *not* proved

- **The scan itself on the real amp-change stream.** The uCsim boot stream runs
  before any cab write, so the edit buffer is zero. The test gate proves the
  IR path; the hardware test proves whether the cab value really lands at
  `0xF6AA` as `00 02 49`.
- **The DSP.** uCsim's model always acknowledges. Whether the AudioDNA2
  renders the 512-byte block is still the gate (S3b proper).
- **The real IR.** The table in this build is a test pattern; the hardware
  candidate must use zeros, a unit impulse, or a real 128-tap IR.

## Hardware candidate (next)

Production gate + source block + 512-byte IR table, minimal delta from stock.
Trigger: select **GSP2101 Clean Tube** (or Sat Tube); the unit forces cab
CAIO4X12 (585); the gate sees 585 and appends the IR on that cab stream.
Boot cannot fire; no flash write. Restore is the stock image through the same
updater.

Open choices before flashing: 128 taps (512 B, the S3a-proven length) or 208
taps (832 B, the mono path); and the first IR: zeros (dry/silent), a unit
impulse (flat), or a real WAV.
