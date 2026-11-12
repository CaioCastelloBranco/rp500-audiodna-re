# RP500 User-Cab Firmware — Build Roadmap

Status: Phase 0 **passed on hardware** (2026-11-10); Phase 1 **S1 closed**;
**S3a and S3b host logic PASS** (2026-11-11). Companion to
`gsp1101_to_rp500_feasibility.md` (§13–14: the port spec, corrected
2026-11-11) and `FINDINGS.md` (concise summary). Resume point:
`05_evidence/2026-11-11_s3b_checkpoint.md`.

Facts re-verified 2026-11-11 — `verify_all.py` **253/253**,
`04_analysis_scripts/audit_claims.py` **115/115**,
`04_analysis_scripts/prove_claims.py` **7/7** (old claims 0/7).

---

## Reassessment 2026-11-11 (after S3b host logic)

The **structure still holds**: S1 closed, S2c open, S3 is the project gate,
S4/S5 depend on it. Five specifics changed:

1. **The S3b trigger is solved.** It is not a cab-menu hook and not a static
   cab table. The RP500 writes the paired cab whenever the amp changes; the
   cab can only be changed afterwards. `GSP2101 Clean Tube` (amp 328) and
   `GSP2101 Sat Tube` (329) force **CAIO4X12** (cab 24, ID **585**). The gate
   therefore keys on the **cab value 585** in the edit buffer `0xF6AA`; the
   amp change is the deliberate, non-boot trigger. See
   `05_evidence/2026-11-11_amp_cab_pairs.md`.
2. **S3b host logic is done.** The production gate (140 B) scans `0xF6AA` for
   `00 02 49`; found -> IR table 512 B + `0xF5`, not found -> the stock 24-byte
   descriptor. uCsim: stock path exact 24 bytes/no terminator/counter `0x18`;
   test-gate IR path 512 bytes + `0xF5`/counter `0x200`, 2 passes each. Only
   the **hardware listen** remains. `05_evidence/2026-11-11_s3b_cab_trigger.md`.
3. **128 vs 208 taps is real.** The C59 loader has a **`mono/left toggle`**:
   mono -> 208 taps; otherwise 128 with the mono/left signal duplicated. The
   archive's `usercab_encode.py` still hard-codes 128 and reads the left
   channel only; fix it before the first hardware IR.
4. **S4 must split.** The RP500's preset protocol (`0x2D`/`0x39`) carries
   **preset parameters**, not a 2 KB IR record. The GSP carries the record
   with `0x7A`/`0x73` into a **separate user-data window**
   (`0x50000`-`0x54FFF`), while the RP500's `0x7A` in the updater log writes
   **firmware flash**. "No flash write and no new protocol" is therefore
   **not proved** for the record. S4a (UI/table) and S4b (storage/transport)
   are separate; S2c gates S4b.
5. **The 113-byte DSP table is identical in both banks**, so it is not
   per-cabinet and does not encode the cab. The cab is a **dependent
   parameter** written by the UI, not a per-model blob.

**Critical path:** **S3b hardware** (the DSP gate) and **S2c storage** (the
product gate), in parallel. Everything else waits on one or both.

**Goal:** the RP500 accepts a user IR (WAV) over USB-MIDI, stores up to ten of
them, lists them as `USER 1..10` in the cabinet menu, and plays them through
the DSP. The **RP500's own protocol** (gdigi/HMG) is the preset/UI path; the
2 KB record's store and transport are the open S4b question (not the GSP's
Jcabinet).

---

## 0. The corrected model (read this first)

**The RP500's DSP link does one thing:** it streams a **fixed 24-byte
parameter descriptor** from code space to the DSP data port `0xD070` — bank 14
from `0x2DC2`, bank 15 from `0x2E3B`, both read with `MOVC A,@A+DPTR`. The
block is **identical in both cabinet banks** and is immediately followed by
code, so it is a cabinet-independent **DSP parameter descriptor**. There are
**no factory cabinet IRs**: the factory cabinets are parametric DSP models (a
strict scan for 128-tap coefficient blocks finds zero in every image we have),
so an impulse response only exists in the **user-cabinet feature**, which the
GSP1101 added in firmware C54. The host differentiates cabinets by writing
the **cab parameter** (a dependent `MetaParam`); the 113-byte DSP table is
identical in both banks, so it is not per-cabinet and does not encode the cab.

The GSP1101 — which *does* have user cabinets — additionally has a **second,
variable-length DSP path**: 32 XRAM-sourced streams (2 per bank × 16 banks),
base `0x2445+index` (C48) / `0x2603+index` (C63), bounded by a length cell and
**terminated with `0xF5`**. The user IR is staged into that XRAM block
(`XRAM 0x1483+` → `XRAM 0x2603+`, count in `XRAM 0x14C3`) and streamed on that
path.

> **So the port is not a source swap.** Swapping `MOVC`→`MOVX` in the RP500's
> existing stream would change 24 bytes of parameters, not deliver an IR. The
> port is to **add** the GSP's terminated XRAM stream to the RP500 and point it
> at the staged user record.

**The gate is two-part**, and both halves must hold:

| | Question | Status |
|---|---|---|
| **G1** | Does the RP500's AudioDNA2 *accept* a terminated, variable-length block? | unmeasured |
| **G2** | Does it *render* that block as a convolution? | unmeasured |

G2 is the sharper one: the factory cabinets are *parametric models*, so an IR
is a different kind of data, and "a DSP that only implements parametric cab
models cannot render a user IR". Evidence for both: the RP500 and the GSP share
**23 addresses** in the host windows (RP500 v2.0, GSP C48, GSP C63) including
the complete handshake set — `0xD01E/1F/20, 0xD034, 0xD050, 0xD05A/5B,
0xD066/69/6D/6E/6F, 0xD070` and `0xE000/0xE200/0xE400/0xE800` — and the GSP
convolves with user IRs on the same part. The **parts list (2026-11-12)
confirms both units use the same `72-1002` AudioDNA2** (GSP: qty 2; RP500:
qty 1), so that is now chip-identity fact, not inference. The RP500 firmware
still never exercises the path, so **both halves have to be measured** (S3).

---

## Phase 0 — Reproducible build + hello-world on hardware (DONE)

| Item | Status | Artifact |
|---|---|---|
| Bank map: P1 low nibble = bank number; 16-bank table at `0x0200`; identical 0x2C80-byte prefix in all 16 banks | Done | `06_deliverable/rp500_bank_map.md` |
| `.DigBin` repack/unpack byte-exact | Done | `04_analysis_scripts/digbin_pack.py` |
| Hello-world: cab 24 `DIGISPKR`→`CAIO4X12`, flashed, unit shows new name | Done | `09_builds/rp500_v20_caio4x12.DigBin` |
| Updater rev 2.1 carrying the patched image, flashed | Done | `09_builds/updater_2.1/Digitech.RP.Series.Firmware.Updater.exe` |

Gate: hello-world string on a real RP500 — **PASSED** 2026-11-10 (log:
`05_evidence/2026-11-10_rp500_updater_flash.log`).

---

## Phase 1 — Port the user-cabinet feature

Each step is cheap, reversible and gated. Nothing in Phase 1 touches the
hardware until S3, and S3's hardware step is a *minimal* build.

### S1 — The DSP payload path (CLOSED)

| Fact | Where |
|---|---|
| RP500 streams to `0xD070` from **two code-sourced sites** | bank 14 `0x9ABA`, bank 15 `0xBEAC` |
| both reads are `MOVC A,@A+DPTR` (code space) | `0x9AB6`, `0xBEA8` |
| sources | `0x2DC2` (bank 14), `0x2E3B` (bank 15) — **24 bytes, identical**, then code |
| a third path also writes `0xD070` | the 113-byte configuration block at bank 14 `0x2C80` / bank 15 `0x2CBB` (identical), copied into DSP registers `0xD000`–`0xD070`, skipping `0xD059` |
| the 16-bit byte counter | XRAM `0xFF24` (hi) / `0xFF25` (lo) |
| the source address | `base + counter` (DPTR built with `ADD A,#lo` / `ADDC A,R6`) |
| flow control | status `0xD06E` bits 2/3; the DSP's ready flag is read from `0xD070` |
| setup helper | bank 15 `0xDBB3` writes `0xD020` / `0xD05B` / `0xD06D` / `0xD06F` |
| **no length limit** | the host keeps sending as long as the DSP acknowledges; the `0x7FF8` compare (`0xBE3D`/`0xBE40`) is a **stall abort** on the *"status did not change"* path, not a byte cap. **Measured:** 118 650 bytes and still going, with an always-acknowledging DSP |
| cross-reference | the **RP1000 runs the same routine**, byte-for-byte identical except for the scratch counter cell (`0xFFAA/0xFFAB` vs `0xFF24/0xFF25`) — cross-reference structurally, never byte-for-byte |

The GSP's counterpart (the path we must add) lives in C63 bank 15 at `0x2F12`
and `0x3072`; it reads `XRAM 0x2603+index`, stops when `index == length`
(`XRAM 0x2704`) and writes **`0xF5`** to `0xD070` as the terminator.

**Empirical anchor:** `04_analysis_scripts/rp500_ucsim_stream.py` captures the
real stream under uCsim with a modelled DSP — the first 24 bytes at `0xD070`
are exactly the descriptor at `0x2E3B`, and everything after is code
(`05_evidence/2026-11-11_ucsim_dspstream_long.md`).

> **Consequence for the hook.** There is no "blob A vs blob B" to select: the
> descriptor is cabinet-independent. The hook we need is *"when `USER n` is
> active, run the new terminated XRAM stream instead of the descriptor
> stream"* — one `LJMP` in the replicated prefix (identical in all 16 banks),
> as established for S1 before the correction.

### S2 — Where the presets live (PARTLY CLOSED — `rp500_storage.md`)

Three measured facts:

| Fact | Evidence |
|---|---|
| The device's flash is exactly **1 MB** and a firmware update **rewrites all of it** | the device's own flash map (`0x78`): `maxBlock=256, segments=16`; 4 039 of 4 096 blocks sent. The all-`0xFF` skip applies **only in segment 0** — **all 548** empty blocks in segments 1–15 are written, including bank 1's 24 528-byte free run at `0xA030` |
| The firmware has **no MOVX-visible bulk store** | 215 distinct written XDATA addresses, and none of them is a data area: DSP window `0xD000`–`0xDFFF`, DSP command ports `0xE000`–`0xEFFF`, 8051 scratch `0xF000`–`0xFFFF` — plus **3** stray writes below `0xD000`. The ~3 000 `MOVX @R0/@R1` accesses are all low XRAM scratch |
| There is **no MOVX-visible external device** | no `MOVX` to any paged range |

**Correction (recorded, not dropped):** the first answer was "therefore the
presets are inside the AudioDNA2". That is **too strong** — the XDATA map only
rules out a **MOVX-visible** device. A **bit-banged serial store (SPI/I²C) is
invisible to it**, and the firmware's `ERASE ` / `FLERR ` / `BUSY ` strings are
exactly what such a driver emits. gdigi's bank list (`PRESETS_MEDIA_CARD`,
`PRESETS_EXTERNAL`) confirms the platform has **several persistent back-ends**.

⇒ The user bank's physical store is **still open**; the leading candidate is an
external serial device driven from bank 7. What *is* closed: it is not the
firmware flash, not the `0x5FD0` free run and not XRAM.

### S2b — The preset protocol (CLOSED — `rp500_preset_protocol.md`)

The RP500 speaks the **gdigi/HMG protocol**: its MIDI dispatch table at bank 7
`0x699E` carries **all 12** of gdigi's preset message IDs, with handlers at
`0x6Axx` (machine-checked, `audit_claims.py` §12c).

**"Save preset" is one message** — `MOVE_PRESET` (`0x39`):

```
<srcBank> <srcIndex> <dstBank> <dstIndex> <name>\0 <flags>
```

gdigi stores with `src = edit buffer (4,0)`, `dst = user (1,x)`, `flags = 1`.
Parameters go in separately with `RECEIVE_PRESET_PARAMETERS` (`0x2D`); a whole
preset is pulled with `REQUEST_PRESET` (`0x2A`); everything is dumped with
`REQUEST_BULK_DUMP` (`0x18`).

⇒ **The port uses the RP500's own protocol, not the GSP's Jcabinet protocol** —
no Super7 packing, no XOR checksum, no new protocol class, and gdigi is already
a working client.

### S2c — Find the serial store (NEW, next)

Follow the `MOVE_PRESET` user branch — bank 7 `0xABD2` → `LCALL 0B4B`
(`R7 = 0x3B`) → target `0xD8AD` — through to the routine that emits `ERASE ` /
`FLERR `, and identify the device and its address layout.

Gate: the physical store and its per-slot layout are known.

### S3 — The gating experiment (G1 + G2)

**This is the only experiment that can stop the project.** It is non-
destructive and needs no UI.

**Half 1 — in the simulator: DONE (2026-11-11).** A 26-byte gate + a 512-byte
table on the *stock* firmware makes the DSP data port receive exactly **512
bytes, in order, then `0xF5`, then nothing** (twice — the firmware invokes the
stream routine once per cabinet bank). The stock handshake, setup helper and
epilogue are untouched; only the source and the termination are ours. 539 bytes
differ from stock, all in provably-unused space.

```
python 04_analysis_scripts/s3a_loader_stub.py
```

Evidence: `05_evidence/2026-11-11_s3a_loader_stub.md` (+ the uCsim log). This
proves the **host half**; it says nothing about the DSP.

**Half 2 — on hardware (S3b).** The host logic is done; the hardware build
reuses the production gate:

- the trigger is the **cab value 585** (CAIO4X12), written when the amp is set
  to **GSP2101 Clean Tube** or **Sat Tube**; the gate scans `0xF6AA` for
  `00 02 49`, so boot cannot fire;
- choose the first IR: zeros (dry/silent), a unit impulse (flat), or a real
  WAV. **128 taps = 512 B** (the S3a-proven length); **208 taps = 832 B** (the
  loader's **mono** path, `mono/left toggle`). The archive encoder still
  hard-codes 128 and must be fixed for stereo;
- keep the stock image on disk; restore with the same updater.

Gate: the DSP renders it — cab goes dry (zeros) or changes (real IR). Run it
twice, full preset vs everything bypassed, to separate "no mode" from "no
cycles". If it does not render, the next variant sends the descriptor first,
as the GSP does.

*Safety:* this build is a minimal delta from the last known-good image; the
stock image stays on disk; the restore path is the same updater with the stock
image.

### S4 — Host work, split in two (only if S3 passes)

**S4a — UI/table (straightforward).** Extend the cab table 28 → 38 entries,
add `USER 1..10` names, and decide how the amp→cab pairing treats user cabs.
The RP500's own preset protocol (`0x2D`/`0x39`) is fine for the **edit
buffer** and the menu.

**S4b — storage and transport (open; gated by S2c).** A 2 KB IR record is not
a preset parameter. The GSP carries it with `0x7A`/`0x73` into a separate
**user-data window** (`0x50000`-`0x54FFF`); the RP500's `0x7A` in the updater
log writes **firmware flash**, not a user store. Whether the RP500's serial
preset store can hold ten 2 KB records, and which command writes it, is still
open. Do **not** claim "no flash write / no new protocol" for the record until
S2c answers.

Gate: the unit shows `USER 1..10`, accepts a WAV through the chosen store, and
plays it after a reboot.

### S5 — Verify on hardware

Upload with the chosen host path (the RP500's own protocol for presets; the
record path chosen in S4b), select `USER 1`, listen, power-cycle.

Gate: the IR survives a reboot.

---

## Phase 2 — Housekeeping (DONE)

| Item | Status | Artifact |
|---|---|---|
| Every load-bearing claim re-derived from the images | Done | `04_analysis_scripts/audit_claims.py` (115/115) |
| Every **changed** claim proved with a discriminating test (old vs new) | Done | `04_analysis_scripts/prove_claims.py` (7/7), `05_evidence/claims_ledger.md` |
| Archive under version control, byte-exact | Done | git `main`, tag `baseline-2026-11-11`; `00_master/TOOLCHAIN.md` "Version control" |
| **S3a — the IR loader proved in the simulator** | Done | `04_analysis_scripts/s3a_loader_stub.py`, `05_evidence/2026-11-11_s3a_loader_stub.md` |

---

## Toolchain (installed, proven)

| Tool | Version | Role |
|---|---|---|
| SDCC | 4.5.0 | mcs-51 **compiler** (`sdcc`), assembler (`sdas8051`), linker (`sdld`) |
| uCsim `s51` | 0.8.15 | 8051 **simulator** (bank switch + DSP handshake + stream capture) |
| Zig | 0.17.1 | host compiler for the "compile twice" test oracle |
| `at51`/`delsum`/`biodiff` | 8051Enthusiast | 8051 RE toolbox |
| Git | 2.56.0 | version control for the archive |

Pattern: **compile twice, test once** — portable C → host build = oracle, SDCC
build = what goes into the firmware. Verified end to end with
`04_analysis_scripts/ucsim_check.py`.

The stock firmware runs under the simulator (3.65 billion ticks), the
bank-switch mechanics are proven (3 001 switches, 0 spurious hits; reset path
selects bank 15), and the DSP handshake is modelled in
`04_analysis_scripts/rp500_ucsim_dsp.py`; the stream capture lives in
`04_analysis_scripts/rp500_ucsim_stream.py`.

---

## Risk register

| Risk | Likelihood | Mitigation |
|---|---|---|
| **The DSP rejects or cannot render the IR block (G1/G2)** | ~30% | **The one real gate** — S3 tests it before anything else is written; if it fails, the project stops with a documented negative result |
| **The DSP has no room for a user IR** | ~20% | Part of G2; the S3 hardware build answers it directly. The GSP stores IR records *outside* the DSP, so if the RP500's DSP is the constraint, the feature needs a different vehicle |
| Bad image | low | Bootloader fallback is reported by the uploader author; never tested destructively; every build stays a minimal delta from stock, and the stock image stays on disk |
| Bank space / reachability | low | `0x5FD0` free run for stubs; proven all-`0xFF` (24 528 bytes). **Not persistent** — a firmware update overwrites it (S2) |
| Atomicity failure (power loss mid-store) | low | The store is the device's, not ours; the host protocol must be idempotent and the device must own the commit |
| **The user-bank store is never located** | medium | S2c: bounded static search (bank 7 `0xABD2` → `0xD8AD` → `ERASE `/`FLERR `). Not on the S3 critical path — the DSP gate is tested first |
| Bank/hook mistakes | low | Emulator unit tests before flashing |
| **Single-analyst interpretation error** | ~3–5% | Mitigated: uCsim's independent disassembler agrees with ours; the emulator's behaviour matched the static prediction; the manuals are independent human sources; every changed claim has a discriminating test in `claims_ledger.md`. **Residual:** no second reviewer — a full prose re-read against the ledger and an independent re-derivation in Ghidra would close it |

---

## Build outputs

| File | What it is |
|---|---|
| `09_builds/rp500_v20_caio4x12.bin` | patched 1 MB flat image (hello-world) |
| `09_builds/rp500_v20_caio4x12.DigBin` | same image in the updater container |
| `09_builds/flash_ready/rp500V20.DigBin` | drop-in name for any 2.0 slot |
| `09_builds/updater_2.1/Digitech.RP.Series.Firmware.Updater.exe` | updater with a 2.1 RP500 revision carrying the patched image |

**What we will not attempt:** new DSP commands or register-level changes (the
register map is shared with the GSP), stereo user IRs (the manual specifies
left channel only, applied to both outputs), a GSP-identical UI.

---

## Reproduce everything

```
python verify_all.py                        # 253 assertions
python 04_analysis_scripts/audit_claims.py  #  102 assertions
python 04_analysis_scripts/prove_claims.py  #   7 claims proved
python 04_analysis_scripts/digbin_pack.py verify 01_source_firmware/rp500V20.DigBin
python 04_analysis_scripts/patch_cab_name.py --old DIGISPKR --new CAIO4X12
python 04_analysis_scripts/patch_updater.py
python 04_analysis_scripts/rp500_ucsim_stream.py --runs 3000   # DSP stream capture
```

The cab list is a 28-entry pointer table at `bank4:0x478E` pointing at 9-byte
records from `bank4:0x3486`; the record is the menu string, so one 8-byte edit
renames the cabinet. `patch_cab_name.py` refuses to run if the old name is not
unique in the image.

Commit discipline: verify → commit, in that order, so the tree is never
committed in a state where the checks fail.

---

## Next action

**Critical path, in parallel:**

1. **S3b hardware listen** (the DSP gate). Build the production gate + the
   chosen IR; flash only with the owner's go-ahead; select **GSP2101 Clean
   Tube**; listen; restore stock. If it does not fire, the cab value is not at
   `0xF6AA` — trace the `0x2D`/DSP cab path next. If it fires but nothing
   changes, the DSP received the block but did not render it (G2 negative).
2. **S2c serial store** (the product gate). Follow `MOVE_PRESET` user branch
   bank 7 `0xABD2` → `0x0B4B` → `0xD8AD` to the `ERASE `/`FLERR ` routine;
   identify the device and whether ten 2 KB records fit. Static; no hardware.

**Only after both:** S4a (UI/table), S4b (transport into the store), S5
(reboot persistence).

**If S3b is declined**, the archive stands as: mechanism fully specified, host
half proved in the simulator (S3a + S3b host logic), DSP gate unmeasured. That
is a legitimate stopping point.

**Resume point:** `05_evidence/2026-11-11_s3b_checkpoint.md`.
