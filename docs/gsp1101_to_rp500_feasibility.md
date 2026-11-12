# GSP1101 IR-Cabinet Feature → RP500 Port: Feasibility Assessment

**Artifacts analyzed:** GSP1101 firmware images (`c48_fw.bin`, `c63_fw.bin`, `gsp1101_fw.bin`) and older builds (v11–vC20), RP500 firmware image (`rp500_fw.bin`), Windows updater executables (`JUpdater Gsp1101vC63.exe`, `JUpdater GSP1101vC48.exe`, `JUserCabUpdater vC59.exe`, `GSPUpdaterV20.exe`), the `.DigBin` container format, and the **GSP1101 parts list** plus the GNX 2 / GSP 2112 / GSP 2101 / RP50 service manuals (`03_docs/`).

**Tools:** REA (Ghidra 12.1.4 backend) on the Windows PE updaters and the Jcabinet encoder; Python static analysis on the raw 8051 images.

---

## 1. Verdict

**Host/firmware side: feasible, and now fully specified.**
**DSP/IR engine side: unproven — still the only gating blocker.**
**Overall: not a practical "patch-the-firmware" port today.** The feature is an extension of the same platform (same 8051 host, the same 25 speaker-model names plus special entries, GSP1101 adds exactly 10 user slots), the host-side data format is fully recovered (§11), the complete GSP wire protocol is recovered too (§11.7 — handshake, `0x7A` chunks, `0x73` commit, Super7 packing, checksum), **and the RP500's own preset protocol is recovered as well** (`rp500_preset_protocol.md`; all 12 gdigi message IDs are in its dispatch table). But the actual IR filtering runs on the DSP, and the two products use **different subsets** of a shared host/DSP interface (23 addresses in common). Without proof that the RP500 DSP accepts a 128-tap block **and convolves with it** — or DigiTech's AudioDNA2 microcode/toolchain — the port cannot produce audio from the supplied files. What remains is one narrow, testable proposition, not an open-ended unknown.

> **Corrections in the 2026-11-11 revision** (each with a discriminating test in
> `05_evidence/claims_ledger.md`): the RP500's DSP payload is a **24-byte
> parameter descriptor**, not a coefficient block (§13.10); the `0x7FF8` compare
> is a **stall abort**, not a length cap; the port is **not** a source swap;
> there are **no factory IRs**; and there is **no host-side preset store**
> (`rp500_storage.md`). Where an older sentence below still reads otherwise, the
> correction note beside it governs.

> **Status 2026-11-12 — the chip-variant half is settled.** The GSP1101's two
> DSPs and the RP500's one DSP are the **same `72-1002` AudioDNA2** part (GSP
> BOM: qty 2 "Audio DNA2 Rev B"; RP500 U25: `72-1002 GREEN`). The firmware does
> not select between the two GSP chips, and the old `0xFDFC` chip-select claim
> is corrected in §13.3. So the remaining gate is **microcode/enablement**, not
> chip identity: can the RP500's `72-1002` be put into the variable-length block
> mode and made to convolve? That is one bench measurement, not another
> disassembly. See `05_evidence/2026-11-12_gsp1101_parts_list.md` and
> `05_evidence/2026-11-12_gsp_two_chip_test.md`.

(§12 corrected two earlier draft statements: the GSP1101's **user-cab record**
is 128 × 32-bit taps, and the IR build added **no** new host→DSP command.
§13.10 further corrected the **RP500's** payload: it is a 24-byte parameter
descriptor, not a coefficient block.)

> **Correction notice (2026-11-11, second re-verification) — the port is *not* a
> source swap.** §13.4/§13.6/§13.8 are rewritten. The RP500's DSP link does
> not carry an IR-sized payload at all: it carries a **fixed 24-byte parameter
> descriptor**, **identical in both cabinet banks** and immediately followed by
> executable code. The GSP1101's user cabinets ride on a **different, separate,
> variable-length XRAM-sourced stream** that the RP500 firmware does not have.
> The port must therefore **add** that path rather than re-point an existing
> one. The gate is unchanged (does the RP500's AudioDNA2 accept a
> variable-length block?) but the work is larger than §13.8 previously claimed.
> Details: §13.10.

---

## 0. Correction notice (2026-11-09 re-verification)

A full re-check of every factual claim in this report found **one systematic addressing error** (§0.1) and **several wrong numeric claims** (§0.2 image format, §0.3 DSP command set, §9.2/§9.4 window statistics, §12.3 FIR-block counts). Everything else — the verdict, the encoder and record format, the `.DigBin` container, the DSP register-reference counts, and every RP500 address — re-verified clean.

**0.1 Bank offsets in C48/C63/V20 were systematically wrong.** An earlier pass mis-indexed the bank bodies, so many intra-bank offsets for the three GSP1101 builds are shifted. The correction depends on the build:

- **C48 / C63** — the reported bank offsets came from a stub-stripped slice of each body, so the true offset is **+8 bytes**, independent of bank (the 8 bytes are the bank-entry stub described in §0.2).
- **V20** — the reported values came from a mis-indexed flat image, so the true offset is **+8·(N+1) bytes** for bank *N* (e.g. +0x58 for bank 10, +0x80 for bank 15).

Corrected anchors:

| item | earlier draft | **correct** |
|------|---------------|-------------|
| C63 `CHAMP1X8` | bank 11 `0xD8EE` | bank 11 **`0xD8F6`** |
| C63 `USER 1` | bank 11 `0xD9D8` | bank 11 **`0xD9E0`** |
| C63 `USER %d` | bank 0 `0xBFF4` | bank 0 **`0xBFFC`** |
| C63 `CAB_EN_XLR_LPF` | bank 8 `0xE7F0` | bank 8 **`0xE7F8`** |
| C63 `USER_CAB %D` | bank 15 `0x3407` / flat `0xF3407` | bank 15 **`0x340F`** / flat **`0xF340F`** |
| C48 `CHAMP1X8` | bank 10 `0x7618` | bank 10 **`0x7620`** |
| C48 `USER_CAB %D` | bank 15 `0x3396` | bank 15 **`0x339E`** |
| V20 `USER_CAB %D` | bank 15 `0x32BA` | bank 15 **`0x333A`** |
| V20 cab block | bank 10 `0x57C8` | bank 10 **`0x5820`** |

All C63/C48 bank-15 service strings in §2.3 follow the same +8 rule. **RP500 and V20 counts/addresses that were derived from the flat 1 MB images are unaffected and were re-verified** (§2.5, §9.4, §12.5).

**0.2 The GSP1101 image is not "8-byte header + 64 KB".** The updater-embedded image is `0x100080` bytes and the layout is:

```
body0 64 KB | desc1 | body1 64 KB | desc2 | ... | desc15 | body15 64 KB | trailer 8
```

where `desc_k` (at `k·0x10000 + (k−1)·8`) is `00 kk 00 00 00 01 00 00` — the **same descriptor the `.DigBin` uses**. The 8 bytes at the start of each body are the first bytes of the shared bank-entry stub (code), not a header. The RP500 flat image is the same 16 × 64 KB bodies with the descriptors removed. So both devices use the *same* bank-body format; only the container wrapper differs. §2.1 is corrected accordingly.

**0.3 The DSP command-set tables had two errors.** (a) `0xD066` is written with **{6, 7, 0x84, 0x86, 0x87, 0x8B}** in C48/C63 but **{6, 7, 0x84, 0x85, 0x86, 0x87, 0x8B, 0x98}** in V20 — the IR build *removed* two writes; it added none. (b) The GSP1101 `0xE200` value set is **{1, 2, 4, 8, 0x10}**; the `0xC8` and `8` in the earlier table belong to `0xE400`, not `0xE200`. The conclusion in §12 is unchanged and is if anything stronger.

*(Correction 2026-11-10: the original §0.3 text gave the `0xE200` set as {0, 1, 2, 4, 8, 0x10}. Re-derivation with the `d51.py` disassembler gives {1, 2, 4, 8, 0x10} — there is no `0`.)*

**Method note (all DSP command sets).** Every `MOV DPTR,#<reg>` site is located and the following `MOV A,#imm` is read from the **disassembly**, not from a raw byte scan. A byte scan (`cmdvals.py`) yields false positives because the byte `0x74` can be an immediate operand of a preceding instruction rather than an opcode. `verify_all.py` in the project root implements the disassembly-based extraction.

---

## 2. What is confirmed (evidence)

### 2.1 Both devices are 16-bank 8051 flash images

| | GSP1101 | RP500 |
|---|---|---|
| Image size | 1,048,704 B (`0x100080`) in the updater; 1,048,576 B (16 × 64 KB bodies) as a flat image | 1,048,576 B (16 × 64 KB bodies) |
| Layout | `body0` + 15 × (`8-byte descriptor` + `body`) + `8-byte trailer`; descriptor `00 kk 00 00 00 01 00 00` at `k·0x10000 + (k−1)·8` | 16 × 64 KB bodies, descriptors stripped |
| Location | embedded in updater `.data` at file offset `0x19F8` | flat image |
| Bank-entry stub | first bytes of every body (code, not a header): **V20 (2.0)** `EA 80 68 02 2E C5 53 91`, **C48** `EA 80 68 02 30 83 53 91`, **C63** `EA 80 68 02 30 7A 53 91` | `EA 00 02 00 6B 53 91 DF` |
| Reset/entry | 8051 vector/code | `EA 00` (MOV A,R2), `00` (NOP), `02 00 6B` (LJMP 0x006B) |

Both are unquestionably 8051-family code (`02` LJMP, `12` LCALL, `75` MOV dir,#imm, `90` MOV DPTR,#imm16, `E5` MOV A,dir, `E0/F0` MOVX). The two devices use the **same 16 × 64 KB bank-body format**; a direct binary transplant is not viable because the bank *contents* are different builds with different DSP command sets (§12.5), not because the container differs.

**Address convention.** Quoted addresses are `bank k offset X`, measured in the concatenation of the 16 × 64 KB bodies. For the flat images (V20, RP500) body *k* is at file offset `k·0x10000`; for the interleaved images (C48, C63) body *k* is at `k·0x10000 + k·8` because of the interleaved 8-byte descriptors. `verify_all.py` in the project root checks every address quoted in this report in exactly this convention.

### 2.2 The cabinet model set is shared; only the 10 user slots differ

GSP1101 (C63) cab-name block (`bank 11`, `0xD8D2`–`0xDA26`, flat `0xBD8D2`) contains the **same 25 fixed 8-character speaker names as the RP500**. The block begins with the special entries `DREAD ACOUSTIC` (`0xD8D2`), `JMBO ACOUSTIC` (`0xD8E1`), `DIRECT` (`0xD8EF`), then the 25 speaker names starting at `CHAMP1X8` (`0xD8F6`):

`CHAMP1X8, DLUX1X12, DXRV1X12, BRIT1X12, GBSN1X12, BMAN2X12, TWIN2X12, BRIT2X12, JAZZ2X12, BMAN4X10, CLAS4X12, GREN4X12, FANE4X12, BOTQ4X12, VNTG4X12, RECT4X12, SOLO4X12, BRGT2X12, METL4X12, ROCK4X12, ALTR4X12, DVTG4X12, CHNK4X12, SPNK4X12, DIGISPKR`

then a second `DIRECT  ` entry (`0xD9D7`, 9-byte record), then **`USER 1`…`USER 10`** (`0xD9E0`–`0xDA26`).

**USER record format — important for a port.** The 25 speaker names are 9-byte fixed records (8 chars + NUL), but the **USER entries are variable-length, NUL-terminated**, exactly like the older V20 style:

| Entry | Offset | Bytes |
|-------|--------|-------|
| `USER 1` | `0xD9E0` | `55 53 45 52 20 31 00` (7) |
| `USER 2` | `0xD9E7` | 7 |
| … | +7 each | 7 |
| `USER 9` | `0xDA18` | 7 |
| `USER 10` | `0xDA1F` | `55 53 45 52 20 31 30 00` (8) |

The USER table therefore spans `0xD9E0`–`0xDA26` (the NUL of `USER 10` is at `0xDA26`), followed immediately by unrelated strings (`%s`, `%59s`, `GLOBAL CABINET`). A port must append **variable-length** user entries, not 9-byte fixed ones — the RP500's own cab pointer table at `bank 4:0x478E` points at 9-byte records, so the USER entries would need either 9-byte padding or a second table with its own stride.

The strings immediately before `CHAMP1X8` (`DIGI MOSH`, `DREAD ACOUSTIC`, `JMBO ACOUSTIC`, `DIRECT`) are the shared acoustic/direct entries plus the tail of the amp list: `DIGI MOSH` is an amp model (release notes), while `DREAD`/`JMBO`/`DIRECT` correspond to the special cab entries (`DREAD AC`/`JUMBO AC`/`DIRECT` in the RP500's 28-entry table). The two lists are physically contiguous, so the exact split is not meaningful. What is certain is the 25 fixed 8-char speaker names plus the 10 user slots.

RP500 cab list (`bank 4` offset `0x3486`, flat `0x43486`) is a **28-entry** name/pointer table: the 25 speaker models `CHAMP1X8 … DIGISPKR`, then `DIRECT`, `DREAD AC`, `JUMBO AC` (pointer table at `bank 4:0x478E`, big-endian 16-bit pointers, 9-byte fixed strings). It has **no USER slots**. The C48 (pre-IR) block has the identical 28-entry layout, with `DIRECT  ` at bank 10 `0x7701`, `DREAD AC` at `0x770A`, `JUMBO AC` at `0x7713`.

Correction to an earlier draft: the RP500's 28-entry pointer table (decoded in §9.3) selects exactly the same 25 speaker names as C63, then `DIRECT`, `DREAD AC`, `JUMBO AC`. The GSP1101 has the same 25 speaker names plus the special entries and the 10 user slots. `DIGI MOSH` is an amp model, not a cab. This does not change the conclusion — it strengthens the point that the RP500 cab list is a UI name table with no per-model payload, and that its name records are already in C63's 9-byte format.

This is still the strongest architectural finding: the GSP1101's cab feature is the same cab engine extended with user-cab entries.

The editorial (.NET) side confirms the same story. Diffing `Hmg.Devices.dll` between X-Edit GSP1101 Beta **vC46** (pre-IR) and **vC63** (post-IR) shows the class set is unchanged — same 14 methods in `GSP1101Device`/`GSP1101Preset` — and the only differences are **data tables**:

- 10 new cab-table rows: index 26 → ID `596` "User Cab 1", 27 → `597`, … 34 → `604` "User Cab 9", 35 → `736` "User Cab 10";
- one new parameter, ID `2510`, "Cab Enable LPF to XLR";
- one new field, `MidiOutPresetMapCount`.

Indices 0–25 map to the factory cab IDs `571`–`585` / `608`–`626`, with index 25 → `570` "Direct". So the user-cab feature is literally "ten more table rows" on the editor side; no new protocol class, no new transport, no new encoder in the editor. This is consistent with §12: the device firmware likewise gained strings and tables, not a new DSP primitive.

### 2.3 GSP1101 has a user-cab transfer/store path; RP500 has none

GSP1101 `bank 15` is the service/update/bulk-dump bank. It contains:

- `SEND BLOCK` (`0x3387`), `SEND PRESET` (`0x3392`), `SEND AMP` (`0x339E`)
- `BULK DUMP` (`0x33AF`), `Receiving a Bulk Dump` (`0x33B9`), `from X-Edit` (`0x33CF`)
- `BLOCK: %D` (`0x33DB`), `PROGRAM: %D` (`0x33E5`), `GLOBAL: %D` (`0x33F1`)
- `USER AMP %D` (`0x3403`), **`USER_CAB %D` (`0x340F`)**
- `FLASH ERASE ERROR` (`0x345E`), `FLASH WRITE ERROR` (`0x3470`), `FLASH INIT SECTOR ERROR` (`0x34B2`)
- `PRE DSP` (`0x357E`), `POST DSP` (`0x3586`), `PRE SAMPLE` (`0x358F`), `FLASH_DATA: %D` (`0x359A`)

The same `USER_CAB %D` message already exists in the pre-IR firmware 2.0 (V20 bank 15 `0x333A`), so the message name predates user cabs and does not by itself prove a working user-cab path in V20.

The RP500 has no `USER`, `USER_CAB`, `CABINET`, or `GLOBAL CABINET` strings. Its `bank 15` service page instead has `RP 500`, `UPDATE`, `UPLOAD`, `PRESET`, `GL PARAM`, `BULKERR1`, `FLASH`, `RESTORE` — a preset/global bulk-dump path, but no user-cab command.

### 2.4 The editor side is GSP1101-only and does not contain the IR loader

`JUpdater Gsp1101vC63.exe` is GSP1101-specific (no RP500 device strings). It contains the user-cab UI class `UserCabGainPage` (RTTI VA `0x5C3034`) and its constructor `FUN_00407b40`, which references:

- `Cabinet Gain` (`0x4A7698`), `cabGain`
- `Cabinet Index 1 to 10` (`0x4A76C8`), `cabPos`
- `Store cabinet to GSP1101 else it will be a temporary cabinet` (`0x4A7790`)
- `Warning! If the storing of the cabinet is interrupted then you will have to perform a factory reset and all your user presets will be lost.` (`0x4A7810`)
- `mono/left toggle button` (`0x4A7944`), `mono/left vC56` (`0x4A7974`)
- `Store temporary cabinet (vC59)` (`0x4A7994`)

The constructor is pure JUCE UI construction (sliders/labels/layout); it does **not** contain the IR file decoder. No `.wav`/`.aif` strings and no WAV/AIFF format classes (`WavAudioFormat`, `AiffAudioFormat`, `AudioFormatManager`) exist in this binary. The C63 release notes name the IR-import tool **Jcabinet**, not X-Edit; the supplied updater has the `UserCabGainPage` (gain/position/store) and the HMG SysEx transport (`Super7TxSysexMsg`/`Super7RxSysexMsg`) but not the WAV→128-sample conversion. So the GSP-side reference implementation is still incomplete.

The warning confirms the user cab is stored in the device's user-data flash area (the same area as user presets), not in the firmware image.

### 2.5 Flash headroom favours the RP500

`0xFF` free-space census (runs ≥ 256 B), per build:

| Build | Total free | Largest contiguous |
|---|---|---|
| GSP1101 V20 | `0x2889A` = 166,042 B | `0x8431` = 33,841 B |
| GSP1101 C48 | `0x7135` = 28,981 B | `0x155F` = 5,471 B |
| GSP1101 C63 (IR build) | `0x4E19` = 19,993 B (~19.5 KB) | `0x14FB` = 5,371 B (bank 14) |
| **RP500** | **`0x277BA` = 161,722 B (~158 KB)** | **`0x5FD0` = 24,528 B (banks 1/2)** |

The RP500 has ~8× more free flash than the C63 IR build. Note that the C63 IR build has *less* free flash than the pre-IR V20 build — the user-cab feature consumed some of it.

> **Free bytes are not free storage** (corrected 2026-11-11). The updater's
> all-`0xFF` skip applies **only inside segment 0**; every empty block in
> segments 1–15 is rewritten on each update, including this `0x5FD0` run. The
> census above measures room for **code that ships with the firmware**, not for
> user data (`rp500_storage.md` §1). Whether any slot storage exists host-side
> is answered there: it does not.

### 2.6 Shared code is limited

The two images share some 8051 routines and the cab vocabulary, but they are different builds with different bank maps. Same-offset byte similarity is low (RP500 ↔ C63: 9.2 % overall, 4.7–14.3 % per bank). This is not a diff-and-patch relationship.

---

## 3. Gap analysis: what a port would actually require

### Host side (solvable, and now specified)

> **Status 2026-11-11.** Items 3, 4 and 6 below were rewritten after the
> storage and protocol work: the RP500 has **no free flash sector** to store
> records in, and its service code is a **numeric-ID dispatcher in bank 7**, not
> the GSP's text-named flow in bank 15. See `rp500_storage.md` and
> `rp500_preset_protocol.md`.

1. **Cab table**: extend the RP500 cab table (bank 4, `0x43486`) by 10 entries (indices 30–39) and add display names.
2. **Preset/global data**: add a user-cab index field and validation (0–9) to the preset/global structures.
3. **Transport**: use the RP500's **own** preset protocol — `RECEIVE_PRESET_PARAMETERS` (`0x2D`) to fill the edit buffer, `MOVE_PRESET` (`0x39`) to commit a slot. It is already implemented in the firmware (dispatch table at bank 7 `0x699E`, all 12 gdigi IDs present) and **gdigi is a working client**. No new message class and no Super7/checksum layer.
4. **Storage**: **not a host-side task.** The RP500's flash is 1 MB and a firmware update rewrites all of it; there is no XRAM store. Slots are kept by the **device** (the physical medium is still being pinned — `rp500_storage.md` §4, S2c). The host must not add a flash-write primitive for records.
5. **Device UI**: add menu text/selection for the new slots.
6. **Editor**: reuse **gdigi** (`07_open_source_tools/gdigi/`) rather than building one — it already speaks the protocol. The supplied updater remains GSP1101-only for the GSP path; for the RP500 the updater is only needed to ship firmware.

### DSP side (the gating blocker)

The 8051 cannot perform 44.1 kHz IR convolution. The convolution must run on the RP500's DSP (DigiTech AudioDNA-family DSP, based on the GSP's `DNA= %d` diagnostic). To port the feature you would need one of:

- **A confirmed convolution/coefficient-load mode in the RP500 DSP** (then the host work above is the main effort), or
- **DigiTech's DSP microcode/toolchain** to add such a mode (not present in any supplied artifact), or
- **A hardware/datasheet description** proving the DSP's coefficient RAM and cycle budget can host the IR length used by the GSP1101.

The supplied firmware images do **not** contain an obvious DSP microcode blob or IR coefficient tables; the 1 MB flash is dominated by 8051 code, strings and UI/preset data. The GSP's user-cab data lives in the device's user-data flash (per the factory-reset warning), so its size cannot be inferred from the firmware image.

### Protocol / documentation

The GSP1101 side is fully recovered: the IR file format, the 2048-byte record
(§11) and the complete wire protocol — handshake, `0x7A` chunks, `0x73`
commit, Super7 packing and checksum (§11.7). The device-side service strings
(`SEND BLOCK`, `USER_CAB %D`) are in §2.3.

> **Correction (2026-11-11).** An earlier draft said "the RP500 editor and its
> SysEx protocol are not in the supplied set … the RP500's own SysEx/command
> vocabulary [is] still missing". **That is wrong — it was in the archive all
> along.** `07_open_source_tools/gdigi/` is the open-source RP500 host tool, and
> its message IDs match the RP500 firmware's MIDI dispatch table (bank 7
> `0x699E`) **12 of 12**. The vocabulary is recovered in
> `rp500_preset_protocol.md`: preset save is `MOVE_PRESET` (`0x39`), parameter
> push is `RECEIVE_PRESET_PARAMETERS` (`0x2D`), dump is `REQUEST_BULK_DUMP`
> (`0x18`). The port therefore uses the **RP500's own protocol**, not the GSP's
> Jcabinet framing — no Super7, no XOR checksum, no new message class.

---

## 4. Feasibility rating

| Work item | Feasibility with supplied artifacts | Notes |
|-----------|-----------------------------------|-------|
| Locate/extend cab table | High | Same 25 speaker-model vocabulary; RP500 table is easy to extend |
| Add user-cab command | **High** | the RP500's own protocol is recovered (`MOVE_PRESET` 0x39, `0x2D`); all 12 gdigi message IDs are in its dispatch table — see `rp500_preset_protocol.md` |
| Storage for 10 slots | **Not host-side** | no free flash (1 MB, fully rewritten) and no XRAM store; the device keeps the slots. Medium risk until the medium is pinned (S2c) |
| Device UI/menu | Medium | 8051 display code, but doable |
| RP500 editor + IR converter | **Solved** | format fully recovered from `JUserCabUpdater vC59.exe` (§11); **gdigi already speaks the protocol**, so no editor needs writing |
| DSP convolution/IR engine | **Low / unverified** | the gate: G1 (accepts a length-bounded block?) and G2 (convolves with it?). No DSP microcode/toolchain |
| **Overall** | **Low without vendor DSP info** | host-only work would produce storage/UI but no audio |

---

## 5. Recommended proof-of-concept (before any port work)

1. ~~**Capture the GSP1101 protocol.**~~ **Done** — transport and framing are fully recovered statically (§11.6–11.7): handshake `0x01`, chunked `0x7A` data writes of `0x100` bytes, one `0x73` commit, Super7 7-bit packing and the XOR/`0x7F` checksum. No capture is needed for the payload or the framing.
2. ~~**Determine the IR length/format.**~~ **Done** — 128 taps, signed 32-bit big-endian, 28-bit full scale, 44.1 kHz source only (§11).
3. **Probe the RP500 DSP path.** This is now the only decisive test, and it needs the physical unit:
   - First, with an unmodified RP500, send a standard cab-select command for index 29+ (or an invalid `CAB_TYPE`) and listen for any DSP response/error. **Done (Appendix B):** indices 570–626 are accepted, ≥627 is rejected, and each accepted change carries only the 2-byte value — so the index path exists but never transfers a block. This is suggestive, not decisive.
   - Second, if the first test is inconclusive, **add** — do not re-point — a length-bounded, `0xF5`-terminated XRAM stream and send a known short IR through it. *(Corrected 2026-11-11: the earlier plan said "patch the host to write the record to a free sector and switch to it through the existing bank-15 `0xBE97` stream". Both halves of that were wrong — there is no free sector (`rp500_storage.md`), and the existing stream carries a 24-byte descriptor, not IR data (`§13.10`).)*
   - If the DSP ignores the block or produces no audio, the feature is DSP-gated and stops there.
4. **Minimal host patch.** Add one user slot to the RP500 cab table (28 entries at bank 4 `0x3486`), and drive the new stream with a known short IR using the RP500's own preset protocol (`MOVE_PRESET` 0x39). *(The earlier "`USER_CAB` handler + free flash sector `0x5FD0`" plan is withdrawn: the store is the device's, and `0x5FD0` is overwritten on every firmware update.)*
5. **Measure.** If the RP500 DSP produces the convolved output, proceed; if not, stop — the remaining work requires DSP firmware/toolchain that is not available.

---

## 6. Bottom line

The GSP1101 user-IR feature is **architecturally adjacent** to the RP500: same 8051 host family, a shared set of speaker-cab models, and the GSP1101 adds user slots plus a bulk-dump/flash-store path. The host-side data format is fully recovered (§11: a 2048-byte record carrying 128 × 32-bit taps) and so is the transport (§11.7: handshake, `0x7A` chunked writes, `0x73` commit, Super7 packing), and the C48-vs-C63 comparison (§12) shows the IR build added **no new host→DSP command** — so the payload travels over a channel that already exists.

However, the feature's audio core is DSP coefficient convolution. No firmware image contains 128-tap tables for the factory cabs, so the factory cabs are parametric DSP models; a user cab is a different kind of data. The RP500 has a block channel to its DSP but a **different command set** from the GSP1101, and nothing in the supplied artifacts proves its DSP accepts a raw coefficient block. **Without that proof — or DigiTech's AudioDNA2 microcode/toolchain — the port is not feasible as a firmware-only project.** Deployment is no longer the blocker (§10), and the file format is no longer the blocker (§11), so the next decisive step is a DSP capability test, not more 8051 analysis.

---

## 7. Addendum: replacing an existing cabinet model instead of adding slots

**Question:** instead of adding 10 user-cab slots (new UI, new SysEx command, new flash storage), could one overwrite an existing factory cabinet model with a custom IR?

**Short answer:** It reduces the host-side scope but does **not** clear the DSP blocker. The RP500's factory cab entries are name strings plus a DSP-side model selected by an index — they are not per-cab IR/coefficient files sitting in the firmware. Replacing one therefore still requires either (a) DSP microcode changes, or (b) proof that the RP500 DSP accepts downloadable coefficient/IR blocks and a way to feed them. Without one of those, replacing a model changes nothing audible.

### 7.1 Evidence that the factory models are not replaceable data blobs

- The RP500 cab "table" is a **UI name list**: 25 fixed 9-byte strings at `bank 4:0x3486`–`0x3566` (`CHAMP1X8 … DIGISPKR`), plus `DIRECT`, `DREAD AC`, `JUMBO AC`, addressed by a big-endian 16-bit pointer table at `bank 4:0x478E`. The list is immediately followed by unrelated display format strings (`BASS %2D`, `MID %2D`, `TREBLE %2D`, …), so there is no model payload after it.
- No 25/28/30-entry coefficient, offset, or IR-length table exists in the image. Scans for monotonic 30-entry offset tables and for audio-like blocks only found smooth parameter-scaling/preset tables (e.g. `bank 9:0xB800` is a linearisation curve, `bank 9:0xA900` is a fixed-point ramp table), not impulse responses.
- No `WAV`, `AIFF`, `IR`, `IMPULSE`, `CONVOL` strings exist in the RP500 image; `CAB_TYPE` is a parameter name only.
- The GSP1101, which does support user cabs, carries the extra machinery: `USER_CAB %D`, `SEND BLOCK`, `BULK DUMP`, `FLASH_DATA: %D`, plus DSP-SDRAM diagnostics `SDram Addr= %08lx h Cmd= %d DNA= %d`, `Load Count= %d`, `SD= …`. The RP500 has none of these.
- Both firmwares expose the same style of DSP command/data window (`XDATA 0xD070`, `XDATA 0xE000`, `0xFF24/0xFF25` counters), so the RP500 host *can* talk to a DSP. *(Corrected 2026-11-11: the RP500 does more than single-byte writes — it copies a **113-byte configuration block** into DSP registers `0xD000`–`0xD070` and streams a **24-byte descriptor**. Neither is cab-sized, and neither is IR data; see §13.10.)*

### 7.2 When replacement does help

> **Resolved 2026-11-11.** The bus question this section rests on has been
> answered statically and in the simulator: the RP500 does **not** upload a
> coefficient block when the cabinet type changes. It streams a 24-byte
> descriptor and copies a 113-byte configuration block (§13.10). So the
> "replace a factory model" route does **not** become a host-fed path — it
> faces the same DSP gate as adding slots.

If a bus capture *had* shown the RP500 uploading a **coefficient block** when the cabinet type changes (rather than a one-byte index), the DSP would be host-fed and one could substitute a block for a single model. In that case the "replace" route would save:

- extending the cab table / adding menu entries,
- adding a `USER_CAB` SysEx command,
- allocating and protecting user-flash sectors,
- editor-side slot management.

It does **not** save:

- recovering the DSP's coefficient/IR data format,
- implementing IR→format conversion,
- the modified-image flashing path (no RP500 updater/editor was supplied),
- the destructiveness of changing a model used by every preset.

### 7.3 The cheapest decisive test

1. Put the RP500 in service/test mode and change cabinet type while capturing the 8051↔DSP bus (or the write stream to `0xD070`/`0xE000`).
2. **One index byte changes** → the 28 models are DSP-resident. Replacing one is DSP microcode work; stop unless vendor DSP tools appear.
3. **A block (hundreds/thousands of bytes) is written** → the models are host-fed. Diff the blocks for two cabs, then try substituting a synthetic coefficient set for one index.
4. Capture a GSP1101 user-cab store (USB-MIDI + DSP side if accessible) and compare its load command with the RP500 cab-select traffic. If the RP500 never emits the GSP "load block" command, the convolution path is absent.
5. Only if steps 2–4 show a usable block path: patch one RP500 cab index to point at a custom block and measure the audio. Treat the firmware as experimental — keep a stock image for recovery.

### 7.4 Verdict on the replacement variant

| Aspect | Adding 10 slots | Replacing one factory model |
|--------|-----------------|----------------------------|
| Cab name/UI work | Required | Optional (cosmetic only) |
| SysEx/bulk-dump command | Required | Not required if an existing index is reused |
| User-flash storage | Required | Not required |
| IR format / conversion | Required | **Still required** |
| DSP convolution/coefficient path | **Gating unknown** | **Gating unknown** |
| Reversible | Yes | No (firmware image changes; all presets affected) |
| Overall | Low feasibility | Marginally less host work, same DSP risk |

**Bottom line:** replacing a factory model is a sensible way to shrink a proof-of-concept, not a way around the core problem. The RP500's cabs are DSP-selected models, not swap-in files, so the decisive question remains the same: can the RP500 DSP load and run arbitrary cab/IR data? Until that is demonstrated, neither adding slots nor replacing a model produces a working custom IR.

---

## 8. RP500 XLR output: disabling the cabinet and tapping before the output (firmware-only)

Scope: RP500 image only (`rp500_fw.bin`, 16 × 64 KB 8051 banks).

### 8.1 The XLR is not modelled in firmware at all

- No `XLR`, `BALANCED`, `BAL`, `CABINET`, `CABSIM`, `CAB SIM` strings exist in the 1 MB image, in **ASCII or UTF‑16LE/BE** (the image does use UTF‑16 for the USB descriptors, so both encodings were checked).
- The only output-routing globals the firmware exposes are `MONO` / `STEREO` (`bank 4:0x3063`, `0x306A`) and `1/4 AMP` / `1/4 MIX` (`bank 4:0x3071`, `0x3079`).
- The literal label `1/4 …` shows the firmware only ever configures the 1/4" jacks. There is no XLR/balanced parameter, menu entry, or output-mode value. **Whatever drives the XLR is fixed in hardware to the processed (post-cab) mix.**

### 8.2 There is no cab on/off bit — only `CAB_TYPE`

The 86-entry preset parameter name table is at `bank 6:0xC563`, stride `0x12` (18 bytes). Blocks with an on/off flag:

`WAH_ONBY, COMP_ONBY, STOMP_ONBY, AMP_ONBY, EQ_ONBY, GATE_ONBY, EFF_ONBY, DEL_ONBY, REV_ONBY`

The cabinet block has **only `CAB_TYPE`** — there is no `CAB_ONBY`. So the cabinet cannot be switched off independently; it is removed by selecting the "no cabinet" model.

The cab selector is a 28-entry big-endian pointer list at `bank 4:0x478E`:

| index | entry |
|-------|-------|
| 0–24 | `CHAMP1X8 … DIGISPKR` (25 speaker models) |
| **25** | **`DIRECT` (no cabinet)** |
| 26 | `DREAD AC` |
| 27 | `JUMBO AC` |

### 8.3 Practical recipes

| Goal | Setting |
|------|---------|
| Dry (cab-less) signal on the **XLR** to feed an external IR | preset **`CAB_TYPE = DIRECT`** (index 25) |
| Dry **pre-cab** signal on the 1/4" jacks while the XLR keeps the cabbed mix | output mode = **`1/4 AMP`** |
| Dry on every output | `CAB_TYPE = DIRECT`, or `AMP_ONBY = 0`, or preset `BYPASS` |

Caveats:

- `CAB_TYPE` is a **per-preset** value applied to the whole processed path. Setting it to `DIRECT` makes **both** the XLR and the `1/4 MIX` output dry; you cannot keep a cab on the 1/4" outs while the XLR is dry.
- `1/4 AMP` is the intended **pre-cab tap** (send to a real amp / external cab sim) while the XLR carries the cabbed mix to FOH. This is the firmware-supported "intercept before the cabinet" route.
- `1/4 MIX` is the post-cab mix.

### 8.4 What is *not* possible from firmware

- **No pre-cab signal is routed to the XLR.** To get one there you must make the whole preset dry (`CAB_TYPE = DIRECT`).
- **No digital intercept / insertion point is exposed.** Cabinet filtering runs in the audio DSP; the 8051 only selects a model. A true pre-cab digital tap or an insert ahead of the XLR driver is a board-/DSP-level modification.
- Firmware cannot rule out a **fixed analog pad/filter on the XLR board**. If the perceived "always-on compensator" survives `CAB_TYPE = DIRECT`, it is analog and needs board tracing.

### 8.5 Correction to §7.1: a bulk flash→peripheral transfer *does* exist

Earlier drafts said the RP500 host "only performs single-byte parameter writes" to the DSP window. That is too strong. There is a bulk transfer handler:

- `bank 14:0x99F0` and its duplicate `bank 15:0xBDE7` stream bytes from flash to the DSP window.
- Source address = `0x2DC2 + n` (bank 14) or `0x2E3B + n` (bank 15), read with `MOVC A,@A+DPTR`.
- Each byte is written to `XDATA 0xD070`, gated by status bits 2/3 of `XDATA 0xD06E`; the byte counter is the 16-bit pair `XDATA 0xFF24/0xFF25`; `0xC0`/`0xC1` commands go to `XDATA 0xE000`, and a setup helper at `bank 14:0xA132` writes `0xD020/0xD05B/0xD06D/0xD06F`.
- **There is no length limit in the host code.** The `0x7FF8` compare sits on the *"the DSP status did not change"* path, so it is a **stall abort**, not a byte cap. Measured: with a DSP model that always acknowledges, the firmware pushed **118 650 bytes** and was still going (`05_evidence/2026-11-11_ucsim_dspstream_long.md`).

Why this does **not** change the XLR/cab conclusion:

- The payload is a **24-byte block**, **identical in both cabinet banks**, and it is **immediately followed by executable code** (`bank 14 0x2DDA`, `bank 15 0x2E53` — the head of the next function). It is therefore a cabinet-independent **DSP parameter descriptor**, not a cabinet/IR table.
- A **second** path also writes `0xD070`: a **113-byte DSP configuration block** (bank 14 at `0x2C80`, bank 15 at `0x2CBB` — byte-for-byte identical) copied one byte at a time into DSP registers `0xD000`–`0xD070`, skipping `0xD059`. Its last byte lands on `0xD070`.
- Nothing links a **cabinet selection** to a block transfer; changing `CAB_TYPE` is a parameter write, not a per-cab block load.
- Whether the block is DSP program, a RAM shadow, or peripheral firmware cannot be decided from the static image alone.

### 8.6 Verdict (RP500 XLR)

- **Can the XLR cabinet compensator be disabled?** Not with a dedicated switch — none exists. It is removed indirectly by setting the preset `CAB_TYPE = DIRECT` (index 25), which affects all outputs.
- **Can the signal be intercepted before the output to feed an external IR?** Yes: use `1/4 AMP` (pre-cab tap) or a dry XLR via `CAB_TYPE = DIRECT`. A digital pre-cab tap on the XLR is not available in firmware.
- **Is there an XLR-only "always-on" compensator in firmware?** No. If one exists independent of `CAB_TYPE`, it is analog and must be traced on the board.

---

## 9. V20 → C63 delta: what the user-IR feature actually changed

### 9.1 V20 is the pre-IR firmware 2.0 build

`GSPUpdaterV20.exe` is a 2006 "GSP Update Utility" 1.01 (PE VERSIONINFO, "Copyright (C) 2006"); its UI contains the string **"To update to version 2.0"**. Its firmware is a single 1,048,576-byte `BINFILE` resource at exe offset `0x51E18`, laid out as 16 × 64 KB bank bodies; each body begins with the bank-entry stub `EA 80 68 02 2E C5 53 91`. Extracted to `v20_res_51E18.bin`.

V20 **already** contains:

- the 8051 host code and the same DSP command/data window (`XDATA 0xD070`, `0xE000`, `0xD06E`);
- the service/bulk-dump message table: `SEND BLOCK`, `BULK DUMP`, `BLOCK: %D`, `USER AMP %D`, and **`USER_CAB %D`** (`bank 15`, `0x333A`);
- the XLR/global-cabinet menu strings (`GLOBAL CABINET`, `XLR OUT CABINET MODEL USAGE`, `APPLY GSP CABINET MODELS…THROUGH THE 1/4 LINE OUTPUTS?`).

V20 **does not** contain:

- any `USER 1…10` cab type (its cab-name block at `bank 10` `0x5820` / `0x5844` uses the older long-name vocabulary with 21 speaker models and stops at `JUMBO ACOUSTIC`);
- the `USER %d` display string (C63 `bank 0` `0xBFFC`);
- the `CAB_EN_XLR_LPF` parameter (C63 `bank 8` `0xE7F8`; the same V20 offset is erased `0xFF`).

So "pre-IR" means **no user slots and no cab-LPF parameter**, not "no bulk-dump service code": the `USER_CAB` message name predates the feature; whether V20's handler is live or a stub cannot be decided from strings alone.

### 9.2 C63 is a broad 2.0 feature build, not an IR-only patch

`gsp1101_fw.bin` is exactly the firmware embedded in `JUpdater Gsp1101vC63.exe` at `0xC0FF8` (image `0x100080`; 16 × 64 KB bodies with interleaved 8-byte descriptors; stub `EA 80 68 02 30 7A 53 91`).

- Byte identity V20 ↔ C63: **10.4%** overall (per bank 5.3–18.9%).
- Shared 32-byte windows, 32-byte **aligned** windows over the 16 × 64 KB body view: **19.4% raw** (6358/32768) but only **4.3% informative** (1182/27592) once all-`0xFF` windows are excluded. The raw figure is dominated by erased flash.
- C48 ↔ C63 for comparison: **15.6%** bytes, 8.8% raw window overlap, **6.2% informative** (1967/31847).
- RP500 ↔ C63 for comparison: **9.2%** bytes, 19.2% raw window overlap, 4.6% informative (1264/27737).

*(Statistics re-derived 2026-11-10 with `rederive`-style code now in `verify_all.py`; the earlier draft quoted window figures that could not be reproduced from the archived artifacts and have been replaced with measured values and an explicit method.)*

- C63 adds new amp models, stompboxes, speaker cabs (GIBSON 1X12, JAZZ 2X12, RECTIFIED 4X12), routing/MIDI changes and user cabs (release notes §II–IV).

There is therefore no small IR-only diff to back-port; C63 is the reference implementation and is a whole-image feature release.

### 9.3 The user-cab delta is small on the host

V20 (pre-IR) vs C63, and C63 vs the RP500:

| Item | V20 | C63 | RP500 |
|------|-----|-----|-------|
| Speaker-cab vocabulary | 21 long variable-length names + 3 specials | **25 fixed 8-char names** + 3 specials | **same 25 fixed 8-char names** + 3 specials |
| Cab-name record | variable-length, NUL-terminated | 9 bytes (8 chars + NUL) | 9 bytes (8 chars + NUL) |
| Cab block location | bank 10 `0x5820` (specials) / `0x5844` (`CHAMP 1X8`) | bank 11 `0xD8D2` / `0xD8F6` (`CHAMP1X8`) | bank 4 `0x3486` (`CHAMP1X8`) |
| Cab indexing | string block | fixed 8-char names in a 9-byte block (no pointer table found) | 28 × BE 16-bit pointer table at bank 4 `0x478E` |
| Special entries | `DREAD ACOUSTIC`, `JMBO ACOUSTIC`, `DIRECT` | `DREAD ACOUSTIC`, `JMBO ACOUSTIC`, `DIRECT` | `DIRECT`, `DREAD AC`, `JUMBO AC` |
| User slots | **none** | **`USER 1…10`** (bank 11 `0xD9E0`) | **none** |
| User display string | none | `USER %d` (bank 0 `0xBFFC`) | none |
| XLR/cab LPF parameter | none (erased) | `CAB_EN_XLR_LPF` (bank 8 `0xE7F8`) | none |
| `USER_CAB %D` service message | **present** (bank 15 `0x333A`) | present (bank 15 `0x340F`) | none |

The RP500's cab pointer table at `bank 4:0x478E` decodes to exactly the C63 25 speaker names in the same order, then `DIRECT`, `DREAD AC`, `JUMBO AC` (28 entries). In other words, **the RP500 already shares C63's 25-name vocabulary and 9-byte record format**; it indexes them with an explicit pointer table. Adding `USER 1…10` is a table extension of the same shape as C63's, not a port from a different design.

### 9.4 The DSP interface did not change between V20 and C63

References to the DSP window in banks 14/15 are structurally identical in both builds (addresses shifted by recompilation):

| Reference | V20 | C63 |
|-----------|-----|-----|
| `MOV DPTR,#0xD070` | 10 (b14), 10 (b15) | 10 (b14), 10 (b15) |
| `MOV DPTR,#0xE000` | 13 (b14), 26 (b15) | 13 (b14), 26 (b15) |
| `MOV DPTR,#0xD06E` | 2 (b14), 2 (b15) | 2 (b14), 2 (b15) |
| `0xD020/0xD05B/0xD06D/0xD06F` helpers | same counts | same counts |

Bank 14 shares only **52.8 %** of its raw 32-byte aligned windows with C63, but only **1.5 %** (15/981) once all-`0xFF` windows are excluded. This is evidence that C63 did **not** add a new host↔DSP primitive for user cabs — the driver is the same *design* with recompiled/shifted addresses, not byte-identical code — but it also means the reference implementation cannot tell us whether a new DSP algorithm was required.

*(Statistics re-derived 2026-11-10; the earlier draft's window figures were not reproducible from the archived artifacts.)*

### 9.5 The IR payload is 128 taps; the encoder is a separate binary

Per the C63 release notes, the user-cab importer:

- accepts `.wav`, stereo or mono, 16- or 24-bit;
- takes **the first 128 samples of the left channel** and applies them to both outputs;
- stores 10 cabinet positions;
- is named **Jcabinet**, separate from X-Edit.

At 16-bit that is 256 bytes per slot (~2.6 KB for 10); at 24-bit, 384 bytes per slot (~3.8 KB). Flash/bandwidth are not constraints. 128 samples at 44.1 kHz is ~2.9 ms: this is a **128-tap FIR** (now confirmed in §11 — 128 signed 32-bit taps), i.e. a short cabinet-coloration filter rather than a long room IR. That is exactly the scale a small DSP coefficient RAM can hold, which makes the "data-driven 128-tap cab" hypothesis plausible.

The supplied `JUpdater Gsp1101vC63.exe` contains:

- `UserCabGainPage` (`cabGain`, `cabPos`, "Cabinet Index 1 to 10", "Store cabinet to GSP1101…", "Store temporary cabinet (vC59)", "mono/left toggle button");
- the HMG SysEx transport (`RxSysexMsg`, `TxSysexMsg`, `Super7RxSysexMsg`, `Super7TxSysexMsg`);
- `DownloadImagePage` / `ProgramDevicePage` for the online firmware-update flow.

It does **not** contain a WAV/AIFF decoder (`WavAudioFormat`, `AiffAudioFormat`, `AudioFormatManager` are absent) and no embedded second executable. So it can set cab gain/position and store/upload an already-prepared cabinet, but the `.wav → 128 samples` conversion is still missing; that is the Jcabinet step — which turned out to be a separate binary, `JUserCabUpdater vC59.exe`, fully reversed in **§11**. Correcting §2.4: the IR-import tool is **Jcabinet**, not X-Edit.

### 9.6 Consequences for the RP500 port

- **Host side is more favourable than the raw V20↔C63 byte diff suggests.** The RP500 already shares C63's 25-name, 9-byte-record cab table and indexes it with a big-endian pointer table. Adding 10 user entries is a bounded extension. *(Corrected 2026-11-11: the transport does **not** need a `USER_CAB` bulk-dump handler modelled on the GSP — the RP500's own protocol already carries presets, and all 12 gdigi message IDs are in its dispatch table. See `rp500_preset_protocol.md`.)*
- ~~**Storage is a non-issue.** 10 × 128 samples is a few KB; the RP500 has ~158 KB free flash.~~ **Withdrawn (2026-11-11).** The free flash is overwritten on every update, so it is not storage; there is no XRAM store either. The slots are kept by the device (`rp500_storage.md`), and the medium is still being pinned.
- **The gate is unchanged:** whether the RP500 DSP can load/execute a 128-tap coefficient block **and convolve with it**. The RP500 host has the same style of DSP loader (`bank14:0x99F0`, `bank15:0xBDE7`), but that loader carries a **24-byte descriptor**, and its 104-entry parameter table contains only `CAB_TYPE` (no LPF/user/IR parameter), and no user-cab strings.
- Because C63 added no new DSP primitive, a port is plausible **if** the RP500's cab engine is the same family and its coefficient RAM is loadable. Static images cannot settle that.
- **Flashing path: resolved in principle (see §10).** `NetUpdater 1.0.1` does list the RP500 (ProductID `0x5`) and downloads official `.DigBin` images from `UpdateTargets.xml`; the supplied `rp500_fw.bin` is byte-identical to the official 2.0 image. A patched image can be repackaged in the same container and served through a redirected `UpdateTargets.xml`.
- **Decisive test (revised 2026-11-11):** the GSP-side capture is no longer needed — the framing is recovered. What remains is the DSP: **G1** (does the RP500's AudioDNA2 accept a length-bounded, `0xF5`-terminated block?) and **G2** (does it convolve with it?). Roadmap S3.

### 9.7 Revised verdict

V20 is firmware 2.0 **without** user cabs; C63 is a later 2.0 feature build that adds 10 × 128-sample user cabs. The host-side delta is small, partly pre-existing (`USER_CAB %D`), and the RP500's cab table already matches C63's format and vocabulary — so the host-side port is the tractable part. The audio core is still a DSP coefficient/convolution path that the RP500 firmware does not visibly expose. The port remains **feasible only if** the RP500 DSP accepts a 128-tap block through its existing loader; otherwise it is blocked by missing DSP microcode/tooling.

---

## 10. Deployment path found: NetUpdater and the `.DigBin` container

This section removes the earlier "no RP500 flasher" blocker.

### 10.1 NetUpdater 1.0.1 supports the RP500

`NetUpdater1.0.1.exe` does not embed a device list; it fetches `UpdateTargets.xml` at runtime. The live XML lists, under Brand DigiTech / Family `RP`:

- `RP500`, **ProductID `0x5`**, ports `DigiTech RP500` / `USB Audio Device`;
- revisions **1.2** (Mar 2008), **1.4** (Nov 2008), **2.0** (Dec 2009), images `rp500V12.DigBin`, `rp500V14.DigBin`, `rp500V20.DigBin`.

The same XML lists `GSP1101` (Family `GSP Rack Products`, ProductID `0x01`, up to 2.0) but **not** any C-series build; the only C build ever referenced is a commented-out `Gsp1101vC20.DigBin` "Not Released".

So the official toolchain can update an RP500, and it obtains both the target list and the image over HTTP — both are redirectable.

### 10.2 The `.DigBin` container is now decoded

`rp500V20.DigBin` (1,048,708 B) and `Gsp1101v20.DigBin` (same size) share one layout:

```
12-byte header   00 5C 00 05 00 00 00 00 00 01 00 00
bank 0           64 KB flat (starts at offset 0x0C)
15 × {           8-byte descriptor: 00 kk 00 00 00 01 00 00
                 (bank index kk big-endian, length 0x00010000 big-endian)
                 64 KB bank body }
```

That is `0x0C + 0x10000 + 15 × 0x10008 = 0x100084` bytes. Reassembling the 16 bodies gives:

- RP500: **byte-identical to `rp500_fw.bin`**; the supplied image is exactly official firmware 2.0.
- GSP1101: byte-identical to the `BINFILE` resource extracted from `GSPUpdaterV20.exe`, confirming the earlier extraction.

There is no trailer and no per-file checksum in the container; the last two bytes `01 A5` are simply the end of bank 15's flat image. The 12-byte header is identical for both products, so it is a format marker, not a product/signature field.

### 10.3 Consequence for deploying a patched image

A patched RP500 flat image can be repackaged into a `.DigBin` by inserting the 8-byte bank descriptors and the 12-byte header, and published as a custom revision in a local copy of `UpdateTargets.xml` (hosts-file redirect or a patched URL string). No cryptographic signature is visible in the container.

Still unverified:

- whether the RP500 validates the image beyond the container (version/CRC check in the bootloader);
- the update-mode entry sequence the tool performs;
- whether the tool's device scan keys on the USB product ID alone (likely, per `TargetDevice`/`MidiTargetDevice`).

This makes a **hardware experiment possible**: reflash a patched RP500 with a modified cab table, then observe whether the DSP accepts extended cab indices. That is the decisive test from §7.3, now without needing a vendor flasher.

---

## 11. Reference encoder recovered: `JUserCabUpdater vC59.exe` (Jcabinet)

The missing Jcabinet tool was supplied as a separate binary. It contains the complete host-side path from `.wav` to the 2048-byte record the device stores, so **the user-cab data format is no longer unknown**.

### 11.1 What the binary is

- `JUserCabUpdater vC59.exe` (0xD6200 bytes, JUCE-based).
- UI class `UserCabGainPage` (vftable `0x4B6CB4`, constructor `FUN_00408600`): `Cabinet Gain` (dB, `cabGain`), `Cabinet Index 1 to 10` / `Cabinet position\n(1 to 10)`, `Store cabinet to GSP1101 else it will be a temporary cabinet`, `Store temporary cabinet (vC59)`, `mono/left toggle button` / `mono/left vC56`, `Gain in dB \n(-6 == 1/2)`.
- Warning shown by the store action: *"Warning! If the storing of the cabinet is interrupted then you will have to perform a factory reset and all your user presets will be lost."* — i.e. the cabinet record is written into user flash in place.
- Banner: *"This application will download impulse responses to your GSP1101 user cabinets"*.
- Transport: HMG SysEx classes (`TxSysexMsg`, `RxSysexMsg`, `Super7TxSysexMsg`, `Super7RxSysexMsg`) → USB-MIDI SysEx to the device (see §11.6).
- Validation strings: `Invalid Impulse File, not 'WAVE'`, `not 44100 Hz`, `bad bytes per sample`, `not enough samples`.

### 11.2 WAV acceptance rules (from `FUN_00406ed0`)

RIFF/WAVE, `fmt ` chunk size `0x10`, PCM (format 1), 1–2 channels, **44100 Hz only**, 16- or 24-bit (the release notes match this; the parser also carries a 32-bit scaling case and accepts block align 1–4 bytes), valid `data` chunk with enough frames. The first **128 frames of the left channel** are used and applied to both outputs; the right channel is read and discarded if present. A UI option bit (`[+0xCC] & 1` on the cab object) raises the cap from 128 to **208** frames.

### 11.3 Sample scaling

`16-bit: s << 12`, `24-bit: s << 4` → 28-bit full scale, then multiplied by the linear cabinet gain (from `cabGain`, dB) and rounded to a signed 32-bit integer (`FUN_004a7990`).

### 11.4 The 2048-byte record (exact)

| offset | size | contents |
|--------|------|----------|
| `0x000` | 4 | `00 5C 00 05` (built by `MOV DWORD [esp+0x24], 0x05005C00`) |
| `0x004` | 8 | `00 05`, `cabIdx * 8`, `00 00 00 08 00` |
| `0x00C` | 4 | tap count, **big-endian 32-bit**: `00 00 00 80` = 128 normally; `00 00 00 D0` = 208 with the option bit set |
| `0x010` | 512–832 | **N × signed 32-bit big-endian coefficients**, N = tap count |
| `0x210`/`0x350` | … | `0xFF` fill up to `0x7E7` (unused) |
| `0x7E7` | 23 | filename record, NUL padded |
| `0x7FE` | 2 | `[cabIdx, flag]` |

Notes:

- The `00 5C 00 05` magic is a 32-bit immediate in the encoder, which is why the literal byte sequence does not appear as data anywhere in the firmware images. It is a container/EEPROM-page signature, not a DSP command.
- The `cabIdx * 8` field is a slot descriptor in the record header; it is **not** the device address. Recovered transport (§11.6) shows the device window is 10 slots of `0x800` bytes at `0x50000`–`0x54FFF`, and the slot is selected by the `cabIdx` carried in the final `0x73` commit message, not by the header field.
- The tap-count field equals the number of coefficients actually written, so a 208-tap record and a 128-tap record are both valid; nothing pads the coefficient area to a fixed length.
- The `0xFF` padding and 23-byte name at the tail show the device writes one cab per 2 KB sector; the record is a sector image, not a raw DSP dump.

### 11.5 What the payload size means

The IR is **128 taps ≈ 2.9 ms at 44.1 kHz** (208 taps ≈ 4.7 ms with the option bit): a short speaker-coloration FIR, not a room impulse. 10 slots × 512 B of coefficients = 5 KB of user data, so flash and transfer time are non-issues. The remaining question is purely whether the DSP can execute that block.

### 11.6 How the record is transported

The record is **not** written by the firmware updater. `JUserCabUpdater vC59.exe` builds the 2048-byte buffer in a JUCE `MemoryOutputStream` and hands it to the HMG MIDI transport:

- message objects: `hmg::TxSysexMsg` / `hmg::Super7TxSysexMsg` (7-byte SysEx header) and the receive counterparts;
- queue: a producer thread (`FUN_0049f290`) dequeues and calls the sender `FUN_004a2170`;
- sender (`FUN_004a2170`): `midiOutShortMsg` only when the payload is shorter than 4 bytes; otherwise `midiOutPrepareHeader` + **`midiOutLongMsg`** + a spin on the `WHDR_DONE` flag and `midiOutUnprepareHeader`.

The record is **chunked**, not sent whole. `FUN_00403300` (the download slot at `MidiTargetDevice` vtable `0x4B5010 + 0x14`) walks the device address window `0x50000`–`0x54FFF` in 10 slots of `0x800` bytes and reads the source image in `0x100`-byte chunks:

- `FUN_00402200` reads up to `0x100` bytes from the image at the **absolute flash address** (the stream position is the address itself);
- `FUN_00402850` rejects a chunk whose bytes are all `0xFF`, so untouched slots are skipped rather than erased;
- every non-`0xFF` chunk is sent as one `0x7A` message (address + length + data);
- after the ten-slot sweep, one `0x73` **commit** message is sent, carrying the slot index and the store/temporary flag read from the record trailer at `slotBase + 0x7FE`.

So one 2048-byte cab = 8 data messages of `0x100` bytes (addresses `slotBase + 0x000 … + 0x700`) plus one commit message. The wire framing and the seven-byte `Super7` header are now fully recovered (§11.7); the earlier statement that the record travels as a single long message was wrong.

### 11.7 The Super7 wire format (fully recovered)

Every device message is built by `hmg::Super7TxSysexMsg` (`FUN_0040a750`) from a **7-byte header** — device ID dword, product word, command byte — followed by a 7-bit-packed payload:

| field | bytes | origin |
|-------|-------|--------|
| `F0` | 1 | SysEx start |
| `00 00 10 00` | 4 | device ID dword — copied from the handshake reply at `this+0x4C` |
| `5E 05` | 2 | product/family word — copied from the reply at `this+0x50` |
| `<cmd>` | 1 | opcode: `0x01` handshake, `0x7A` data, `0x73` commit |
| `<payload>` | n | Super7-packed data (below) |
| `<chk>` | 1 | checksum |
| `F7` | 1 | SysEx end |

- **Checksum** (`FUN_0040a910`): XOR of every byte after `F0` up to (but excluding) the checksum itself, masked to 7 bits (`& 0x7F`). It is appended by the finaliser `FUN_0040a8e0` together with `F7`.
- **Super7 packing** (`FUN_0040a830`): each group of **7** payload bytes is preceded by one *MSB byte* whose bits 6…0 are the high bits of those 7 bytes, and each data byte is then sent as `byte & 0x7F`. Trailing partial groups are padded within the same scheme. This keeps every transmitted byte a legal MIDI data byte.
- **Send / await** (`FUN_00403940(msg, timeout, expectedStatus)`): a message is sent and the caller blocks for an expected reply status.

The three application messages:

| message | command | body | expected reply | timeout |
|---------|---------|------|----------------|---------|
| handshake | `0x01` | fixed 7-byte header, no payload | status `0x02` | 500 ms |
| data write | `0x7A` | `<addr32 BE> <len16 BE> <packed data>` | status `0x7E` | 8000 ms (`0x1F40`) |
| commit | `0x73` | `30 01 <cabIdx> <flag>` | status `0x7E` | 8000 ms |

The handshake reply is parsed by `FUN_0040a260`, which fills the flag at `this+0x4E` (1 = 16-bit ID), the ID word at `this+0x4C/0x4D`, the product bytes at `this+0x4F/0x50/0x51`, and `this+0x5E`. **Because the header is read from the reply, no header constant is missing on the RP500 side** — the RP500's own reply is the header the tool would use, and the existing gdigi capture already shows that identity on the wire as `F0 00 00 10 00 5E 05 …`. That is why the old "7-byte Super7 header is unknown" item is now closed.

Notes and limits:

- The firmware-update path is a **different** protocol: `JUpdater Gsp1101vC63.exe` `FUN_00403350` uses commands `0x7B` (erase/flash page), `0x78` and `0x79`, not `0x7A`/`0x73`. User-cab upload and firmware update do not share opcodes.
- No application-side receiver for `0x7A`/`0x73` has been located in either 8051 image. A byte scan of bank 15 in `gsp1101_vC20` and `rp500_v20` for `MOV A,#7Ah` / `#73h` clusters produced only unrelated sites, and the GSP `USER_CAB %D` string at `0xF3338` has no direct code xref (it is reached indirectly through the diagnostic string table).
- The RP500 image contains **no** `USER_CAB`, `User Cab`, `USER %d` or `CAB_EN` string at all, so it has no user-cab command branch to point at. Whatever `0x7A` handling the GSP1101 has, the RP500 does not obviously share it.

---

## 12. Did the IR feature change the DSP side? — C48 → C63

This section directly answers whether "user cab" needed a new host↔DSP primitive.

### 12.1 C48 is the pre-IR control

`JUpdater GSP1101vC48.exe` (firmware at file offset `0xBF5F0`, image `0x100080`, stub `EA 80 68 02 30 83 53 91`) is a **pre-IR** build:

- its cab table (bank 10 `0x7620`) is the same **28 names** as the RP500 (`CHAMP1X8 … DIGISPKR`, `DIRECT`, `DREAD AC`, `JUMBO AC`);
- **no** `USER 1…10`, **no** `USER %d`, **no** `CAB_EN_XLR_LPF`;
- it *does* already contain `USER_CAB %D` at bank 15 `0x339E`.

C63 adds exactly: `USER 1…10` (bank 11 `0xD9E0`), `USER %d` (bank 0 `0xBFFC`), `CAB_EN_XLR_LPF` (bank 8 `0xE7F8`), and a moved `USER_CAB %D` (bank 15 `0x340F`).

### 12.2 The host→DSP command set did not grow across V20 → C48 → C63

Scanning every `MOV DPTR,#<reg>` site and the immediate value written next to it (disassembly-verified with `d51.py`):

| register | V20 | C48 | C63 | RP500 |
|----------|-----|-----|-----|-------|
| `0xE200` values | 1, 2, 4, 8, 0x10 | 1, 2, 4, 8, 0x10 | 1, 2, 4, 8, 0x10 | 1, 2, 3, 4, 8, 0x10, **0x20** |
| `0xE400` values | 1, 0x40, 0x80, 0xC8, 0xFE | 1, 0x40, 0x80, 0xC8, 0xFE | 1, 0x40, 0x80, 0xC8, 0xFE | (none) |
| `0xE800` values | 0xA0, 0xA4, 0xA9, 0xAF, 0xB8, 0xC0 | same | same | (none) |
| `0xD066` values | 6, 7, **0x84, 0x85**, 0x86, 0x87, 0x8B, **0x98** | 6, 7, 0x84, 0x86, 0x87, 0x8B | 6, 7, 0x84, 0x86, 0x87, 0x8B | 4, 5, 6, 7, 0x0B, 0x18 |
| refs `E000 / EE00 / D05A / D05B / D070` | 123 / 7 / 24 / 4 / 104 | 123 / 7 / 24 / 4 / 104 | 125 / 7 / 24 / 4 / 104 | 48 / 3 / 19 / 4 / 6 |

**The IR build added no new DSP command, no new register, and no new bulk primitive — it actually dropped two `0xD066` writes (`0x85`, `0x98`) that V20 makes.** The bank-14/15 DSP driver is the same code with shifted addresses, and bank 14 even keeps byte-identical instruction shapes (`ANL A,#FBh` / `XRL A,#04h` handshake, mailbox staging at XRAM `0x2F89/0x2F8A` in C48 → `0x327A/0x327B` in C63). This means the user-cab block must travel over a path that already existed in V20.

### 12.3 There are **no** factory IR coefficient tables in any image

A scan for stored 128-tap coefficient tables (512-byte blocks, tested at every 512-byte boundary, requiring ≥100 non-zero taps, all |value| < 2²⁴, a smooth sequence — total variation < 60 % of total magnitude — and front-loaded energy) found **zero** candidate blocks in C48, C63, RP500 and V20 alike:

| image | strict FIR-like blocks | blocks with all \|v\| < 2²⁴ |
|-------|-----------------------|----------------------------|
| C48 | **0** | 52 / 2048 |
| C63 | **0** | 38 / 2048 |
| RP500 | **0** | 302 / 2048 |
| V20 | **0** | — |

So:

- the 25 factory cabs are **not** stored as coefficient tables in flash (an earlier draft reported 11/6/10 "isolated" blocks; that used a much weaker filter that code bytes can satisfy by chance — the strict test finds none);
- they are computed/held by the DSP from a small parameter set (the `CAB_TYPE` byte plus DSP-internal structure).

That is the crucial asymmetry: factory cabs need only an index, while a user cab needs 512 bytes of arbitrary coefficients. A DSP that only implements parametric cab models cannot render a user IR.

### 12.4 The two remaining possibilities

Because no new command appeared, exactly one of these must be true:

1. **The DSP microcode changed** between C48 and C63 to add a raw-coefficient cab mode that reuses the existing command/mailbox channel (invisible to the 8051 side), or
2. **The mode already existed** and C48 simply had no UI/storage for it.

Static analysis of the 8051 images cannot separate them, because the DSP's own program is on the far side of the link. (The V20→C63 byte diff is ~90 %, so a silent microcode change is entirely possible.) **§12.7 adds a byte-level comparison of the two blocks the host sends to the DSP: it removes the firmware-side change (C48→C63 is byte-identical in the 113-byte init block) but still cannot see the microcode itself.**

### 12.5 The RP500 link is the *same family* but a *different implementation*

Shared host-port register set in both units: `0xE000`, `0xEE00`, `0xE200`, `0xE400`, `0xE800`, `0xD01F`, `0xD020`, `0xD05A`, `0xD05B`, `0xD066`, `0xD06D`, `0xD06E`, `0xD070`. The handshake idiom is the same: read the control byte, `ANL`/`ORL` a mask bit, write it back, mirror it to the data port.

Differences that matter:

| | GSP1101 (V20/C48/C63) | RP500 |
|---|---|---|
| `0xE200` command values | 1, 2, 4, 8, 0x10 | 1, 2, 3, 4, 8, 0x10, **0x20** |
| control/mailbox | XRAM `0x2F89` / `0x2F8A` (C48), `0x327A` / `0x327B` (C63) | XRAM `0xFDFC` + staging `0xF4D3`, `0xF4AE`, `0xF4FA`, `0xF431`, port `0xE600` |
| `0xD070` references | 104 | 6 |
| bulk channel | `SEND BLOCK` / `FLASH_DATA: %D` service path | `MOVC` flash→`0xD070` byte stream, flow-controlled by `0xD06E` status bits, **no length limit** (the `0x7FF8` compare is a stall abort; measured 118 650 bytes and still going) — bank 15 `0xBE97` loop, source based at bank15 `0x2E3B`, **24-byte descriptor** |
| **variable-length (terminated) DSP stream** | **32** XRAM-sourced streams (`0x2445+index` C48, `0x2603+index` C63), `0xF5` terminator — **the user-IR path** | **none** |

So the RP500 has a block-transfer channel to its DSP, but only a **fixed-length,
code-sourced** one. The GSP's user cabinets ride on a **second, variable-length
channel that the RP500 firmware does not implement** (§13.10).

### 12.6 Revised verdict

| Work item | Status |
|-----------|--------|
| Cab table / UI / 10 slots | Feasible — same table shape as C63 |
| Preset transport | **Solved** — the RP500's own protocol; `MOVE_PRESET` (0x39) framing recovered, all 12 gdigi IDs present (`rp500_preset_protocol.md`) |
| Storage of the 10 records | **Not host-side** — no free flash and no XRAM store; the device owns it (`rp500_storage.md`). Medium risk until the medium is pinned (S2c) |
| IR file format / conversion | **Solved** — §11 gives the exact 2048-byte record |
| Host→device transport (GSP) | **Solved** — handshake + `0x7A` chunks + `0x73` commit, Super7 packing (§11.6–11.7) |
| Deployment (reflash) | Known in principle — `.DigBin` repack + `UpdateTargets.xml` (§10) |
| **A variable-length DSP stream on the RP500** | **Must be added** — the RP500's only stream carries a 24-byte parameter descriptor; the GSP's user-cab path (32 XRAM-sourced streams, `0xF5` terminator) has no RP500 equivalent (§13.10) |
| **RP500 DSP renders 128 taps** | **Unproven — the only gate (G1 + G2)** |

A pure 8051-firmware patch can add the menu entries, the 10 slots, the transport, the XRAM staging and the terminated DSP stream, and it can convert a WAV exactly as DigiTech's tool does. It **cannot** make the RP500 produce a user IR unless that DSP accepts a variable-length block **and convolves with it**. That is now a single, testable question rather than an open-ended unknown. *(Revised 2026-11-11: "the flash records" and "the `USER_CAB` SysEx handler" were both withdrawn — see the rows above.)*

### 12.7 Byte-level comparison of the DSP-facing blocks (2026-11-12)

§12.4 left two possibilities: the DSP microcode changed at C63, or the capability
pre-existed. A direct byte comparison of the two blocks the host actually sends
to the DSP narrows this without needing the microcode. Full data:
`05_evidence/2026-11-12_dsp_block_comparison.md`.

**Method.** The code-space stream routine was located in each image by its
instruction shape (`MOVC A,@A+DPTR` → `MOV DPTR,#D070` → `MOVX @DPTR,A`), and
its source-base constant read out of the preceding `ADD A,#lo` / `MOV A,#hi`.
The 113-byte register-init block was located by the `0xD000+index` copy loop
(limit `0x71`, skip `0x59`). C48/C63 were compared after `payload16()`
extraction (the interleaved 8-byte-descriptor container).

| Block | RP500 vs V20 | C48 vs C63 | result |
|---|---|---|---|
| code-space stream routine | — | — | **instruction-identical**; only counter XRAM and source base differ |
| XRAM variable-length channel | **0 vs 32 sites** | 32 vs 32 | present in V20 (2006), absent from the RP500 |
| 113-byte DSP register init | **91/113 (80.5 %)** | **113/113 (100 %)** | 91 bytes identical; 22 device-specific bytes at `0x20–0x37`, `0x5C`, `0x5E`, `0x63`, `0x66` |
| 24-byte stream descriptor | **17/24** | identical | the entire 15-byte body is shared; 7 device-specific bytes |

**What it settles.**

1. The host↔DSP interface is the **same family and largely the same register
   map**: the same stream loop, the same `0xD070`/`0xD06E` ports, and 91 of the
   113 init bytes literally identical.
2. **C48 → C63 changed nothing in the DSP configuration that is visible in
   firmware.** The 113-byte init block is byte-identical, and the stream
   protocol is unchanged. This is independent confirmation of §12.2's "no new
   DSP command".
3. **The variable-length channel predates the IR feature.** The oldest build
   (v11) already has all 32 XRAM-sourced stores (2 handlers × 16 code banks)
   and the `0xF5` terminator, with only the XRAM scratch addresses moved. The
   IR build did not create the primitive; it started using it for cabinets.

**What it does not settle.** The GSP1101 has **two** AudioDNA2 chips; the RP500
has **one**. Their masks/part numbers were never compared (RP500 U25 reads
`72-1002 GREEN / 7169170 / 1012 KOREA`; no GSP board photograph exists in the
corpus). The RP500 host also never sends a variable-length block, so the DSP's
acceptance of one is unobserved. The block comparison therefore **supports**
the "capability pre-existed, C63 added only the order" hypothesis — it removes
the firmware-side change — but it cannot confirm the chip-level capability. That
still requires a bus capture or the DSP microcode. A 2026-11-12 static test of
the two-chip question found **no chip-select in the IR path**: both handlers
read one XRAM stream and write one `0xD070` port, and the only GSP-only
two-select access (`0xE400` ← `0x40`/`0x80` + read `0xEC40`) is a status/ID
path. See §13.3 and `05_evidence/2026-11-12_gsp_two_chip_test.md`.

---

## 13. Suggestions

### 13.1 Pick the cheapest decisive experiment first

Do **not** start by writing the host patch. The DSP question can be answered with a much smaller experiment:

1. ~~**Bus-level probe (no firmware patch).**~~ **Partly done on hardware.** The USB-side cab sweep (Appendix B) showed every accepted `CAB_TYPE` change sends only the 2-byte parameter value — no block. That closes the *host/USB* half of the question. What remains is the **RP500 8051↔DSP bus itself**: capture the writes while changing `CAB_TYPE` across all 28 models. If each change is **one byte**, the models are DSP-resident and the only route is DSP microcode; if a **block** appears, diff two cabs' blocks — that is the coefficient format, and the port becomes a host-side job.
2. **Single-slot patch (if step 1 is inconclusive).** Patch only the RP500 cab table (bank 4, `0x3486`, 28 → 29 entries), add the **new terminated XRAM stream**, and drive it with the RP500's own preset protocol (`MOVE_PRESET` 0x39). *(Corrected 2026-11-11: the earlier plan — "add a `USER_CAB` handler that writes the 2048-byte record to the free `0x5FD0` block, and select it through the existing bank-15 `0xBE97` stream" — is withdrawn on **both** counts. There is no free `0x5FD0` block to write to (it is overwritten on every update, `rp500_storage.md`), and the existing stream carries a 24-byte parameter descriptor, not IR data (§13.10).)*
3. **Measure.** Audio out = proceed; silence/DSP error = stop.

### 13.2 Reuse what is already recovered

- The **encoder is done** — `usercab_encode.py` produces the exact 2048-byte record. Do not reimplement it; feed it a WAV and write the output.
- The **container is solved** — repack the patched flat image with the 8-byte descriptors and the 12-byte `00 5C 00 05 …` header (§10.2). No signature is present in the container.
- The **transport is solved, and it is the RP500's own** — `MOVE_PRESET` (`0x39`) / `RECEIVE_PRESET_PARAMETERS` (`0x2D`), with gdigi as a working client (`rp500_preset_protocol.md`). That replaces the GSP's `0x7A`/`0x73` framing for this port.
- The **DSP channel is identified** — `0xD070` with `0xD06E` flow control; note it carries a **24-byte descriptor**, so IR data needs the new stream (§13.10), not a re-point.

### 13.3 What is still unresolved

- **The DSP gate.** G1: does the AudioDNA2 accept a length-bounded, `0xF5`-terminated block? G2: does it convolve with it? Nothing static answers this; roadmap S3.
- **The preset medium (S2c).** The user bank's physical store is narrowed to the `MOVE_PRESET` user branch (bank 7 `0xABD2` → `0x0B4B` → `0xD8AD`) but not yet identified.
- **The GSP's Jcabinet receiver.** The framing is complete (§11.7) but no `0x7A`/`0x73` handler was located in either GSP 8051 image. *(This no longer blocks the RP500 port — the RP500 uses its own protocol — but it remains an open question about the GSP.)*

### 13.4 If the DSP gate fails

- The "replace one factory model" variant (§7) does **not** avoid the same gate — it only shrinks the host work. Do not treat it as a fallback that produces audio.
- The only real fallback is a different platform: the GSP1101 (or another AudioDNA2 device with user cabs) already does this in silicon.

### 13.5 Practical cautions

- C63/C48/C59 are **unofficial** builds by a former employee, released after EOL. There is no vendor toolchain, no source, and no support; treat every finding as reverse-engineered fact, not documented behaviour.
- The `.DigBin` container has **no checksum or signature**. Recovery is nevertheless expected to be safe: per the author of the open-source RP500 uploader, a firmware image that does not work causes the unit to fall back to the bootloader's flashing process. That claim is **reported, not experimentally tested** — deliberately flashing a broken image to prove it is not part of the plan, because it risks the unit for information obtainable by static analysis of the bootloader. Mitigation is procedural instead: keep a known-good `rp500V20.DigBin`, keep every build a minimal delta from stock, and validate new code in an emulator before flashing.
- The GSP1101 store path warns that an interrupted cabinet write forces a factory reset. *(Superseded 2026-11-11: the RP500 port does **not** write flash — there is no free flash and the device owns preset storage (`rp500_storage.md`). The atomicity requirement therefore lands on the device's own store, not on ours.)*

---

## Appendix: key addresses

- GSP1101 firmware: updater `.data` offset `0x19F8`; image `0x100080` = 16 × 64 KB bodies with 8-byte descriptors (`00 kk 00 00 00 01 00 00`) interleaved before banks 1–15 plus an 8-byte trailer. Bank-entry stub (first bytes of every body): `EA 80 68 02 30 7A 53 91` (C63).
- GSP1101 cab table: flat `0xBD8D2` (bank 11, `0xD8D2` = `DREAD ACOUSTIC`; `CHAMP1X8` at `0xD8F6`); long-name copy in bank 5 around `0x42F5`.
- GSP1101 service strings: bank 15 `0x32B2` (`Erase %u`) … `0x359A` (`FLASH_DATA: %D`); `USER_CAB %D` `0x340F`.
- RP500 cab table: flat `0x43486` (bank 4, `0x3486`); no USER entries.
- RP500 service bank: bank 15 `0x2C80` (`RP 500`), `0x2C92` (`UPDATE`), `0x2CB4` (`UPLOAD`), `0x5270` (`GL PARAM`), `0x5279` (`BULKERR1`).
- Updater: `UserCabGainPage` RTTI VA `0x5C3034`; constructor `FUN_00407b40`; user-cab wide strings `0x4A7698`–`0x4A7994`; `Super7RxSysexMsg` RTTI `0x5C1758`, `Super7TxSysexMsg` `0x5C1798`; no WAV/AIFF decoder.
- V20 firmware: `GSPUpdaterV20.exe` `BINFILE` `0x51E18`; flat 1 MB = 16 × 64 KB bodies; bank-entry stub `EA 80 68 02 2E C5 53 91`.
- V20 cab table: bank 10 `0x5820` (specials) / `0x5844` (`CHAMP 1X8`); 21 long names; no USER entries.
- C63 cab table: bank 11 `0xD8F6` (25 fixed 8-char names); `USER 1`…`USER 10` at `0xD9E0`; `USER %d` bank 0 `0xBFFC`; `CAB_EN_XLR_LPF` bank 8 `0xE7F8`.
- RP500 cab pointer table: bank 4 `0x478E`, 28 big-endian 16-bit pointers; 9-byte name records at `0x3453` (DREAD/JUMBO/DIRECT) and `0x3486` (25 speaker models).
- RP500 parameter table: bank 6 `0xC563`, 104 entries; only `CAB_TYPE` for the cab block.
- Free flash (runs ≥ 256 B): GSP1101 `0x4E19` total (largest `0x14FB`); RP500 `0x277BA` total (largest `0x5FD0`).
- C48 firmware: `JUpdater GSP1101vC48.exe` file offset `0xBF5F0`; image `0x100080`, stub `EA 80 68 02 30 83 53 91`; cab table bank 10 `0x7620` (28 entries, no USER slots); `USER_CAB %D` bank 15 `0x339E`.
- C59 encoder: `JUserCabUpdater vC59.exe`; WAV parser/encoder `FUN_00406ed0`; float→int `FUN_004a7990`; buffer write `FUN_0047c0f0`; gain `FUN_004067f0`; only xref to `0x406ed0` is the vtable data at `0x4b68e4`.
- C59 UI/transport: `UserCabGainPage` vftable `0x4B6CB4`, constructor `FUN_00408600`; sender thread `FUN_0049F290`; MIDI long/short sender `FUN_004A2170` (`midiOutLongMsg` when length ≥ 4, else `midiOutShortMsg`); HMG `Super7TxSysexMsg`/`Super7RxSysexMsg` RTTI `0x4D5110`/`0x4D50CC`.
- C59 protocol: device vtable `0x4B5010` (slot `+0x14` = download `FUN_00403300`); handshake `FUN_00402eb0` (reply `FUN_0040a260`); frame builder `FUN_0040a750`; Super7 packer `FUN_0040a830`; checksum `FUN_0040a910`; finaliser `FUN_0040a8e0`; send/await `FUN_00403940`; chunk reader `FUN_00402200`; all-`0xFF` skip `FUN_00402850`. Window `0x50000`–`0x54FFF`, 10 slots × `0x800`, chunk `0x100`.
- X-Edit GSP1101 differential (`Hmg.Devices.dll`): vC46 → vC63 adds cab rows 26–35 (IDs `596`–`604`, `736`), param `2510` "Cab Enable LPF to XLR", field `MidiOutPresetMapCount`; class/method set otherwise identical.
- Encoder reimplementation: `usercab_encode.py` reproduces the record byte-for-byte; `--selftest` covers 16-bit mono 128 taps, 24-bit stereo 128 taps with −6 dB gain, 16-bit 208 taps, and WAV rejection. All pass.
- REA artifacts for `JUserCabUpdater vC59.exe`: `rea_evidence_c59.json` (112 records) and `rea_c59_snapshot.bin` (96 evidence records).
- DSP host-port registers (both units): `0xE000`, `0xEE00`, `0xE200`, `0xE400`, `0xE800`, `0xD01F`, `0xD020`, `0xD05A`, `0xD05B`, `0xD066`, `0xD06D`, `0xD06E`, `0xD070`.
- RP500 DSP byte-stream: bank 15 `0xBE97` loop (`MOVC` from `0x2E3B + n` → `0xD070`, status at `0xD06E`; **no length limit** — the `0x7FF8` compare at `0xBE3D` is a stall abort; measured 118 650 bytes and still going); the payload is a **24-byte parameter descriptor** followed by code; setup helper bank 15 `0xDBB3` (`0xD020/0xD05B/0xD06D/0xD06F`); twin in bank 14 around `0x9A12`.
- RP500 **113-byte DSP configuration block** (identical in banks 14 and 15, at `0x2C80` / `0x2CBB`) copied byte-wise into DSP registers `0xD000`–`0xD070`, skipping `0xD059`; bank 15 loop at `0xB86A`–`0xB8A0`. Its last byte lands on `0xD070`.
- RP500 DSP stream capture under uCsim: `04_analysis_scripts/rp500_ucsim_stream.py`; result in `05_evidence/2026-11-11_ucsim_dspstream_long.md` (and the short log `2026-11-11_ucsim_dspstream.log`).
- GSP1101 **variable-length** DSP stream (the user-IR path): 32 XRAM-sourced stores, base `0x2445+index` (C48) / `0x2603+index` (C63), index cell XRAM `0x233F`/`0x24FD`, length cell XRAM `0x2546`/`0x2704`, `0xF5` terminator; IR staged from XRAM `0x1483+` → `0x2603+` with the count in XRAM `0x14C3` (C63 bank 15 `0xD7D1`). The RP500 has **none** of this.
- GSP1101 DSP mailbox: XRAM `0x2F89/0x2F8A` (C48), `0x327A/0x327B` (C63); first `E200` write site bank 14 `0xB2C7` (C48) / `0xB2ED` (C63), writing `E200` 1/2/4/8/0x10 and `E400` 1/0xC8/0xFE.

## 13. What the port actually requires (2026-11-11)

This section replaces the "diff C48 against C63" plan, which turned out to be
impossible, and records what the two firmwares actually show.

### 13.1 C48 → C63 is a full rebuild, not a feature patch

| Measure | Value |
|---|---|
| Common prefix between the two images | **10 bytes** (the bank-entry stub) |
| Bytes that differ | **884,624 of 1,048,576 (84.4 %)** |
| Differing clusters per bank | 2,555 – 8,530 |
| DSP host-port usage C48 vs C63 | **identical** (`0xE000` ×123/×125, `0xD070` ×104/×104, `0xD01F` ×57/×57, `0xEE00` ×7/×7) |

So the IR build is a different program, and a byte diff cannot isolate the
feature. **But** the DSP interface is bit-for-bit the same set of ports in both
builds, which independently confirms §12.2: *the user-cab feature adds no new
DSP command, register or primitive.* The GSP reuses the machinery it already
had.

### 13.2 What C63 adds on the firmware side

| Item | C48 | C63 |
|---|---|---|
| Cab name table (bank 11) | — | `0xD8F0`: 25 factory names (`AMP1X8` … `DIGISPKR`), `DIRECT`, then `USER 1` … `USER 10` at `0xD9C8` |
| Second copy of the USER names | — | bank 5 `0x46A8` (`USER 1` … `USER 10`) |
| `USER_CAB %D` message | bank 15 `0x3396` | bank 15 `0x3407` |

The `USER_CAB %D` *message* exists in C48 too — the feature is new in C63, the
string is not. The cab list is the firmware-side surface of the feature: ten
new entries.

### 13.3 Two AudioDNA chips in the GSP1101 — one DSP in the RP500

> **Correction (hardware owner, 2026-11-11): the RP500 has a single AudioDNA
> DSP.** The GSP1101 has two physical chips. An earlier draft of this section
> read the RP500's two stream sites as two DSP conversations; that is wrong.
> They are **two coefficient sets delivered to the same DSP**.

Both units use the same host interface and both contain two code-space stream
sites:

| Unit | Code-space stream sites | XRAM stream sites | Command port | Status | Data port |
|---|---|---|---|---|---|
| GSP C48 | banks 14, 15 | **32** | `0xE000` | `0xD06E` | `0xD070` |
| GSP C63 | banks 14, 15 | **32** | `0xE000` | `0xD06E` | `0xD070` |
| RP500 v2.0 | banks 14, 15 | **0** | `0xE000` | `0xD06E` | `0xD070` |

On the RP500 the two sites are distinguished by **which parameter blob they
read** and **which command byte they latch** into `0xE000`:

| Site | Source in code space | Command byte | Bytes |
|---|---|---|---|
| bank 14 `0x9AB6` | `0x2DC2 + n` | `0xC0` / `0xC1` | `ADD A,#0C2h` … `MOV A,#2Dh` |
| bank 15 `0xBEA8` | `0x2E3B + n` | `0xA0` | `ADD A,#3Bh` … `MOV A,#2Eh` |

> **Correction (2026-11-11): these are not "two coefficient sets".** The two
> blobs are **24 bytes each and byte-for-byte identical**
> (`c9 12 12 34 12 10 00 09 01 01 0c 50 0a 20 01 00 12 ab 02 0a ed 02 00 1f`),
> and each is **immediately followed by executable code**. They are
> cabinet-independent **DSP parameter descriptors**, not IR payloads and not
> left/right channels. See §13.10.

> **Correction (2026-11-12): the `0xFDFC` claim above was wrong.** `0xFDFC` is
> **RP500-only** (49 references; **zero** in every GSP1101 build from v11 to
> C63). The GSP does not select its second chip through it. The GSP's only
> two-select access is `0xE400` ← `0x40`/`0x80` paired with reads of `0xEC40`
> (a status/ID path, not the IR path), and the user-IR stream itself writes only
> `0xD070` and the `0xE000` flow-control byte. Both of the GSP's "32 XRAM
> stores" are **2 interrupt handlers × 16 code banks**, not two chips. See
> `05_evidence/2026-11-12_gsp_two_chip_test.md`.
>
> So the firmware **does not address the two chips independently**. Whether
> only one of them carries the convolution microcode is invisible to static
> analysis; the hypothesis remains possible, not demonstrated.

> **Resolved at the part-number level (2026-11-12).** The GSP1101 parts list
> (`03_docs/GSP1101 parts list.docx`, 08/31/2007) lists
> `72-1002 | B | 2 | IC Audio DNA2 Rev B ASIC 144 pin LQFP`. The RP500's U25 is
> the **same base part `72-1002`** (marked `72-1002 GREEN`). So the two units
> do **not** use different AudioDNA2 variants: the GSP has **2 × `72-1002`**
> and the RP500 has **1 × `72-1002`**. "Only one chip, unique to this product,
> has the convolution instructions" is therefore **refuted**. The GSP's second
> chip buys capacity (two DSP + two 64 Mbit SDRAM subsystems, `72-0099` ×2),
> not a different instruction set. What is *not* refuted is whether the two GSP
> chips run different microcode; that is still invisible, but it no longer
> matters for the RP500, whose chip is the same part. The remaining question is
> microcode / enablement, not chip identity. The board also carries an **EPM3032A CPLD**
> (`72-0175`), the likely address-decode / chip-select for the two DSPs — which
> is why the host never emits a DSP-id byte. The sibling BOMs confirm the
> pattern: GNX 2 = **3 × `72-5433`** (first-gen Atmel AudioDNA), RP50 =
> **1 × `72-5433`**, GSP1101 = **2 × `72-1002`**, RP500 = **1 × `72-1002`** —
> the DSP count is a tier/capacity choice, not a feature flag. See
> `05_evidence/2026-11-12_gsp1101_parts_list.md`.

### 13.4 The RP500 streams a 24-byte parameter descriptor out of its own code space

RP500 bank 15, `0xBE97`:

```
BE97  MOV  DPTR,#0FF24h
BE9A  MOVX A,@DPTR
BE9B  MOV  R6,A
BE9C  INC  DPTR
BE9D  MOVX A,@DPTR
BE9E  ADD  A,#3Bh        ; source = 0x2E3B + counter
BEA0  MOV  82h,A
BEA2  MOV  A,#2Eh
BEA4  ADDC A,R6
BEA5  MOV  83h,A
BEA7  CLR  A
BEA8  MOVC A,@A+DPTR     ; read a coefficient byte from CODE space
BEA9  MOV  DPTR,#0D070h
BEAC  MOVX @DPTR,A        ; hand it to the DSP
```

One byte at a time, with the `0xD06E` status poll between bytes, and the
counter lives in XRAM `0xFF24`.

**What is actually streamed (corrected 2026-11-11):** the 24 bytes at
`0x2E3B` —

```
c9 12 12 34  12 10 00 09  01 01 0c 50  0a 20 01 00  12 ab 02 0a  ed 02 00 1f
```

— **identical to the 24 bytes at `0x2DC2` in bank 14**, and immediately
followed at `0x2E53` by the next function (`E6` = `MOV A,@R0`). So the payload
is a cabinet-independent **DSP parameter descriptor**.

**There are no factory cabinet IRs.** The factory cabinets are **parametric
DSP models**: the strict coefficient-block scan (smooth sequence, `|v| <
2²⁴`, ≥100 non-zero taps, front-loaded energy) finds **zero** 128-tap
coefficient blocks in the RP500, the GSP C48, the GSP C63 or the GSP V20
images. An impulse response is therefore not a factory-cabinet concept at all
— it is the **user-cabinet feature**, which the GSP1101 *added* in firmware
C54. The RP500's host never asks its DSP for one.

The loop's cap: there **is none** in the host code. The compare against the
constant **0x7FF8** (`BE3D SUBB A,#0F8h`, `BE40 SUBB A,#07Fh`) sits on the
branch taken when the DSP status **did not change** (`BE2D JB E2h,BE4C` is the
"it changed" branch), so it is a **stall abort** — after ~256 consecutive polls
with an unchanged status, and once the byte counter's high byte reaches
`0x7F`/`0x80`, the firmware abandons the conversation. With a DSP model that
always acknowledges, the firmware pushed **118 650 bytes** and was still going
(`05_evidence/2026-11-11_ucsim_dspstream_long.md`) — the first 24 are the
descriptor, everything after is **code**.

The GSP's *user-cab* path is a different routine on a different source: see
§13.10.

### 13.5 Where the GSP keeps user cabs

Not in the firmware image. The Jcabinet tool writes them into the device's
**user-data flash** (window `0x50000`–`0x54FFF`, 10 slots × `0x800`), which is
the same area that holds user presets — consistent with the C59 warning that
interrupting a store costs all user presets. Bank 5 of the firmware image
contains code and strings at those offsets, i.e. the user-data area is *not*
part of the 1 MB firmware image.

### 13.6 What this changes

> Superseded 2026-11-11 — see §13.10. The rows below were written when the
> RP500's 24-byte parameter descriptor was still believed to be a coefficient
> blob; the "different source" conclusion does not hold.

| Question | Answer |
|---|---|
| Can the RP500's DSP take an arbitrary coefficient block? | **Unknown.** The RP500 streams a fixed 24-byte parameter descriptor to the DSP, and nothing in its firmware asks the DSP for a variable-length block. The GSP does exactly that (a variable-length XRAM-sourced stream with a `0xF5` terminator; 32 store sites = 2 handlers × 16 code banks), on the same chip family and the same register map — so the capability probably exists, but it must be **measured**. |
| Is the GSP's user-cab load code portable verbatim? | **No** — the GSP host writes one `0xD070` stream, but the GSP board carries **two physical AudioDNA chips** and the firmware does not select between them; the RP500 has **one** DSP and no such stream. Porting the *code* is the wrong move. |
| Is the *feature* portable? | Yes, in four pieces: (a) a place to store the record, (b) a way to read it back, (c) a way to stage it into XRAM, (d) **a variable-length terminated stream to the DSP** — (d) does not exist on the RP500 and has to be added. |
| What is still unknown | (i) whether the RP500's AudioDNA2 accepts a variable-length block (the gate); (ii) whether the RP500's *user-data* flash (where presets live) is writable and addressable from firmware code; (iii) whether the GSP streams the 2048-byte record or only its 512-byte coefficient part. |

### 13.7 The manual settles the semantics (C54 release notes, §IV "User Cabs")

> "The 1101 now features user cabs. … Impulse responses should be a .wav file
> and can be stereo or mono 16 or 24bit. **The downloading app takes the first
> 128 samples (of the left channel) that it finds and applies these to both of
> the outputs.** Therefore we recommend removing any 0's at the beginning of
> your impulse response with a sound editing application."
> — `03_docs/GSP1101 RELEASE NOTES VERSION C54.txt` lines 303–310

Three facts fall out, and all three simplify the port:

| Manual fact | Consequence |
|---|---|
| **Mono.** Only the left channel is used, and **the same IR is applied to both outputs**. | The user IR is *one* block, duplicated to both channels. On the RP500 (one DSP) no stereo handling is needed either way — the descriptor is cabinet-independent and the user record is a single block. It also means that *if* the GSP's two chips receive the IR, they receive the same mono block. The firmware's "two stream sites" are **not** evidence of this: they are two interrupt handlers replicated across 16 code banks, both reading one XRAM stream and writing one port `0xD070` (`05_evidence/2026-11-12_gsp_two_chip_test.md`). |
| **"remove any 0's at the beginning"** | The IR is written at the **head of a fixed-length coefficient block**; leading zeros simply delay the response. The DSP is therefore **not** told a new IR length — the user IR is the first 128 samples of the block, with zeros after. No DSP reconfiguration is required. (There are no *factory* IRs to share a block with — factory cabinets are parametric models; the IR is the added user-cabinet feature.) |
| "Set the user preset to one of the user cabinet positions. Then start the Jcabinet updater." | The upload is **targeted at the currently selected slot** — the device must be positioned on a user cab before the transfer. So the port needs a UI slot to aim at (L4), exactly as the GSP has. |

Our encoder already matches the first row exactly (`usercab_encode.py`:
"first 128 left-channel frames (right discarded)", `--selftest` green), so the
record format is not a risk.

### 13.8 What the port therefore looks like

> **Superseded 2026-11-11 — see §13.10.** The "Audio" row below was based on
> the belief that the RP500's existing stream carried an IR-sized payload. It
> does not: it carries a 24-byte parameter descriptor, so re-pointing its
> source cannot deliver a user IR.

| Piece | Change | Size |
|---|---|---|
| Upload path | implement the `0x7A`/`0x73` receiver (L3) — protocol fully recovered (§11.7) | a stub in the `0x5FD0` free run |
| Storage | 10 slots × `0x800` in the user-data area (or the free run) | 20 KB |
| UI | 28 → 38 cab entries, `USER 1..10`, and the "select the slot before uploading" behaviour (L4) | table + menu branch |
| **Audio** | ~~change the stream's source~~ — **wrong**: the existing stream carries a 24-byte parameter descriptor, not IR data | — |
| **Audio (corrected)** | **add** a variable-length, XRAM-sourced, `0xF5`-terminated stream to the DSP (a port of the GSP's pull routine), and stage the user record into the XRAM block it reads | ~80 B of stub |
| Select | when a USER cab is chosen, stream *that* record instead of the factory descriptor | one hook |

### 13.9 What the literature adds (and what it settles)

The archived documentation answers several questions the reverse engineering had
left open. Every statement below is quoted from the files in `03_docs/`.

#### From the GSP1101 C63 release notes (the IR build) — `gsp1101 release notes version c63.txt`

> **NEW SPEAKER CABS:** "GIBSON 1X12", "JAZZ 2X12", "RECTIFIED 4X12", **"USER CABS"** (line 100–105)

> "In the next screen you will be prompted for a **gain setting** and a **cabinet position**. It is important to note that impulse responses can greatly increase the output gain on the 1101… We recommend starting with a lower setting such as -30." (lines 357–364)

> "There are **10 cabinet positions** that you can store a cabinet to. You can **audition** any cabinet without storing it to the 1101 by leaving the *Store Cabinet to 1101* unchecked. These unsaved changes will be lost if you change cabinets, change a parameter that alters the cabinet state or change presets… Auditioning is useful because it is quick and doesn't require the 1101 to reboot." (lines 365–374)

> "The updater will then load the cabinet to any program so you can instantly hear the effect of the new user. If you selected store cabinet to the 1101, it will **write the cabinet to flash and reboot**… It is important not to interrupt the unit while it is writing to flash! If this happens the unit may need to be factory reset…" (lines 379–389)

> "the user cabinets work just like the other cabinets and **don't come out the ¼" outputs** unless you have the option turned on… There is also a new parameter in the amp menu that allows you to turn on or off the **low pass filter**." (lines 393–397)

| What it settles | How |
|---|---|
| The commit **flag** in our recovered protocol (`0x73 30 01 <idx> <flag>`) is the **audition / store** bit | audition = temporary (no reboot), store = write to flash + reboot. Both are host-side choices; the wire format is the same |
| The **gain** is applied at upload time, in dB | matches `usercab_encode.py --gain-db`; the manual warns IRs can raise output gain a lot (start at -30 dB) |
| **10 slots** | confirms the 10 × `0x800` window |
| The upload is **aimed at the currently selected slot** | "Set the user preset to one of the user cabinet positions" |
| Interrupting a store can cost the **factory reset** | matches the C59 warning in §11 and the atomic-commit design |
| The C63 build **also changed the factory cab list** | explains why the C48 and C63 cab tables differ beyond the USER rows |
| User cabs bypass the ¼" (XLR) outputs unless enabled | matches the `CAB_EN_XLR_LPF` parameter (ID 2510) found in the X-Edit vC46→vC63 diff |

#### From the GSP1101 C54 release notes (first user cabs) — `GSP1101 RELEASE NOTES VERSION C54.txt`

> "The 1101 now features user cabs… The downloading app takes the **first 128 samples (of the left channel)** that it finds and **applies these to both of the outputs**. Therefore we recommend removing any 0's at the beginning of your impulse response…" (lines 303–310)

Already used in §13.7: the IR is **mono**, written at the **head of a
fixed-length block**, and the upload is aimed at the selected slot.

#### From the RP500 owner's manual — `RP500_OM_EN.txt`

> "Armed with DigiTech's patented **AudioDNA2** custom audio **DSP chip**" (line 218)

> "DSP Section: AudioDNA2T DSP Processor … Preset Memory: **100 User Presets (1-00) / 100 Factory Presets (F1-F00)**" (line 1929)

> cab list entries: "dread AC / Dreadnaught acoustic", "jumbo ac / Jumbo acoustic", "direct / No amp" (lines 1310ff)

| What it settles | How |
|---|---|
| The RP500 has **one** AudioDNA2 chip | the manual says "chip", singular — corroborates the hardware owner's correction and settles §13.3 (the GSP1101 has two *physical* chips; the RP500's two stream sites are two parameter-descriptor conversations with one chip) |
| The RP500's user-data area holds **100 user presets** | the GSP keeps user cabs in the same area as user presets, so the RP500's user-cab storage has a home — and, unlike the firmware's free run, it survives a firmware update |
| The RP500 cab list is the manual's list | `DIRECT`, `DREAD AC`, `JUMBO AC` in the manual match firmware cab entries 25–27 exactly — the cab table in the image *is* the manual's list |

#### From the GSP1101 signal flow — `GSP1101 Signal Flow.txt`

Archived text (42 lines; the diagrams are images). It documents the *audio
routing*, not the DSP: effects after the loop are mono with the stereo dry
summed into both outputs; left/right are summed before an effect unless the
channel's level is 0, which acts as a switch. **This is the GSP1101's external
routing, not the IR path** — it does not contradict the "same IR to both
outputs" rule, which is about the *cabinet* convolution inside the amp model.

#### From the other release notes

`GSP1101 RELEASE NOTES VERSION C25.txt` and `Release Notes Version-final C36.txt`
cover noise-gate, amp-model, MIDI, routing and preset-control changes — they
contain **nothing about user cabs or impulse responses**, which brackets the
feature to C54+.

### 13.10 The corrected DSP model (2026-11-11 re-verification)

A second, targeted re-verification of every load-bearing claim (script:
`04_analysis_scripts/audit_claims.py`, 111/111) changed the **shape of the port**
— not the gate. The findings:

**1. The RP500's DSP payload is a 24-byte parameter descriptor.**

| Fact | Value | Where |
|---|---|---|
| code-sourced stores to the DSP data port `0xD070` | **exactly 2** | bank 14 `0x9ABA`, bank 15 `0xBEAC` |
| source of both | **code space** (`MOVC A,@A+DPTR`) | `0x9AB6`, `0xBEA8` |
| block contents | `c9 12 12 34 12 10 00 09 01 01 0c 50 0a 20 01 00 12 ab 02 0a ed 02 00 1f` | `0x2DC2` / `0x2E3B` |
| the two blocks | **byte-for-byte identical** | — |
| what follows the block | **code** (`E6` = `MOV A,@R0`, head of the next function) | `0x2DDA` / `0x2E53` |
| byte counter | 16-bit XRAM `0xFF24`/`0xFF25`; `DPTR = base + counter` | `0xBE97` |
| **length limit** | **none** — the `0x7FF8` compare is a *stall abort* on the "status did not change" path | `0xBE2D`/`0xBE3D` |
| **measured** | **118 650 bytes** pushed at `0xD070` with an always-acknowledging DSP; the first 24 are the descriptor, the rest is code | `05_evidence/2026-11-11_ucsim_dspstream_long.md` |

⇒ The payload is a **DSP parameter descriptor**, and the factory cabinets are
**parametric DSP models**, not impulse responses: a strict 128-tap
coefficient-block scan finds **zero** blocks in the RP500, GSP C48, GSP C63 and
GSP V20. An IR is exclusively the **user-cabinet feature**, which the GSP1101
*added* in firmware C54 — so the RP500's host has never asked its DSP for one.
The RP500 manual never mentions impulse responses.

**1b. A third write path into the DSP window.** A **113-byte DSP
configuration block** — bank 14 at `0x2C80`, bank 15 at `0x2CBB`, **identical**
in both — is copied one byte at a time into DSP registers `0xD000`–`0xD070`,
skipping `0xD059` (`bank 15 0xB86A`–`0xB8A0`). Its last byte (index `0x70`)
lands on `0xD070`. So `0xD070` is written by **two** mechanisms: the sequential
descriptor stream and this byte-wise configuration copy. Neither carries
cabinet-specific IR data — both blocks are identical across the two cabinet
banks.

**2. The GSP1101 has a second, variable-length DSP path — and that is where
the user IR lives.**

| Fact | C48 | C63 |
|---|---|---|
| XRAM-sourced stores to `0xD070` | **32** = **2 handlers × 16 code banks** (one stream, not two chips) | **32** |
| source base | `0x2445 + index` | `0x2603 + index` |
| index cell | XRAM `0x233F` | XRAM `0x24FD` |
| length cell | XRAM `0x2546` | XRAM `0x2704` |
| terminator | `0xF5` written to `0xD070` | same |
| IR staging | — | XRAM `0x1483+` → XRAM `0x2603+`, count in XRAM `0x14C3` (routine at bank 15 `0xD7D1`) |
| code-space block | 16 bytes at `0x31F3`/`0x3666` | same |

> **Correction (2026-11-12):** the 32 XRAM sites are the **same two interrupt
> handlers replicated across the 16 code banks**, not two chips. Both handlers
> read the same source base and write the same `0xD070` port; neither touches
> `0xE200`, `0xE400`, or any other chip-select register. The transport is
> already present in the oldest build (v11, cells `0x2164`/`0x1F5D`/`0x2B4F`,
> source `0x2063+index`), so C48/C63 added the host-side feature, not the DSP
> path. The only GSP-only two-select access is `0xE400` ← `0x40`/`0x80` +
> read `0xEC40`, a status/ID path, not the IR path. See
> `05_evidence/2026-11-12_gsp_two_chip_test.md`.

The GSP's 16-byte code-space block **shares 8 bytes** with the RP500's 24-byte
descriptor (`01 01 0c 50 0a 20 01 00`) — same platform routine, different
parameter descriptor.

**3. What follows.**

- The RP500 has **no** variable-length DSP path. The GSP's user-cab feature
  does not run on the RP500's existing stream; it runs on a path the RP500
  never uses.
- Therefore **§13.8's "source swap" is wrong**. The port must **add** a
  GSP-style terminated XRAM stream (≈80 bytes of stub in the `0x5FD0` free
  run) and stage the record into the XRAM block it reads.
- **The gate is unchanged but sharper:** can the RP500's AudioDNA2 be put into
  the mode where it accepts a variable-length block? And can it **render** it?
  Because there are **no factory IRs** (§12.3), the factory cabinets are
  parametric models and a user IR is a *different kind of data* — so the
  question is not "can it take a longer block" but "does it have a convolution
  path at all". Evidence for "yes": the RP500 and the GSP share **23
  host/DSP addresses**, including the complete handshake set — the 13
  DSP-window registers `0xD01E/1F/20, 0xD034, 0xD050, 0xD05A/5B, 0xD066/69/6D/6E/6F,
  0xD070` and the command ports `0xE000/0xE200/0xE400/0xE800` — i.e. the same
  host interface on the same chip family, and the GSP1101 convolves with user
  IRs. Evidence for "not yet proven": the RP500 firmware never exercises that
  path, so the capability cannot be read off the image — it has to be
  **measured** (roadmap S3).
- Two further open questions fall out of the model: whether the GSP streams
  the whole 2048-byte record or only its 512-byte coefficient part, and what
  the RP500's 148 DSP register writes per bank actually configure.

---

## 14. The sibling firmwares: what the other AudioDNA2 products prove

The updater bundle carries **27 firmware images** for ten DigiTech products.
Six of them are siblings of the RP500 — three **RP1000** (1 MB, same shape) and
three **RP355** (720 KB, 11 banks) — and two more are the **GSP1101** pair we
already had. All of them are now unpacked into `01_source_firmware/`
(`rp1000V10/V11/V12.bin`, `rp355V11/V13/V14.bin`) and surveyed with
`04_analysis_scripts/platform_survey.py`.

### 14.1 The RP1000 runs the RP500's coefficient loader verbatim

| Unit | Banks | Coefficient-stream source bases | P1 bank table |
|---|---|---|---|
| **RP500 v2.0** | 16 | bank 14 `0x2DC2`, bank 15 `0x2E3B` | in **all 16** banks (identical 0x2C80 prefix) |
| **RP1000 V12** | 16 | bank 14 **`0x2DC2`**, bank 15 **`0x2E3B`** | in 1 of 16 banks |
| **RP355 V14** | 11 | bank 9 `0x2D02`, bank 10 `0x5114` | in 1 of 11 banks |
| **GSP C48** | 16 | bank 14 `0x31E3`, bank 15 `0x35F5` | in 1 of 16 banks |
| **GSP C63** | 16 | bank 14 `0x31F3`, bank 15 `0x3666` | in 1 of 16 banks |

The RP1000's stream code is **the same routine** as the RP500's — same source
bases, same ports, same structure, and byte-for-byte identical *except* for
the scratch cell the byte counter lives in (`MOV DPTR,#0FFAAh` on the RP1000
vs `#0FF24h` on the RP500; the counter pair is `0xFFAA/0xFFAB` vs
`0xFF24/0xFF25`). So the coefficient loader is a **shared AudioDNA2
platform routine**, copied between products and re-based on the local scratch
addresses. Two consequences:

- The change we plan is a **platform** patch, not an RP500 quirk.
- The RP1000 is a second, larger target for the same patch (and its free-flash
  run is `0x5DF0`, comparable to the RP500's `0x5FD0`).

The RP500 is also the odd one out in *banking*: it replicates an identical
0x2C80-byte prefix (reset vector, dispatcher, P1 table) into **every** bank,
while the RP1000/RP355/GSP carry the common code in one bank only. That
difference is what made the RP500's bank map so easy to read.

### 14.2 The decisive one: the GSP streams coefficients out of XRAM

Counting coefficient stores to the DSP data port `0xD070` by where the byte
came from:

| Unit | code-space streams | **XRAM-sourced streams** |
|---|---|---|
| RP500 v2.0 | 2 | **0** |
| RP1000 V12 | 2 | **0** |
| RP355 V14 | 2 | **0** |
| GSP C48 | 2 | **32** |
| GSP C63 | 2 | **32** |

The GSP has, in **every bank, two coefficient streams that read the byte from
external RAM** rather than from code space. Example, GSP C63 bank 0 `0x2F49`:

```
2F44  ADDC  A,#26h        ; DPTR = 0x2603 + counter
2F46  MOV   83h,A
2F48  MOVX  A,@DPTR       ; read the coefficient byte from XRAM
2F49  MOV   DPTR,#0D070h
2F4C  MOVX  @DPTR,A       ; hand it to the DSP
```

**This is the key result.** The AudioDNA2 DSP accepts coefficients delivered
from XRAM just as happily as from code space — the GSP1101 (the platform that
*has* user cabs) does exactly that, with 32 such streams, and has done so since
before the IR feature (C48 has them too). The RP-series never does it: its
loader is hard-wired to `MOVC` out of code space.

### 14.2a The loader predates the IR feature (2026-11-11)

A differential of C48 (no user cabs) against C63 (the IR build) settles what
the IR update actually changed, and it is clean:

| Loader part | C48 (pre-IR) | C63 (IR build) | RP500 |
|---|---|---|---|
| receive buffer | `0x1483` | `0x1483` | — |
| source index | `0x14C5` (×4) | `0x14C5` (×4) | — |
| byte count | `0x14C3` (×7) | `0x14C3` (×7) | — |
| destination index / length | `0x2546` (×69) / `0x2547` (×79) | `0x2704` (×69) | — |
| block base | `0x2445` | `0x2603` | — |
| stream sites | 32 | 32 | **0** |
| factory code-space descriptor | `01 01 0c 50 0a 20 01 00 14 bd 02 0b 46 02 14 b0` | **identical** | different (24 bytes) |

The reference counts are **identical**; the cells are merely relocated because
C63 is a rebuild. So:

> **C63 added no transport, no DSP command and no loader code.** It added the
> cab-list surface (`USER 1..10`) and pointed the existing generic loader at the
> received IR. The pre-IR build already received a block at `0x1483` and
> shipped it to the DSP — i.e. the channel is a **generic host→DSP block
> loader**, not an IR-specific one.

Two consequences for the port:

- It **weakens the "the DSP needs an IR mode" hypothesis**: a mode would have
  had to be added by C63, and C63 added nothing on the DSP side.
- It tells us **what to port**: not just a terminator, but the whole loader
  (receive buffer + index + count + block base + stream). The RP500 has none of
  it — zero references to any loader cell.

It does **not** answer the DSP question: the RP500's DSP is configured by the
RP500's own firmware, and only the hardware can say whether it accepts a block.

### 14.2b Could C48 be a *partial* IR update? No — the loader is as old as v1.1

The archive holds **seven** GSP1101 builds, so the question "did the loader
arrive gradually, or did C48 contain work in progress?" can be answered from
the series rather than assumed:

| build | code-space streams | **XRAM streams** | `USER n` cab names | `USER_CAB` string |
|---|---|---|---|---|
| v1.1 (official) | 2 | **32** | 0 | yes |
| v1.2 (official) | 2 | **32** | 0 | yes |
| v1.3 (official) | 2 | **32** | 0 | yes |
| v2.0 (official) | 2 | **32** | 0 | yes |
| C20 (unofficial) | 2 | **32** | 0 | yes |
| C48 (unofficial, pre-IR) | 2 | **32** | 0 | yes |
| **C63 (IR build)** | 2 | **32** | **10** | yes |
| RP500 v2.0 | 2 | **0** | 0 | no |

So:

- The loader is present in **every** GSP1101 build, back to the oldest official
  firmware we have. It is **not** IR work in progress — it is platform code.
- The feature arrived in **one step**: only C63 has the `USER 1..10` names.
- The `USER_CAB` string exists in **v1.1** as well, so its presence in C48 was
  never evidence of "part of the work done" — it is shared platform vocabulary.

The RP500 is the outlier: **zero** XRAM streams. It is the same platform with
that facility never implemented on the host side.

> **Correction (2026-11-11, §13.10).** The conclusion drawn here — "so the RP500
> port is precisely: change the loader from `MOVC` to `MOVX`" — **does not
> follow**. The GSP's XRAM streams are a *separate, variable-length,
> `0xF5`-terminated* mechanism, not a re-sourced version of the RP500's
> code-space stream. The RP500's code-space stream carries a **24-byte
> parameter descriptor** (identical in both banks, followed by code), so
> re-pointing its source cannot deliver a user IR.
>
> The correct reading of this table: the RP500's DSP **can** be fed from XRAM —
> that capability is proven *by the GSP on the same chip family* — but the
> RP500's firmware has no such path, so one must be **added** (≈80 bytes of
> stub: length-bounded pull + `0xF5` terminator), together with the XRAM
> staging step. The open question S2 (where the record is stored) is **not**
> removed from the critical path: the receiver can write XRAM directly, but the
> record must also *persist* across power cycles, which needs the user-data
> store.

### 14.3 What the siblings are worth, in one line each

| Firmware | Value |
|---|---|
| RP1000 ×3 | proof that the loader is platform code (identical bases); a second target; a *different* banking scheme to compare against |
| RP355 ×3 | a third platform layout (11 banks), same loader family |
| GSP C48 vs C63 | the IR feature in a platform that **already** had XRAM-sourced streams — i.e. the feature did not invent a new DSP path, it reused one |
| RP150/155/250/255/350/BP355 | smaller products; more instances of the same platform code for cross-referencing |

---

## Appendix B: Hardware Test Results (Physical RP500)

Test performed on a physical DigiTech RP500 connected via USB-MIDI to a Linux host. Device identified as `DigiTech RP500:DigiTech RP500 MIDI 1`.

### Device Connection

| Item | Value |
|------|-------|
| Connection | USB-MIDI (ALSA raw MIDI) |
| Device port | ALSA card 2, device 0, subdevice 0 (`hw:2,0,0`) |
| gdigi | Successfully built and ran; unit controllable via its UI |
| Device detection | Confirmed via `lsusb`, `amidi -l`, `aconnect -l` |

### Cabinet Index Range — Empirical Testing

Cabinet type parameter `AMP_CAB_TYPE` (ID **2560**, position **9**, channel A) was probed via SysEx `get_option`/`set_option`.

| Value Range | Result | Notes |
|-------------|--------|-------|
| 570–585 | ✅ Accepted | Factory range. All values accepted; display names confirmed (Direct, Champ® 1x8, Deluxe® 1x12, Twin 2x12, Blonde 2x12, Bassman 4x10, Boutique 4x12, Fane 4x12, DigiTech® Spkr Comp, and others) |
| 586–626 | ✅ Accepted | Extended range. All values accepted; display names confirmed (DigiTech® Spank 2x12, DigiTech® Solo 4x12, DigiTech® Bright 2x12, DigiTech® Chunk 4x12, British 2x12, British 4x12, British Green 4x12, DigiTech® Metal 4x12, DigiTech® Rock 4x12, DigiTech® Alt 4x12, DigiTech® Vintage 4x12, Vintage 4x12, British 1x12, GA 1x12, Recto 4x12, Jazz 2x12) |
| 627 | ❓ Not confirmed | Listed as `JBL 2x15` in gdigi.h (shared multi-product enum) but does not correspond to any cabinet on this RP500 unit |

**Conclusion:** The RP500 DSP accepts cabinet parameter values beyond the factory UI range of 585, up to at least 626. The factory limit of 585 is a UI constraint, not a DSP constraint.

### Custom IR Record — Encoding and Transmission

A custom cabinet impulse response was encoded and transmitted:

| Item | Value |
|------|-------|
| Source WAV | `IR/MesaV3022.wav` — 44.1 kHz, PCM, mono, 24-bit, 208 samples |
| Encoder | `usercab_encode.py` (C59/Jcabinet reimplementation) |
| Output record | 2048 bytes (`0x800`) |
| Slot | 1 |
| Gain | 0 dB |
| Taps | 208 |
| Transport | USB-MIDI SysEx (`F0` + payload + `F7`) |
| Transmission result | ✅ Message sent successfully (no transmission error) |
| DSP acceptance | ❓ **Unconfirmed** — no observable audio change, display update, or confirmation received |
| User cab UI slot | ❌ None exists in factory firmware; no way to select or activate the transmitted record |

### Key Findings from Hardware Testing

1. **DSP accepts extended cabinet indices** — Values 586–626 were accepted and produced expected cabinet names. The DSP is not hard-limited to 585.

2. **SysEx transport works** — The RP500 receives and responds to SysEx parameter messages. `RECEIVE_PARAMETER_VALUE` responses were observed for valid factory/extended cabinet indices.

3. **No user cab subsystem in factory firmware** — The RP500 has no `USER 1`–`USER 10` strings, no `USER_CAB %D` handler, no `CAB_EN_XLR_LPF` parameter, and no UI menu for user cab slots. A transmitted 2048-byte custom IR record has no activation path. *(Note 2026-11-11: the RP500 does have a **preset** service with numeric IDs — `MOVE_PRESET` 0x39, `RECEIVE_PRESET_PARAMETERS` 0x2D — which gdigi drives; what it lacks is the GSP's text-named `USER_CAB` machinery. See `rp500_preset_protocol.md`.)*

4. **gdigi.h enum values are not all valid on RP500** — Value 627 (`JBL 2x15` in gdigi.h shared enum) does not exist on this RP500 unit. gdigi supports multiple DigiTech products; not all enum values apply to every model.

### Firmware Flash Verification (2026-11-10)

A physical RP500 was flashed with a patched image using the bundled updater, end to end.

| Item | Value |
|------|-------|
| Updater | `09_builds/updater_2.1/Digitech.RP.Series.Firmware.Updater.exe` (NetUpdaterClone bundle, RP500 revision **2.1**) |
| Image | `09_builds/rp500_v20_caio4x12.DigBin` — cab 24 `DIGISPKR` → `CAIO4X12`, 8 bytes changed |
| Dry run | 23:41:46–23:42:26 — handshake OK, flash map `maxBlock=256`, 16 segments × 64 KB, `Data to write: 1048576 bytes (image bytes: 1048576)`, no writes |
| Real write | 23:44:39 identify (`Version OK: "2.0"`), 23:44:46–23:51:49 write (**7 m 03 s**) |
| Blocks | **4,039** `0x7A` data blocks (4,038 unique + 1 retry), 4,040 `0x7E` ACKs |
| Errors | 1 NAK (`0x0C`) at address `0x0F0000`, retried and acknowledged |
| Safety stops | none |
| Result | Unit boots normally; cab list last entry reads **CAIO4X12**; presets and audio unchanged; X-Edit display unchanged (see below) |

Evidence: `05_evidence/2026-11-10_rp500_updater_flash.log` (both runs, 12,437 lines).

**Updater quirk found while auditing the log.** The 0xFF skip in `MidiTargetDevice.PerformUpdate` is

```csharp
if (!array.All(b => b == byte.MaxValue) || num6 <= num5) SendDataBlock(...);
```

`num6 <= num5` (segment size ≤ segment start) is true for every segment except segment 0, so the
all-`0xFF` optimisation only applies to bank 0. Measured against the image: bank 0 has 58 all-`0xFF`
blocks (all skipped), banks 1–15 have 548 (all written). That is exactly the 4,038 unique blocks in
the log. Writing `0xFF` to erased flash is a no-op, so it is harmless — but it costs ~15 % extra
traffic, and it explains the 7-minute write. Not fixed here; the stock updater behaves the same way.

**X-Edit behaviour.** X-Edit shows **no change** — it still displays the factory name for cab 24.
So the editor resolves cab names from its **own** table, not from the device. Two consequences:

- The device cab menu is the authoritative display for firmware-side name changes; X-Edit will
  not reflect them.
- Any future `USER 1`–`USER 10` entries added to the firmware will likewise be invisible to a
  stock X-Edit. Making them visible would require patching the editor as well, which is out of
  scope for the firmware work.

This is consistent with the factory cab-name strings being absent from `Hmg.Devices.dll` (only
`User Cab 1`–`User Cab 10` are present there): the editor's copy lives elsewhere in the editor
installation.

### Key Findings from Hardware Testing (continued)

5. **The firmware flash path is verified end to end.** A patched `.DigBin` bundled into the updater
   as revision 2.1 flashes cleanly, the device declares a flash map that exactly covers the image,
   and the unit boots with the changed string. The container model, the updater integration and the
   flash path are all confirmed on hardware. The *bootloader fallback* is **not** confirmed on
   hardware — it is reported by the uploader author and will be analysed statically rather than
   tested with a deliberately broken flash.