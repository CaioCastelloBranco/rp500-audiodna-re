# The two-chip test — does the GSP1101 firmware address its AudioDNA2 pair independently?

**Date:** 2026-11-12
**Method:** static only. No hardware, nothing flashed.
**Question under test (user hypothesis):** the GSP1101 has two AudioDNA2 chips;
perhaps only one of them carries the convolution instructions, and that chip is
unique to the GSP.

**Script:** `04_analysis_scripts/two_chip_test.py` (reproduces every number below).
**Images:** `gsp1101_v11.bin` (oldest), `gsp1101_v20.bin`, `c48_fw.bin`,
`c63_fw.bin` (IR build), `rp500_v20.bin`. C48/C63 offsets are bank-body offsets
after `payload16()` extraction.

---

## 1. The "32 XRAM sites" are **2 handlers × 16 code banks**, not two chips

Every GSP build has exactly 34 stores to the DSP data port `0xD070`:

| Build | total `0xD070` stores | code-space | XRAM-sourced | XRAM banks |
|---|---|---|---|---|
| GSP v11 (oldest) | 34 | 2 | **32** | 0–15 (all 16) |
| GSP v20 | 34 | 2 | **32** | 0–15 (all 16) |
| GSP C48 | 34 | 2 | **32** | 0–15 (all 16) |
| GSP C63 (IR) | 34 | 2 | **32** | 0–15 (all 16) |
| RP500 v20 | **2** | 2 | **0** | — |

The 32 XRAM stores are the **same two interrupt handlers replicated once per
64 KB code bank**: 2 handlers × 16 banks = 32. This is a property of the 8051's
banked code space, not evidence of two DSPs.

## 2. Both handlers serve **one** stream, on **one** port

In C63, the two handlers are at bank 0 `0x2F10` and `0x3070`. Both reference the
**same** XRAM cells and the **same** source base:

| Handler | length cell | index cell | ack/aux cell | command cell | source base |
|---|---|---|---|---|---|
| `b0:2F10` | `0x2704` | `0x24FD` | `0x2705` | `0x327A` | `0x2603 + index` |
| `b0:3070` | `0x2705` | `0x24FD` | `0x2704` | — | `0x2603 + index` |

Both write bytes to `0xD070` and terminate with `0xF5`. Neither touches
`0xE200`, `0xE400`, or any other candidate chip-select port.

## 3. The oldest build already has the **same transport** — different addresses

| Build | handler | length | index | command | source base |
|---|---|---|---|---|---|
| v11 | `b0:26A0` | `0x2164` | `0x1F5D` | `0x2B4F` | `0x2063 + index` |
| v20 | — | `0x2164` | `0x1F5D` | `0x2B4F` | `0x2063 + index` |
| C63 | `b0:2F10` | `0x2704` | `0x24FD` | `0x327A` | `0x2603 + index` |

The instruction structure is identical; only the XRAM scratch addresses moved
when the program was recompiled. **The variable-length, `0xF5`-terminated,
XRAM-sourced DSP stream therefore predates the user-cab feature by years.**
C48/C63 did not add the transport; they added the host-side feature that uses
it.

## 4. Chip-select candidates

| Image | `0xFDFC` refs | `0xE400` refs | `0xEC40` refs | `0xE200` refs |
|---|---|---|---|---|
| GSP v11 | **0** | 27 | 5 | 24 |
| GSP v20 | **0** | 27 | 5 | 24 |
| GSP C48 | **0** | 28 | 5 | 24 |
| GSP C63 | **0** | 27 | 5 | 24 |
| RP500 v20 | **49** | 4 | **0** | 11 |

- `0xFDFC` is **RP500-only**. The earlier claim (doc §13.3) that the GSP
  selects its second chip "through the command byte staged in `0xFDFC`" is
  **false** and has been corrected.
- `0xE400` takes three immediate values in every GSP build — `0x01`, `0x40`,
  `0x80` — and **never** in the RP500.
- `0xEC40` is read **only** in the GSP, and always paired with `0xE400` set to
  `0x40` then `0x80`:

```
E400 <- 0x40 ; A <- EC40 ; A &= 0xF0 ; store high nibble
E400 <- 0x80 ; A <- EC40 ; A &= 0xF0 ; OR with (high nibble >> 4)
E400 <- 0x00
```

This is the only **GSP-only two-select access** in either firmware. It is a
status/ID read (the value is compared against a stored copy and a flag at
`0x2C.6` is tested), **not** the user-IR path. It is the best static candidate
for a two-device select, but it is not used to route IR data.

## 5. The IR handler does not select a chip

Within the two C63 IR handlers:

| Port | occurrences |
|---|---|
| `0xD070` (data) | 5 |
| `0xE000` (command) | 1 — only the `|0x80` / `|0x40` flow-control command |
| `0xE200` | **0** |
| `0xE400` | **0** |

The command byte is staged in XRAM `0x327A` and only has bits `0x40`/`0x80`
set/cleared around it. Those are transfer handshake bits, not a chip field.

## 6. Hardware — the parts list answers the chip-identity question

The RP500 board photograph
(`05_evidence/board/02_dsp_audioDNA2_sdram_flash.jpg`) shows **one** AudioDNA2
(U25, marked `72-1002 GREEN / 7169170 / 1012 KOREA`), one SDRAM (U24, Samsung
`K4S641632N-LC75`), and one firmware flash (U26). There is no second DSP
footprint.

The GSP1101 parts list (`03_docs/GSP1101 parts list.docx`, 08/31/2007) lists:

| Qty | Part | Description |
|---|---|---|
| **2** | **`72-1002`** | **IC Audio DNA2 Rev B ASIC 144 pin LQFP** |
| 2 | `72-0099` | IC 64 Mbit SDRAM 4Mbx16 7.5 ns TSOP-54 |
| 1 | `72-0175-00V1` | IC CPLD EPM3032A TQFP44 |
| 1 | `72-0089-06V1` | IC 16 Mbit 3.3 V flash, "GSP1101 OS" |

So the GSP's two chips are **2 × `72-1002`** — the **same base part** as the
RP500's single U25. The GSP is two complete DSP + SDRAM subsystems; the RP500 is
one. The EPM3032A CPLD is the likely address-decode / chip-select that lets one
8051 drive two DSPs without an explicit DSP-id byte. See
`05_evidence/2026-11-12_gsp1101_parts_list.md`.

---

## What this establishes

1. **The GSP1101 firmware does not address two DSPs independently.** Both IR
   handlers read the same XRAM stream and write the same `0xD070` port. There is
   no chip-select in the IR path.
2. **The transport predates user cabs.** The oldest GSP build (v11) already
   contains the identical variable-length stream, with only the scratch
   addresses changed. C48/C63 added the host-side feature, not the DSP path.
3. **`0xFDFC` is not a GSP chip-select.** It is RP500-only; doc §13.3 was wrong.
4. **The only GSP-only two-select path is `0xE400`/`0xEC40`, and it is a
   status/ID read, not the IR path.**
5. **The GSP's two chips are the same `72-1002` ASIC as the RP500's single
   chip** (GSP parts list: qty 2, "IC Audio DNA2 Rev B ASIC 144 pin LQFP";
   RP500 U25: `72-1002 GREEN`). The "only one chip, unique to this product, has
   the convolution instructions" hypothesis is **refuted at the part-number
   level**: there is no GSP-only AudioDNA2 variant.

## What this does **not** establish

- The **DSP microcode** is still not in any artifact. The same ASIC can run
  different microcode, and the firmware image does not contain (or clearly
  load) a convolution program.
- Whether the **EPM3032A CPLD** routes `0xD070` to one DSP, both, or a selected
  one. That is in the schematic / CPLD netlist, not the BOM.
- Whether the RP500's **`72-1002 GREEN`** is the same silicon revision as the
  GSP's **`72-1002 Rev B`**. The part number is identical; a revision difference
  would not normally *remove* an instruction.

## The hypothesis, now

The chip-identity half is settled: **the GSP's two DSPs are the same ASIC part
as the RP500's one DSP.** The remaining half is microcode / enablement, and the
firmware is consistent with either:

- **Both GSP chips run the same convolution-capable microcode** (IR broadcast /
  per-output routing), or
- **The second chip is extra capacity** for amp/effects, with the same
  instruction set.

Because the ASIC part is identical, the RP500's single chip has the same
*hardware* potential. The open question is whether its firmware can load or
activate a convolution program — not whether it has a different, convolution-less
chip.

The C63 release notes still add the useful fact that user cabs "don't come out
the XLR outputs unless you have the option turned on" — a per-output routing
choice, consistent with either mapping.

## What would settle the rest

1. The **AudioDNA2 microcode / ISA** (not present in any artifact) — the decisive
   unknown.
2. A **logic-analyzer capture** of the GSP host↔DSP bus during a user-cab load,
   to see whether `0xD070` traffic reaches one chip or both and what the CPLD
   does.
3. The **GSP1101 schematic / CPLD netlist**, to see how the EPM3032A maps the two
   DSPs.

Until then, the correct statement is: **the RP500 port's gate is unchanged and
narrower — "not demonstrated," not "impossible."** The parts list removes the
chip-variant doubt; the microcode doubt remains.
