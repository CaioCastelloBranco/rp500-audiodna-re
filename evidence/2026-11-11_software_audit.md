# Software audit of the user-cab hypothesis — 2026-11-11

**Scope.** Re-check every structural claim the S3b/port plan rests on, using
the shipped host tools as independent evidence: the official X-Edit payload,
the GSP X-Edit C46/C63 builds, `JUserCabUpdater vC59.exe`, the modern RP-series
updater **and its captured flash log**, and gdigi. Firmware: RP500 v2.0,
RP1000 V10–V12, RP355 V11/V13/V14, GSP v1.1–v2.0/C20/C48/C63.

**Rule.** No hardware was touched for this audit. Every claim below is
reproduced by `04_analysis_scripts/audit_software_probe.py` (**31/31 PASS**).

---

## 1. What the cab loader actually does

`JUserCabUpdater vC59.exe` is a **native JUCE/MIDI** application, not .NET.
Disassembly of its WAV path (`0x4070C0`–`0x407B60`) gives the exact recipe:

| Property | Value | Evidence |
|---|---|---|
| Input | RIFF/WAVE, PCM, **44.1 kHz**, mono or stereo, 8/16/24/32-bit | strings + checks at `0x4071B4`–`0x4074DC` |
| Taps | **128** normally; **208** when the option flag is set | `cmp ebx,0x80` @ `0x4075BB`; `cmp ebx,0xD0` @ `0x4075CA` |
| Tap format | **32-bit big-endian** (four bytes per tap) | packer @ `0x407754`–`0x407796` |
| Record | **2048 bytes** = 2023-byte data area + **23-byte `USER n` name** + **2-byte trailer** | pad `0x7E7` @ `0x4077CA`; append `0x17` @ `0x40792D`; append `2` @ `0x4079B9` |
| Trailer | `<cabIdx> <flag>`; the commit reads it at `slotBase+0x7FE` | report §11.6 + the record layout |
| Mode | **temporary (audition)** vs **store** | UI strings: *"Store cabinet to GSP1101 else it will be a temporary cabinet"* |

The loader warns that interrupting a store requires a **factory reset** and
loses user presets. So the feature has an explicit **volatile** mode as well as
a persistent one. That matters: a safe RP500 experiment does not need the
persistent path at all.

**Slots:** 10 × 0x800 = 20 KB, matching the GSP user-data window
`0x50000`–`0x54FFF`. That window is **not** a hole in the 1 MB firmware image
(bank 5 contains code at those offsets); it is a **separate store** addressed
by the cab tool.

---

## 2. The feature is ten table rows, not a new protocol

| Image | Table | Result |
|---|---|---|
| RP500 v2.0 | bank 7 `0x519F`, **28** BE16 entries | 25 speaker models + `DIRECT` + `DREAD AC` + `JUMBO AC` (IDs `607`,`606`) |
| GSP C63 | flat `0x95CFC`, **38** entries | the same 28, with **10 user IDs** (`596`–`604`, `736`) inserted after `DIRECT` |
| GSP C48 / RP1000 / RP355 | — | no `USER 1`/`USER 10` names |

X-Edit agrees: `CabType_1 = 2560`; user cabs are **values** of the same
parameter, not a new parameter. The C46→C63 delta is exactly ten table rows
plus one parameter (`2510`). There is no new editor class, transport or
encoder.

**Correction:** the RP500's 28th/27th entries are **not** hidden user slots.
They are the two acoustic cabs, which X-Edit simply does not list. The device
menu is authoritative, as observed.

---

## 3. The transport is the RP500's own Super7 SysEx

`F0 00 00 10 <device> <family> <product> <cmd> <7-bit-packed payload> <chk> F7`,
with `chk = XOR(all bytes after F0, excluding chk and F7) & 0x7F`.

Verified against all ten short messages in the captured update log
(`0x01` identity, `0x08` version, `0x78` flash map, `0x7A` blocks, `0x7B` end).

The RP500 **does** speak it: its own updater completed a full 1 MB write. The
`0x7A` body is:

```
<addr32 BE> <len16 BE> <packed data>
```

Block 0 decodes to `addr=0x000000`, `len=0x0100`, and the first 256 bytes of
`rp500_v20.bin` **exactly**. The log has **4039** `0x7A` frames; the device
declared **16 × 64 KB** segments and the update wrote **1048576** bytes.

The GSP cab tool uses the same `0x7A`, but against the **user-data window**
(`0x50000`–`0x54FFF`), and a `0x73` commit. The RP500 updater uses `0x7A`
against the **firmware flash** and a `0x7B` end. **Same opcode, different
address space/mode.**

---

## 4. The DSP picture is unchanged

Exact instruction patterns (`MOVX A,@DPTR; MOV DPTR,#0D070h; MOVX @DPTR,A`
and the `MOVC` equivalent):

| Image | code-space streams | XRAM-sourced streams |
|---|---|---|
| RP500 v2.0 | 2 | **0** |
| RP1000 V12 | 2 | **0** |
| RP355 V14 | 2 | **0** |
| GSP C48 | 2 | **32** |
| GSP C63 | 2 | **32** |

The "32" is **two sites in each of the 16 banks** — one replicated routine,
not 32 model streams. C48 already has it, so C63 added **no DSP primitive**.

The two 113-byte tables (bank 14 `0x2C80`, bank 15 `0x2CBB`) are
**byte-identical**, as are the two 24-byte descriptors. They are **not**
per-model cab data; the cab selection is elsewhere.

**No factory IRs**, re-checked at the loader's real width (32-bit taps,
128/208): **0** candidates in RP500, C48, C63 and V20. The earlier scan used
16-bit taps — the right conclusion for the wrong reason.

---

## 5. Corrections to the archive

| Earlier statement | Now |
|---|---|
| "per-cabinet parameter table" (113 B) | **identical** in both banks; not cab-specific |
| "`0x2D` = count + `<id><pos><value>`" | gdigi's wire format is correct, but the firmware handler at bank 7 `0x8BCD` reads a **4-byte header** and dispatches on a type byte; the value path is **not yet traced** |
| "the RP500's `0x7A` is the transport for a user IR" | it is the **firmware-flash** block write; the GSP's `0x7A` targets a **separate user-data store** |
| "128-tap scan finds no factory IRs" | correct result; the scan was **16-bit**, the loader is **32-bit** |
| "32 XRAM streams" | 32 **sites** = one replicated routine × 16 banks |

The archive's **storage** conclusion still holds: the RP500's firmware flash is
1 MB and fully written; there is no spare window. The leading candidate for
presets (and therefore for an IR record) remains a **serial store**, which the
XDATA map cannot see.

---

## 6. What this changes for S3b

- **Host half is not the blocker.** The RP500 speaks the same Super7 transport
  the GSP cab tool uses, and the record format is fully known.
- **Storage is not needed for the experiment.** S3a already sends 512 bytes +
  `0xF5` from a code-space table; no flash and no XRAM are required.
- **The blocker is the cab trigger.** The best handle is the cab parameter
  `CabType_1 = 2560` (`0x0A00`), value `608` for cab 24. The next safe step is
  **simulator-only**: boot the existing uCsim harness with two different cab
  values and diff the DSP writes. If nothing changes, trace the `0x2D`
  handler's value path (the `StoreParam`-style call at `0xB8DA`).
- **The DSP gate is unchanged:** does the RP500's AudioDNA2 render a 512-byte
  coefficient block? Nothing static answers it.

---

## 7. Reproduce

```
python 04_analysis_scripts/audit_software_probe.py
AUDIT RESULT: 31/31 checks passed
```
