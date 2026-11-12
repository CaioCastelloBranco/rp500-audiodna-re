# Project state — where we are, and how to carry on

**Objective:** determine whether the DigiTech GSP1101 user-cabinet (IR) feature
can be ported to the RP500, and build as much of it as the hardware allows.

**Status as of 2026-11-11:** the build → container → updater → bootloader →
device chain is **proven end to end on hardware**, the RP500 firmware is
**mapped and executable in a simulator**, and the remaining question (can the
RP500's DSP convolve a user IR?) is now *testable* rather than speculative.

---

## 1. What is done, with the evidence

| # | Result | Evidence |
|---|---|---|
| 1 | GSP1101 user-cab **wire protocol** fully recovered (handshake, Super7, `0x7A` data, `0x73` commit, XOR/`0x7F` checksum, 10 slots × `0x800` at `0x50000`) | report §11.6–11.7 |
| 2 | **WAV → 2048-byte record** encoder, byte-exact against the C59 reference | `06_deliverable/usercab_encode.py` (self-test passes) |
| 3 | `.DigBin` container model (16 × 64 KB, address-tagged records, no checksum/signature) | `04_analysis_scripts/digbin_pack.py`, byte-exact round trip |
| 4 | **Patched firmware build** (cab 24 `DIGISPKR` → `CAIO4X12`, 8 bytes) | `09_builds/rp500_v20_caio4x12.DigBin` |
| 5 | **Updater integration**: RP500 revision **2.1** carrying that build (5 same-length edits) | `09_builds/updater_2.1/` |
| 6 | **Flashed on hardware** — dry run, then real write, 4,039 blocks, 1 NAK retried, no safety stops | `05_evidence/2026-11-10_rp500_updater_flash.log` |
| 7 | Device boots and shows `CAIO4X12`; presets and audio unchanged | user report + log |
| 8 | **Bank map**: P1 low nibble = bank number; identical `0x2C80` prefix in all 16 banks; free run `0x5FD0` at bank 1 `0xA030` | `06_deliverable/rp500_bank_map.md` |
| 9 | **Working 8051 core**: uCsim runs the stock RP500 firmware (3.65 B ticks, real bank switch to bank 15) | `04_analysis_scripts/rp500_ucsim_run.py` |
| 10 | **8051 test bench**: assemble → link → run → compare with a Python reference | `04_analysis_scripts/ucsim_check.py` |
| 11 | **Toolchain**: SDCC 4.5.0 (compiler + uCsim), Zig 0.17.1 (host compiler), 8051 RE toolkit | `00_master/TOOLCHAIN.md` |
| 12 | Updater source recovered and archived | `07_open_source_tools/netupdaterclone_src/` |
| 13 | Archive self-verification | `python verify_all.py` → **253/253** |
| 14 | **Version control**: the whole archive is a git repository (`main`, tag `baseline-2026-11-11`), stored byte-exact | `00_master/TOOLCHAIN.md` "Version control" |
| 15 | **Proof of the 2026-11-11 correction**: 7 claims, each with a discriminating test; 7/7 new hold, 0/7 old hold | `05_evidence/claims_ledger.md`, `04_analysis_scripts/prove_claims.py` |
| 16 | **Version store inside the folder**: one folder per version with a SHA-256 manifest, plus one cumulative history bundle | `99_snapshot/`, `00_master/AUDIT_GUIDE.md`, `04_analysis_scripts/cut_snapshot.py` |

## 2. Closed paths — do not redo these

| Finding | Where |
|---|---|
| The RP500 cab-select path takes an **index**, not IR data; a 2048-byte record can be transmitted but has no activation path | report §9, hardware appendix |
| No `0x7A`/`0x73` receiver in either 8051 image; no `USER_CAB` strings in the RP500 | report §2.3 |
| C48 → C63 added **no new DSP command, register or primitive** — the user cab reuses existing DSP machinery | report §12.2 |
| The GSP's user window `0x50000`–`0x54FFF` is **not** free space on the RP500 (that is the GSP layout); the RP500's free run is `0x5FD0` at bank 1 `0xA030` | bank map §5 |
| X-Edit does **not** reflect firmware cab names — it has its own table; the device menu is authoritative | report appendix B |
| The updater's all-`0xFF` skip only applies to segment 0 (banks 1-15 write their empty blocks) | report appendix B |
| The **commit flag** in `0x73 30 01 <idx> <flag>` is the **audition/store** bit (audition = play from RAM, no reboot; store = write to flash + reboot) | C63 release notes, report §13.9 |
| The user IR is **mono** (left channel only), applied to **both** outputs, written at the **head of a fixed-length block** | C54 release notes, report §13.7 |
| The RP500 has a **single AudioDNA2 DSP chip** (its two stream sites are two parameter-descriptor conversations, not two chips) | RP500 manual + hardware owner, report §13.3 |
| The RP500's firmware cab list **is** the manual's list (`DIRECT`, `DREAD AC`, `JUMBO AC` = entries 25-27) | RP500 manual, report §13.9 |
| The RP500 has **100 user presets** — a user-data area exists, so user cabs would survive a firmware update there | RP500 manual line 1929, report §13.9 |
| **The RP500 has no MOVX-visible persistent store**: the flash is 1 MB and a firmware update rewrites **all** of it (the all-`0xFF` skip applies only in segment 0 — all 548 empty blocks in segments 1–15 are written, including bank 1's `0xA030` free run); there is no XRAM store (215 written XDATA addresses, all in the DSP window / command ports / 8051 scratch) | `06_deliverable/rp500_storage.md`, `audit_claims.py` §12b |
| **The RP500 speaks the gdigi/HMG preset protocol** — its MIDI dispatch table (bank 7 `0x699E`) carries **all 12** of gdigi's preset message IDs, with handlers at `0x6Axx`; **"save preset" = `MOVE_PRESET` (0x39)**, payload `<srcBank> <srcIndex> <dstBank> <dstIndex> <name>\0 <flags>` | `06_deliverable/rp500_preset_protocol.md`, `audit_claims.py` §12c |
| The platform has **several preset back-ends** (`SYSTEM 0`, `USER 1`, `ARTIST 2`, `MEDIA_CARD 3`, `EDIT_BUFFER 4`, `FACTORY2 5`, `EXTERNAL 6`) and the firmware branches on the bank in `MOVE_PRESET` | `06_deliverable/rp500_preset_protocol.md` |
| **S2's first answer was revised**: "the presets are inside the AudioDNA2" is too strong — the XDATA map only rules out a **MOVX-visible** device, and a bit-banged serial store is invisible to it (`ERASE `/`FLERR `/`BUSY ` are such a driver's strings). The user bank's physical store is still open | `06_deliverable/rp500_preset_protocol.md` §5 |
| The **RP1000's coefficient loader is the same routine as the RP500's** (source bases `0x2DC2`/`0x2E3B`, same ports) — byte-for-byte identical except for the scratch cell the byte counter lives in (`0xFFAA/0xFFAB` vs `0xFF24/0xFF25`). A shared AudioDNA2 platform routine. | report §14.1 |
| **The RP500's DSP payload is a 24-byte parameter descriptor**, identical in both cabinet banks and immediately followed by code — *not* an IR and *not* cabinet-specific. **There are no factory cabinet IRs**: the factory cabinets are parametric DSP models (a strict 128-tap coefficient-block scan finds zero in every image), so an IR exists only in the **user-cabinet feature**, added to the GSP1101 in firmware C54. | report §13.10, `audit_claims.py` §2, README_FIRST.md (FIR-block scan) |
| **The RP500's DSP stream has no length limit** — the `0x7FF8` compare is a *stall abort* on the "status did not change" path. Measured: 118 650 bytes and still going with an always-acknowledging DSP; the first 24 are the descriptor, the rest is code. | report §13.10, `05_evidence/2026-11-11_ucsim_dspstream_long.md` |
| A **second** path writes `0xD070`: a 113-byte DSP configuration block (identical in banks 14/15) copied into DSP registers `0xD000`–`0xD070`, skipping `0xD059`. | `audit_claims.py` §1b |
| **The GSP1101 has a second, variable-length XRAM-sourced DSP path** (32 streams, `0xF5` terminator) and the user IR is staged into it (XRAM `0x1483+` → `0x2603+`). The RP-series has **none** of it. | report §13.10, `audit_claims.py` §3 |
| The GSP's XRAM path **predates** the IR feature (C48 already has 32 such streams) — the feature reused an existing path rather than inventing a DSP primitive | report §14.2 |
| A "downgrade" to an older revision is filtered out by `VersionComparer.IsNewer`; the revision must be **newer**, hence 2.1 | roadmap "Updater integration" |

## 3. The open questions (in priority order)

1. **Can the RP500's DSP render a user IR at all?** — the scientific gate.
   With no factory IRs anywhere (factory cabinets are **parametric models**),
   a user IR is a *different kind of data*, and "a DSP that only implements
   parametric cab models cannot render a user IR". The RP500's firmware only
   ever asks its DSP for a **fixed 24-byte parameter descriptor**, so the
   capability cannot be read off the image. Evidence that it exists: the
   GSP1101 — same chip family, same host interface (**23 addresses common to
   all three images**, including the whole handshake set `0xD01E/1F/20,
   0xD034, 0xD050, 0xD05A/5B, 0xD066/69/6D/6E/6F, 0xD070` and
   `0xE000/0xE200/0xE400/0xE800`) — does exactly that on 32 streams with a
   `0xF5` terminator. It has to be **measured**. (report §13.10)
2. **Where do user cabs live on the RP500?** — **PARTLY CLOSED**: not in the firmware flash (1 MB, fully rewritten) and not in XRAM (no store). The **protocol** is closed — the RP500 speaks gdigi's preset protocol, and "save preset" is `MOVE_PRESET` (0x39). The **physical store** is still open; the leading candidate is a serial (SPI/I²C) device, which the XDATA map cannot see (S2c).
3. **Can firmware read its own flash?** — moot: the flash is fully rewritten by an update and holds no user data.
4. **One IR or two?** — **settled by the manual** (C54 release notes, §IV):
   the user IR is **mono** (left channel only) and **the same IR is applied to
   both outputs**. The RP500's descriptor is cabinet-independent, so no stereo
   handling is needed on that side.
5. **The upload must be aimed at a slot** — the GSP requires the preset to be
   positioned on a user cab before Jcabinet runs. The RP500 port needs the
   equivalent (part of L4).
6. **What are the RP500's DSP register writes configuring?** — a 113-byte
   configuration block (identical in banks 14/15) is copied into DSP registers
   `0xD000`–`0xD070`, and the per-model handlers write more. A user cab must
   slot into the same mechanism.
7. **Where is the bootloader and what does it validate?** — static analysis
   (`delsum` is installed for the checksum part).
8. Which interrupt vectors are in use, and does the RP500's USB-MIDI stack run
   on the 8051 or on the DSP?

## 4. The plan (roadmap Phase 1, revised 2026-11-11)

**What we can build, concretely:** the RP500 accepts a user IR (WAV) over
USB-MIDI using the **stock Jcabinet protocol**, stores up to ten, lists them as
`USER 1..10` in the cabinet menu, and plays them through the DSP. One stub, one
table, **one new DSP stream**, one hook.

| Step | Question | Method | Gate |
|---|---|---|---|
| **S1** | What does the RP500's DSP link actually carry? | static + simulated, closed: a **24-byte parameter descriptor**, `MOVC` from `0x2DC2`/`0x2E3B`, 16-bit counter at XRAM `0xFF24`/`0xFF25`, **no length limit** (the `0x7FF8` compare is a stall abort) | **done** |
| **S2** | Where do user cabs live? | static: the device-initiated flash map, an XDATA memory map, and the platform's preset protocol | **partly closed** — not flash, not XRAM; protocol recovered; physical store still open |
| **S2b** | What is the preset protocol? | gdigi's source vs the RP500's MIDI dispatch table (bank 7 `0x699E`) | **closed** — 12/12 message IDs match; `MOVE_PRESET` (0x39) framing known |
| **S2c** | Find the physical preset store | follow bank 7 `0xABD2` → `0x0B4B` → `0xD8AD` to the `ERASE ` routine | the device and per-slot layout are known |
| **S3** | **Can the DSP take and render a variable-length block?** | the gating experiment: simulator first (patched stream routine, XRAM source, `0xF5` terminator, DSP handshake model), then a minimal hardware build that writes a 512-byte record | the DSP renders the 512 bytes — or we stop with a documented negative result |
| **S4** | Build the rest | receiver + storage + XRAM staging + the new terminated stream + UI (28 → 38 entries) | the unit shows `USER 1..10` and accepts a WAV |
| **S5** | Verify on hardware | upload with the **stock Jcabinet app**, select `USER 1`, listen, power-cycle | the IR survives a reboot |

**Immediate next action: S2c** — the physical preset store — then **S3**, the
only step that can stop the project.

**Not attempted, on purpose:** new DSP commands or register changes (the
register map is shared with the GSP), stereo user IRs (the manual says left
channel only), and a GSP-identical UI.

| Stage | What | Why | Status |
|---|---|---|---|
| **A.1** | Bank remap | without it every run dies at the first bank switch | ✅ **done** — the simulator switches banks itself via breakpoint-attached `file` commands: 3,001 switches, 0 spurious hits |
| **A.2** | DSP host-port model | the firmware polls the DSP status register `0xD06E` until it changes — with no DSP it waits forever | ✅ **done** (crude): the simulator acknowledges every `0xE000`/`0xFDFC` host command by bumping the status byte; A/B: off → hangs after 300 switches, on → keeps running (3,300 switches) |
| **A.3** | General trace capture (`PC` + DSP-port writes), then diff two images | a *tool*, not a phase — deferred on purpose; its only consumer is B/C, which has a cheaper route | ⬜ parked (machinery exists; ~1 h when needed) |
| **A.4** | Targeted experiment: call the cab-select routine directly and record its DSP writes | the one measurement the emulator is uniquely good for | ⬜ folded into **S3** (the simulator prototype does exactly this, and cheaper) |
| **S** | Static G48→C63 firmware diff | the GSP's user-cab load path, read rather than inferred | ✅ **done — and it changed the plan**: the two builds differ in 84 % of the image (a full rebuild, so no byte diff), but their DSP host-port usage is *identical*, confirming the IR feature adds no new DSP primitive. C63 adds only a cab-list surface (`USER 1..10`). See report §13 |
| **B** | Differential execution of GSP **C48 vs C63** with the same stimulus; diff the traces | the difference *is* the user-cab implementation, at instruction level | ⬜ **dropped** — unnecessary: the DSP interface is identical in both builds and the manual fixes the semantics |
| **C** | Same trace on the RP500; compare with B; measure buffer capacity | decides whether L5 (convolution) is reachable | ⬜ **dropped** — answered by report §13.10: the RP500 streams only a 24-byte parameter descriptor to its single DSP, so the user-IR path has to be **added** (a new terminated XRAM stream) rather than re-sourced |
| **D** | Build L2 (code injection + `LJMP` hook), L3 (`0x7A`/`0x73` receiver), L4 (UI 28 → 38), L5 (**new terminated XRAM stream** + staging + selector hook) | one stub, one table, one new stream, one hook | ⬜ → becomes S4 |

**Tooling built along the way (reusable):** the uCsim bench with a faithful
bank switch and a modelled DSP handshake
(`04_analysis_scripts/rp500_ucsim_banks.py`, `rp500_ucsim_dsp.py`), the
8051 test bench (`ucsim_check.py`), and the reconstruction of the updater's
source (`07_open_source_tools/netupdaterclone_src/`).

**The trick that makes S3 possible:** *binary instrumentation* — patch the
reset vector of the image under test to call an internal routine with chosen
arguments, or simply seed the data the routine will read. Ghidra supplies the
addresses and calling convention, the simulator executes, the trace records the
DSP port writes.

## 5. Ground rules agreed on

- **No destructive experiments.** The unit is the irreplaceable asset; we never
  flash an intentionally broken image to prove a recovery path. The bootloader
  claim is *reported*, not tested, and is instead analysed statically.
- **Safe-build protocol**: minimal deltas from the last known-good image, keep
  the known-good image on disk, emulator-validate code before flashing, and
  the simulator is now a real pre-flash bench.
- **X-Edit is not a witness** for firmware-side names.
- **Version upward only** (2.0 → 2.1), never downward.
- Patch in place; never rebuild the 1 MB image from source.
- `verify_all.py` must stay green — it is the archive's regression suite.

## 6. Archive map

| Folder | Contents |
|---|---|
| `00_master/` | this file, `README_FIRST.md` (index), `TOOLCHAIN.md` (environment), `CREDITS.md` (model + tool attribution) |
| `01_source_firmware/` | stock images: RP500 v1.2/v1.4/v2.0, GSP1101 v2.0/C48/C63, `.DigBin` containers |
| `02_source_binaries/` | shipped binaries: updater, X-Edit, GSP updaters, Jcabinet |
| `03_docs/` | manuals and release notes (text extracts) |
| `04_analysis_scripts/` | every script used (322 files); the important ones are listed in `README_FIRST.md` |
| `05_evidence/` | REA evidence, the flash log, the carved `updater_app.dll` |
| `06_deliverable/` | feasibility report, firmware roadmap, bank map, `usercab_encode.py` |
| `07_open_source_tools/` | gdigi, 8051 toolkit, ilspycmd, reconstructed updater source |
| `08_ghidra_banks/` | per-bank dumps imported into Ghidra |
| `09_builds/` | patched firmware + the 2.1 updater |
| `ghidra_proj/` | the Ghidra project for the 8051 images |

## 7. Where the device currently is

The unit runs **our patched RP500 v2.0** (cab 24 renamed to `CAIO4X12`),
flashed on 2026-11-10. It reports firmware version **2.0** over MIDI (we did
not change the device-side version string — only the updater's revision
label), so the updater keeps offering 2.1, which is convenient for repeated
experimental flashes.

**Restore image** if needed: `01_source_firmware/rp500V20.DigBin` (stock).
To put the stock image back into the updater:
`python 04_analysis_scripts/patch_updater.py --image 01_source_firmware/rp500V20.DigBin`.
