# RP500 User-Cab Firmware — Findings

**Objective:** Can the GSP1101 user-cabinet (IR) feature be ported to the DigiTech
RP500?

**Answer (re-verified 2026-11-11):** The *mechanism* is portable and every byte
of the host-side protocol is recovered — but **the port is not the one-byte
source swap it was previously described as.** Re-verification of the RP500
image against the GSP images shows:

> The RP500's DSP link carries only a **fixed 24-byte parameter block** read
> from code space. The GSP1101's user-cabinet feature runs on a **completely
> separate, variable-length, XRAM-sourced DSP stream** that the RP500 firmware
> does not have. The RP500 therefore needs that path **added**, not patched.

Everything below is re-derived from the artifacts by
`04_analysis_scripts/audit_claims.py` (111/111) and `verify_all.py` (253/253);
nothing is carried over from memory.

---

## 1. What the feature is

The GSP1101 accepts a user IR (WAV) over USB-MIDI with the **stock Jcabinet
protocol**, stores up to ten of them, lists them as `USER 1..10` in the cabinet
menu and plays them through the DSP. The IR is **mono** — the downloader takes
the **first 128 samples of the left channel** and applies them to **both
outputs** (GSP1101 C54 release notes, lines 303–310).

The stored record is **2048 bytes** (`usercab_encode.py`):

| Offset | Size | Content |
|---|---|---|
| `0x000` | 4 | `00 5C 00 05` header |
| `0x004` | 8 | `00 05`, slot×8, `00 00 00 08 00` |
| `0x00C` | 4 | sample count, BE32 (0x80 = 128) |
| `0x010` | 512 | **128 × signed 32-bit BE coefficients** |
| `0x7E7` | 23 | filename, NUL padded |
| tail | 2 | slot, flag (flag = audition/store) |

---

## 2. Findings

| # | Finding | Evidence |
|---|---|---|
| 1 | The RP500 writes the DSP data port `0xD070` from **two code-sourced stream sites** — bank 14 at `0x9ABA`, bank 15 at `0xBEAC` — both `MOVC A,@A+DPTR`. It has **zero** XRAM-sourced streams. | `audit_claims.py` §1 |
| 2 | Those streams read a **24-byte block** at `0x2DC2` (bank 14) / `0x2E3B` (bank 15), **identical in both banks**, and the block is **immediately followed by executable code** (`0x2DDA` / `0x2E53` = `E6` = `MOV A,@R0`, the head of a function). | `audit_claims.py` §2 |
| 3 | ⇒ The RP500's streamed block is a cabinet-independent **DSP parameter descriptor**, not an impulse response. **There are no factory cabinet IRs anywhere in this product family** — the factory cabinets are **parametric DSP models** (a strict scan for 128-tap coefficient blocks finds **zero** in the RP500, the GSP C48/C63 and the GSP V20 images), so an IR is a thing that only exists in the **user-cabinet feature**, which the GSP1101 added in firmware C54. The RP500 manual never mentions impulse responses. | `README_FIRST.md` (strict FIR-block scan); `audit_claims.py` §2 |
| 3b | A **third** path also reaches `0xD070`: a **113-byte DSP configuration block** (bank 14 at `0x2C80`, bank 15 at `0x2CBB` — **byte-for-byte identical**) copied one byte at a time into DSP registers `0xD000`–`0xD070`, skipping `0xD059`. Its last byte lands on `0xD070`. | `audit_claims.py` §1b |
| 4 | The GSP1101 has a **second, variable-length DSP path**: 32 XRAM-sourced stores = **2 interrupt handlers × 16 code banks** (both handlers read the same source/index/length), base `0x2445+index` (C48) / `0x2603+index` (C63), bounded by a length cell (XRAM `0x2546` / `0x2704`) and **terminated with `0xF5`** written to `0xD070`. | `audit_claims.py` §3; `two_chip_test.py` |
| 5 | The GSP's user IR is **staged in XRAM** before it is streamed: a copy routine (C63 bank 15 `0xD7D1`) moves `XRAM 0x1483+index` → `XRAM 0x2603+index`, count in `XRAM 0x14C3`. | `audit_claims.py` §3 |
| 6 | The GSP also has the **same two code-space streams** as the RP500 (banks 14/15), with a **16-byte** block that **shares 8 bytes** with the RP500's 24-byte block — i.e. the same platform routine, a different parameter descriptor. | `audit_claims.py` §3 |
| 6b | **The variable-length block loader predates the user-cab feature.** C48 (no user cabs) already carries the whole loader — receive buffer `0x1483`, source index `0x14C5`, count `0x14C3`, destination index/length `0x2546`/`0x2547`, block base `0x2445` — and C63's copy is the **same code with the same reference counts**, merely relocated (`0x2704`/`0x24FD`/`0x2603`). The factory code-space descriptor is **byte-identical** in both builds. So the IR feature added **no transport, no DSP command and no loader code** — it reused generic plumbing. The RP500 has **none** of it (0 references to every loader cell). The transport is older still: the **oldest build (v11)** already has the same two handlers, with the cells merely moved (`0x2164`/`0x1F5D`/`0x2B4F`, source `0x2063+index`). | `audit_claims.py` §12d; `two_chip_test.py` |
| 6c | **C48 is not a partial IR update.** Every GSP1101 build in the archive — **v1.1**, v1.2, v1.3, v2.0 (official), C20, C48, C63 — has the *same* 2 code-space + **32 XRAM** streams. Only **C63** has the `USER 1..10` cab names, so the feature arrived in one step. And `USER_CAB` exists in **every** build including v1.1, so that string is platform vocabulary, not work in progress. | `audit_claims.py` §12e |
| 6d | **The firmware does not address the GSP's two AudioDNA2 chips independently.** `0xFDFC` is **RP500-only** (49 refs; 0 in every GSP build v11→C63), so the old "GSP selects its second chip via `0xFDFC`" claim is wrong. The IR path writes one `0xD070` port and one `0xE000` flow-control byte; neither handler touches `0xE200`/`0xE400`. The only GSP-only two-select access is `0xE400` ← `0x40`/`0x80` + read `0xEC40`, a status/ID path. The RP500 board carries one AudioDNA2 (U25, `72-1002 GREEN`). Whether the two GSP chips differ in microcode is **invisible to static analysis** and remains open. | `05_evidence/2026-11-12_gsp_two_chip_test.md`, `two_chip_test.py` |
| 7 | The RP500 and the GSP use the **same host↔DSP handshake registers**: **23 addresses are common to all three images** (RP500 v2.0, GSP C48, GSP C63) — the 13 DSP-window registers `0xD01E/1F/20, 0xD034, 0xD050, 0xD05A/5B, 0xD066/69/6D/6E/6F, 0xD070` and the command ports `0xE000/0xE200/0xE400/0xE800`. Same chip family ⇒ the variable-length path is very likely present in the RP500's DSP — **but that is a hypothesis, not a measurement.** | static analysis |
| 8 | The RP1000 V12 runs the **same loader** (same two code-space streams, same bases `0x2DC2`/`0x2E3B`, same DSP port counts) — a shared AudioDNA2 platform routine, not an RP500 quirk. | `audit_claims.py` §5 |
| 9 | The host has **no length limit** on the DSP stream. The `0x7FF8` compare (bank 15 `0xBE3D`/`0xBE40`) sits on the *"the DSP status did **not** change"* path, so it is a **stall abort** (≈256 consecutive polls with an unchanged status, once the byte counter's high byte reaches `0x7F`/`0x80`), not a length cap. *(This corrects the earlier "cap 0x7FF8 bytes" wording.)* | `audit_claims.py` §4 |
| 9b | **Measured, not inferred:** with a DSP model that always acknowledges, the firmware pushed **118 650 bytes** at `0xD070` and was still going — the first 24 are the descriptor, everything after is **code**. A real DSP must terminate the transfer by ceasing to acknowledge; the RP500 sends no terminator and no length. | `05_evidence/2026-11-11_ucsim_dspstream_long.md`, `rp500_ucsim_stream.py` |
| 9c | **The host half of the IR path is proved in the simulator.** A 26-byte gate + a 512-byte table on the stock firmware makes the data port receive **512 bytes, in order, then `0xF5`, then nothing** (twice — one invocation per cabinet bank). The stock handshake, setup helper and epilogue are untouched; 539 bytes differ from stock, all in unused space. | `04_analysis_scripts/s3a_loader_stub.py`, `05_evidence/2026-11-11_s3a_loader_stub.md` |
| 10 | The **upload protocol** is fully recovered: `0x7A` data + `0x73` commit, Super7 packing, XOR/`0x7F` checksum; commit **flag = audition/store**; **gain = dB at upload**; **10 slots**; the upload targets the **selected slot**. | `usercab_encode.py`, C63 release notes |
| 11 | The **build works on hardware**: patched image flashed via updater rev 2.1, cab 24 renamed, unit boots. | `05_evidence/2026-11-10_rp500_updater_flash.log` |

---

## 3. What changed on re-verification (important)

The earlier draft of this file described the port as a **source swap**: change
`MOVC A,@A+DPTR` to `MOVX A,@DPTR` in the RP500's stream so it reads the
stored user record instead of code space. **That is wrong**, and the audit
proves why:

| | RP500 | GSP1101 |
|---|---|---|
| code-space streams to `0xD070` | 2 (24-byte parameter descriptor) | 2 (16-byte parameter descriptor) |
| other writes to `0xD070` | 1 (the 113-byte configuration block) | many |
| **variable-length XRAM streams** | **0** | **32** (the user-IR path) |
| terminator `0xF5` | never written | yes |

The RP500's 24-byte block is a *parameter descriptor*, identical for every
cabinet, and the emulator confirms byte-for-byte that it is what reaches the
DSP. Swapping its source would not deliver a user IR; it would deliver
different 24 bytes. The GSP's user IR travels on the **other** path.

**Corrected port shape:** *add* a GSP-style terminated XRAM stream to the
RP500, stage the 2048-byte record into XRAM, and select it for `USER 1..10`.

---

## 4. The port (corrected spec)

| Piece | What | Size | Risk |
|---|---|---|---|
| **Receiver** | the RP500's own preset protocol: `RECEIVE_PRESET_PARAMETERS` (`0x2D`) to fill the edit buffer, `MOVE_PRESET` (`0x39`) to commit a slot | already in firmware | low — and **gdigi is a working client** |
| **Storage** | the **device** keeps the slots; the host never writes the store. Medium not yet pinned (S2c) | n/a | medium |
| **Staging** | copy the selected record into XRAM (the GSP does `XRAM 0x1483+` → `XRAM 0x2603+`) | ~30 B | low |
| **DSP stream** | **new**: XRAM → `0xD070`, length-bounded, terminated with `0xF5`, status-polled at `0xD06E` — a port of the GSP's pull routine, one copy in the replicated prefix | ~80 B | **medium — the DSP must accept it** |
| **UI** | cab table 28 → 38 entries, `USER 1..10` | table + menu branch | medium |

**Storage location:** the RP500's firmware flash is exactly 1 MB and fully
overwritten by an update, and the `0x5FD0` free run goes with it — so there is
**no host-side store**, in flash or in XRAM. The slots are the device's; the
medium is still being pinned (`rp500_storage.md`, `rp500_preset_protocol.md`).

**The gate:** everything above is host-side work we can do. What it cannot do
is make the RP500's AudioDNA2 *render* a user IR. Now that we know there are
no factory IRs, that means something sharper: the factory cabinets are
**parametric models** (an index into the DSP), while a user IR is a
**different kind of data** that needs the DSP's convolution path — "a DSP that
only implements parametric cab models cannot render a user IR". The RP500's
firmware never asks its DSP for one, so we cannot read the capability off the
image — it has to be **measured** (see §7).

---

## 5. What we will NOT attempt

- New DSP commands or register-level changes — the register map is shared with
  the GSP; the path we need is one the GSP already uses
- Stereo user IRs — the manual specifies left channel only, applied to both
  outputs
- A GSP-identical UI — the RP500's cab list is 8-character names
- Any destructive experiment on the unit (bootloader fallback is reported, not
  tested)

---

## 6. Recheck of assumptions (all verified by test)

| Assumption | Test | Verdict |
|---|---|---|
| The `0x5FD0` free run is genuinely unused | dumped bank 1 `0xA030`..`0xA030+0x5FD0`: **24 528 bytes, 0 non-`0xFF` bytes**; ends exactly at the bank boundary | **HOLDS** |
| Firmware flash = exactly 1 MB, fully overwritten by update | device flash map (`0x78`): **16 segments × 0x10000**; 4 039 of 4 096 blocks sent, and the all-`0xFF` skip applies **only inside segment 0** — all 548 empty blocks elsewhere are written | **HOLDS** |
| The RP500's DSP stream is code-sourced | 2 stores to `0xD070`, nearest preceding load is `MOVC` in both cases | **HOLDS** |
| The GSP's IR path is XRAM-sourced | 32 stores whose nearest preceding load is `MOVX`; one base + index each | **HOLDS** |
| The RP500's streamed block is not an IR | 24 bytes, identical in both cabinet banks, followed by code | **HOLDS** |
| Prefix identical in all 16 banks; same address = different code per bank | asserted by `verify_all.py`; bank 14 vs bank 15 at `0x80D2` disassemble differently | **HOLDS** |
| GSP's XRAM path predates the user-cab feature | the oldest build (v11) already has the same 2 handlers (32 sites = 2 × 16 banks), with cells moved; C48/C63 are byte-identical to each other | **HOLDS** |
| The `0x5FD0` free run is **not** persistent storage | the updater's all-`0xFF` skip applies only to segment 0; **all 548** empty blocks in segments 1–15 (including bank 1's `0xA030` free run) are written on every update | **HOLDS** |
| The RP500 has **no MOVX-visible store** | 215 distinct written XDATA addresses, all in the DSP window / DSP command ports / 8051 scratch; **3** stray writes below `0xD000` | **HOLDS** |
| "…therefore the presets are in the AudioDNA2" | — | **REVISED** — a bit-banged serial device is invisible to the XDATA map; see the next row |
| The RP500 speaks the **gdigi/HMG preset protocol** | its MIDI dispatch table (bank 7 `0x699E`) carries **all 12** of gdigi's preset message IDs, with handlers at `0x6Axx` | **HOLDS** (machine-checked) |
| "Save preset" = **`MOVE_PRESET` (0x39)** | payload `<srcBank> <srcIndex> <dstBank> <dstIndex> <name>\0 <flags>`; gdigi stores edit buffer (`4`,0) → user (`1`,x) | **HOLDS** |
| The platform has **several preset back-ends** | gdigi: `SYSTEM 0`, `USER 1`, `ARTIST 2`, `MEDIA_CARD 3`, `EDIT_BUFFER 4`, `FACTORY2 5`, `EXTERNAL 6`; the firmware branches on the bank in `MOVE_PRESET` | **HOLDS** |
| The RP500's DSP can accept a user IR | **not tested** — the RP500 firmware never uses a variable-length path | **OPEN** |

---

## 7. Remaining unknowns (in priority order)

| # | Question |
|---|---|
| S2 | ~~**Where do user cabs live on the RP500?**~~ — **PARTLY CLOSED** (`06_deliverable/rp500_storage.md`): not in the firmware flash (1 MB, fully rewritten) and not in XRAM (no store). The **protocol** is closed (`rp500_preset_protocol.md`); the **physical store** is still open — the leading candidate is a serial (SPI/I²C) device, which the XDATA map cannot see. |
| S2b | ~~Decode the bulk preset service~~ — **CLOSED** (`rp500_preset_protocol.md`): the RP500's dispatch table matches gdigi's IDs 12/12; `MOVE_PRESET` (0x39) framing recovered; banks mapped. |
| S2c | **Find the serial store** — follow the `MOVE_PRESET` user branch (bank 7 `0xABD2` → `0x0B4B` → `0xD8AD`) to the routine that emits `ERASE `/`FLERR `, and identify the device and its layout. |
| S3 | **Can the RP500's AudioDNA2 take and render a user IR?** — the single gating question. Simulator first (patched stream routine: XRAM source, `0xF5` terminator, DSP handshake model), then a minimal hardware build that sends a 512-byte record and produces audible output. |
| S4 | **Which code applies a cabinet, and where is the cab index?** — the port needs this selector (to fire an IR block for one cab). *Negative results so far (2026-11-11):* the prefix table at `0x18DC` is **not** a per-cabinet selector — its only caller does a 2×2-bit index and reaches 4 entries; and the cab pointer table at `0x478E` has **no direct code reference** in bank 4 (zero `MOV DPTR,#47xx`), so its access path is indirect. Bank 4's string pool starts at `0x2C80` and is read by a prefix helper at `0x0569`. *New handles (software audit):* the cab parameter is `CabType_1 = 2560` (`0x0A00`), value `608` for cab 24; the RP500's 28-entry ID table and C63's 38-entry table are the same list plus 10 user IDs; the 113-byte DSP tables are **identical** in both banks, so they do not encode the cab; the `0x2D` parameter handler is at bank 7 `0x8BCD` and its value path (via `0xB8DA`) is the next trace. |

---

## 8. Revision log — 2026-11-11

Everything this revision changed, in one place. The first seven rows have a
discriminating test each (`claims_ledger.md`, `prove_claims.py`); the rest are
new work or infrastructure.

| # | What | Where |
|---|---|---|
| 1 | **The RP500's DSP payload is a 24-byte parameter descriptor**, identical in both cabinet banks and followed by code — not an IR-sized coefficient block | §2 findings 1–3; `claims_ledger.md` C1 |
| 2 | **The `0x7FF8` compare is a stall abort, not a length cap** — measured 118 650 bytes streamed | `claims_ledger.md` C2; `05_evidence/2026-11-11_ucsim_dspstream_long.md` |
| 3 | **The GSP C48 XRAM base is `0x2445`**, not `0x2602`; C63 is `0x2603` | `claims_ledger.md` C3 |
| 4 | **Three mechanisms write `0xD070`**, not two: the descriptor stream plus a 113-byte configuration block copied into DSP registers `0xD000`–`0xD070` | `claims_ledger.md` C4 |
| 5 | **There are no factory IRs** — factory cabs are parametric models | `claims_ledger.md` C5 |
| 6 | **23 host/DSP addresses are common to all three images**, not "148 vs 151/154 registers" (that count included code pointers) | `claims_ledger.md` C6 |
| 7 | **The GSP's user IR is staged in XRAM** (`0x1483+` → `0x2603+`, count `0x14C3`) with a `0xF5` terminator | `claims_ledger.md` C7 |
| 8 | **The port is not a source swap** — it must **add** a terminated XRAM stream | §3, §4; report §13.10 |
| 9 | **The RP500 speaks the gdigi/HMG preset protocol** — 12/12 message IDs in its dispatch table (bank 7 `0x699E`); `MOVE_PRESET` (`0x39`) framing recovered | `rp500_preset_protocol.md` |
| 10 | **There is no host-side preset store** — flash is 1 MB and fully rewritten, no XRAM store; the device owns the slots | `rp500_storage.md` |
| 11 | **The RP1000 runs the same stream routine** but re-based on its own scratch cell (`0xFFAA` vs `0xFF24`) — cross-reference structurally only | §2 finding 8; report §14.1 |
| 12 | **New tooling**: the DSP stream capture (`rp500_ucsim_stream.py`), the XDATA memory map (`rp500_memmap.py`), the claims proof (`prove_claims.py`) and a second audit (`audit_claims.py`) | `04_analysis_scripts/` |
| 13 | **Version control + a version store inside the folder** | `00_master/AUDIT_GUIDE.md` |
| 14 | **Two clone defects found and fixed**: EOL conversion in a fresh clone, and `ghidra_proj/` missing from the bundle | `00_master/AUDIT_GUIDE.md` "invariant" |

Two claims were **withdrawn twice** and are recorded as such rather than
quietly corrected: the storage location ("inside the AudioDNA2" → "an external
serial store, not yet located") and the port mechanism ("source swap" →
"add a stream"). Both trails are in `rp500_storage.md` §4 and
`rp500_preset_protocol.md` §5.

---

## 9. Software audit — 2026-11-11

A second, independent pass used the shipped host tools as evidence:
`JUserCabUpdater vC59.exe`, the official RP-series updater **and its captured
flash log**, X-Edit C46/C63, and gdigi. Reproduce with
`python 04_analysis_scripts/audit_software_probe.py` — **31/31 PASS**. Full
write-up: `05_evidence/2026-11-11_software_audit.md`.

**What the cab loader really does.** RIFF/WAVE, 44.1 kHz, mono/stereo; clamps
to **128 taps** (or **208** with the option bit); each tap is **32-bit
big-endian**, not 16-bit; the record is **2048 bytes** = 2023-byte data area +
23-byte `USER n` name + 2-byte trailer. The UI has an explicit **temporary
(audition)** mode and a **store** mode; interrupting a store costs a factory
reset.

**The feature is ten table rows.** RP500 bank 7 `0x519F` has **28** IDs: 25
speaker models + `DIRECT` + `DREAD AC` + `JUMBO AC` (`607`,`606`). C63 has the
same 28 at flat `0x95CFC` **plus** the 10 user IDs (`596`–`604`, `736`).
RP500, RP1000, RP355 and C48 have **no** `USER n` names. X-Edit's
`CabType_1 = 2560` is the same parameter; user cabs are **values**.

**The transport is already on the RP500.** The captured update proves the
RP500 speaks Super7 (`F0 00 00 10 … <XOR&0x7F> F7`). `0x7A` is
`<addr32><len16><packed data>`; block 0 decodes to the first 256 bytes of
`rp500_v20.bin` exactly. The update wrote **4039** blocks into **16 × 64 KB**
segments (1 MB). The GSP cab tool uses the same `0x7A`, but against the
**separate user-data window** `0x50000`–`0x54FFF`; the RP500 updater uses it
against **firmware flash**. Same opcode, different address space/mode.

**Corrections.** (a) The two 113-byte "per-cabinet" DSP tables are
**byte-identical**, as are the two 24-byte descriptors — they do not encode
the cab. (b) The `0x2D` handler at bank 7 `0x8BCD` reads a **4-byte header**
and dispatches on a type byte; the archive's one-line wire summary is
incomplete for the device side. (c) The earlier "no factory IRs" scan used
16-bit taps; re-run at the loader's 32-bit width it still finds **0**
candidates in RP500/C48/C63/V20. (d) The "32 XRAM streams" are **2 sites ×
16 banks** (one replicated routine), not 32 models.

**Consequence for S3b.** The host half is not the blocker, and storage is not
needed for the experiment (S3a's code-space table already sends 512 B + `0xF5`).
The blocker remains the **cab trigger**; the best handle is `CabType_1 = 2560`
(value `608` for cab 24). The next safe step is **simulator-only**: boot the
existing uCsim harness with two different cab values and diff the DSP writes.
The DSP gate itself is unchanged and still unmeasured.

---

## 10. Amp → cab pairing is the trigger (2026-11-11)

The RP500 **always writes a cab when the amp changes**. The user can change
the cab afterwards, but the next amp change overwrites it; a cab cannot be
chosen before an amp. This is the `MetaParam` relationship: `AmpType_1 = 2496`
(position 8) controls `CabType_1 = 2560` (position 9) in
`RP500Preset.cs` (`controlledParams3` includes the cab).

**The decisive pair:** `GSP2101 Clean Tube` (amp 328) and `GSP2101 Sat Tube`
(329) both select **CAIO4X12** - cab index 24, cab ID **585**. Selecting one
of those amps is a deliberate, repeatable, non-boot event that **guarantees**
the cab write. That is the trigger option B needs; the full amp→cab table is
not required and is not a contiguous table in the image (see
`05_evidence/2026-11-11_amp_cab_pairs.md`).

Because the cab can be changed after the amp, the gate should key on the
**cab value 585**, not the amp value: amp change to GSP2101 Clean/Sat → 585 →
fire; a manual cab selection to CAIO4X12 → 585 → fire; any other cab → no
fire. At boot the edit-buffer table at `0xF6AA` is **zero** (measured), so a
gate reading it cannot fire at boot.

The two acoustic entries are a **locked pair**, not selectable cabs:
`Dread Acoustic` is fixed to `DREAD AC` (607) and `Jumbo Acoustic` to
`JUMBO AC` (606); those cabs are not in the 26-row selectable list and cannot
be used by any other amp. That explains the 26-vs-28 difference between the
manual/X-Edit list and the firmware table, and it does not affect the
GSP2101 Clean/Sat → CAIO4X12 trigger.

---

## 11. S3b host logic proved (2026-11-11)

The cabinet-conditional gate is now built and measured in uCsim. **PASS.**
Full write-up: `05_evidence/2026-11-11_s3b_cab_trigger.md`; reproduce with
`python 04_analysis_scripts/s3b_cab_trigger.py --runs 16000`.

| Case | At `0xD070` | First payload | Terminator | Counter | Passes |
|---|---|---|---|---|---|
| production gate (real `0xF6AA` scan), no cab value | 48 B | exact 24-byte descriptor | absent | `0x0018` | 2 |
| test gate (hard-coded IR source) | 1026 B | 512-byte table, in order | `0xF5` at 513 | `0x0200` | 2 |

The gate hooks the stock byte-send entry (`0xBE97`) and the source-base
computation (`0xBE9E`); code/data live in the bank-15 free run at `0xE095`
(gate, 140 B), `0xE800` (source block, 26 B) and `0xE200` (512-byte table).
State cells are free XRAM `0xF8E0`–`0xF8E4`.

At a stream's first byte it scans 100 3-byte cells at `0xF6AA` for
`00 02 49` (585 = CAIO4X12). Found → IR table, length 512, `0xF5`; not found →
the stock descriptor at `0x2E3B`, length 24, no terminator. At boot the table
is zero, so the production gate cannot fire.

**Still open:** (i) whether the real amp-change stream actually leaves `585`
at `0xF6AA` — the uCsim boot stream runs before any cab write, so only the
hardware can settle it; (ii) whether the DSP renders the 512-byte block — the
S3b gate proper; (iii) the first hardware IR (zeros, unit impulse, or a real
128/208-tap WAV).

---

## 12. WAV → IR table converter (2026-11-11)

`04_analysis_scripts/wav_to_ir_table.py` converts a PCM WAV to the 44.1 kHz,
128-tap (512-byte) or 208-tap (832-byte) coefficient table the S3b gate needs,
and optionally the full 2048-byte loader record. Selftest and Mesa conversion
in `05_evidence/2026-11-11_wav_to_ir_table.md`.

**Why not the provided C63 tool:** `JUserCabUpdater vC59.exe` is the only WAV
converter in the shipped software, but it is a **GUI / MIDI uploader** — it
needs a device, builds a 2048-byte device record, and sends it over SysEx. It
has no batch/encode-only mode and does not output the standalone 512-byte DSP
table. The C63 X-Edit does not convert WAVs. The script reproduces the
loader's coefficient algorithm offline; the optional `--record` matches the
loader's record layout (header at 4, coefficients at `0x10`, count at `0x0C`,
name at `0x7E7`, trailer at `0x7FE`).

**Verified:** `IR/MesaV3022.wav` (44.1 kHz, mono, 24-bit, 208 samples) → 128
taps; first coefficient `0x14690` = 5225 << 4; record coefficients at `0x10`
match the table; count 128.

**Also fixed:** `04_analysis_scripts/platform.py` shadowed Python's stdlib
`platform` module; renamed `rp500_platform_survey.py`.

---

## 13. S3b hardware candidate (2026-11-11)

Built on the **CAIO4X12** last-known-good image, not the stock image, so the
unit's cab 24 keeps its name. Adds only the production gate (scan `0xF6AA`
for `00 02 49` = 585), the source block, and a **128-tap unit impulse**.

| | |
|---|---|
| flat image | `09_builds/rp500_v20_s3b_impulse.bin` |
| container | `09_builds/rp500_v20_s3b_impulse.DigBin` |
| sha256 | `be967671a8c8bd16388c6351c3a08626db508c43f5d07323ffbfee77b4838c4f` |
| delta | **684 bytes, all bank 15** |
| impulse | tap 0 = `0x7FFFFF0`, taps 1–127 = 0 |
| updater | `09_builds/updater_2.2/...exe` (revision 2.2; embedded image verified) |

**Design:** IR on **CAIO4X12** (585); **Direct** (570) stays the dry
reference and the stock path. The impulse should make CAIO4X12 **flat/dry**
like Direct if the DSP renders the block. The static CAIO4X12 model may still
be selected; the **stock CAIO4X12** image is the baseline that separates
"ignored" from "rendered".

**Status:** built and verified in uCsim on the CAIO4X12 base. The production
scan is now exercised with positive/negative controls: **585 → 512-byte
impulse + `0xF5`**; **584 → stock 24-byte descriptor**; **no cab → stock
24-byte descriptor**. The production gate (the payload) is unchanged; the
controls use simulator-only gates that write the cab value to `0xF6AA` and
then run the same scan code. **Flash pending user action**; steps and restore
in `05_evidence/2026-11-11_s3b_checkpoint.md` §6.

**Restore:** `09_builds/updater_2.1` returns the pre-gate CAIO4X12 image
(revision 2.1 > device 2.0, default filter). `09_builds/updater_2.3_stock` is
a 2.3-labeled updater whose embedded image is the **stock** `.DigBin`
(verified SHA `01d947…`), so stock is available in the default filter without
the "show all" switch. The 2.2 updater replaced the 2.0 revision, so it cannot
restore stock 2.0 itself.

**Two more corrections from this pass.** (a) The preset descriptor pointer
table is at **XRAM `0xF912 + 2*i`**, not `0xF9F2`; the walker at `0xD8C4`
doubles the index with `ADD A,ACC` (`25 e0`), adds `#0x12`, then `ADDC #0xF9`.
`audit_claims.py` guarded this with `...count(...) >= 0`, which is always true;
it now checks the arithmetic. (b) The C59 loader's **`mono/left toggle`** is
the 128/208 switch; mono → 208 taps, otherwise 128 with the mono/left signal
duplicated. `usercab_encode.py` currently hard-codes 128 and reads the left
channel only, so the stereo path is not implemented yet.
