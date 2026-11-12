# DSP-facing block comparison — RP500 vs GSP1101 (V20 / C48 / C63)

**Date:** 2026-11-12
**Method:** static only. No hardware, nothing flashed.
**Images:**

| Image | Size | SHA-256 (first 16) |
|---|---|---|
| `rp500_v20.bin` | 1,048,576 | `718fda7de9206838` |
| `gsp1101_v20.bin` | 1,048,576 | `1cd3f72cb9fa4699` |
| `c48_fw.bin` | 1,048,704 (16 × 0x10008) | `93ac1e46d15db32f` |
| `c63_fw.bin` | 1,048,704 (16 × 0x10008) | `303ff25336cf7951` |

C48/C63 are the interleaved-descriptor container; all offsets below are **bank-body
offsets after `payload16()` extraction** (`img[k*0x10008+8 : k*0x10008+0x10008]`).

Scripts: `04_analysis_scripts/compare_blocks_final.py`, `compare_gsp_stream.py`,
`find_init_block.py`.

---

## 1. The code-space stream routine is instruction-identical

All four images contain the same loop. Only the constants differ:

```
MOV DPTR,#<counter>      ; XRAM 16-bit byte counter
MOVX A,@DPTR
MOV R6,A
INC DPTR
MOVX A,@DPTR
ADD  A,#<lo>             ; source base low
MOV  DPL,A
MOV  A,#<hi>             ; source base high
ADDC A,R6
MOV  DPH,A
CLR  A
MOVC A,@A+DPTR           ; byte from code space
MOV  DPTR,#D070
MOVX @DPTR,A             ; -> DSP data port
```

| Image | site (bank:addr) | counter XRAM | source base |
|---|---|---|---|
| RP500 | 14:0x9AA5 | `0xFF24/25` | `0x2DC2` |
| RP500 | 15:0xBE97 | `0xFF24/25` | `0x2E3B` |
| V20 | 14:0x717D | `0x2086/87` | `0x317D` |
| V20 | 15:0xD1BD | `0x2086/87` | `0x3588` |
| C48 | 14:0xDAE3 | `0x2443/44` | `0x31E3` |
| C48 | 15:0xD2C5 | `0x2443/44` | `0x35F5` |
| C63 | 14:0xDB3C | `0x2443/44` | `0x31F3` |
| C63 | 15:0xD5C1 | `0x2443/44` | `0x3666` |

The two sites per image are duplicates (same code, shifted address), as §13.3
already established.

## 2. The XRAM variable-length channel

Counting `MOV DPTR,#D070 ; MOVX @DPTR,A` sites and classifying the byte source:

| Image | total | code-space (`MOVC`) | XRAM (`MOVX`) | terminator |
|---|---|---|---|---|
| RP500 | 2 | 2 | **0** | — |
| V20 | 34 | 2 | **32** | `0xF5` |
| C48 | 34 | 2 | **32** | `0xF5` |
| C63 | 34 | 2 | **32** | `0xF5` |

The XRAM channel is the GSP user-cab / user-model path: index cell
`0x233F` (C48) / `0x24FD` (C63), length cell `0x2546` (C48) / `0x2704` (C63),
source `0x2445+index` (C48) / `0x2603+index` (C63), terminated by `0xF5`
written to `0xD070`.

**V20 (2006, pre-IR) already has all 32 sites.** The channel therefore
predates the user-cab feature by at least one product generation.

## 3. The 113-byte DSP register-init block

Copy loop: 113 bytes, index 0–0x70, **skipping index 0x59**, destination
`0xD000+index`.

| Image | site | content |
|---|---|---|
| RP500 | 14:0x2C80 / 15:0x2CBB | identical in both banks |
| V20 | 14:0x3100 | |
| C48 | 14:0x3160 (body starts 0x3158) | |
| C63 | 14:0x3170 (body starts 0x3168) | |

Pairwise:

| Pair | identical | notes |
|---|---|---|
| **C48 vs C63** | **113/113 (100 %)** | the IR build changed nothing |
| RP500 vs V20 | 91/113 (80.5 %) | 22 diffs |
| RP500 vs C48/C63 (shift-corrected) | 83/105 | same 22 diffs |

The 22 differing bytes are confined to:

```
offset 0x20–0x37  (36-byte device-specific parameter region)
offset 0x5C, 0x5E, 0x63, 0x66
```

The other **91 of 113 bytes are byte-identical** across the RP500 and the GSP
family, including the whole of `0x00–0x1F` and `0x38–0x70`.

Side-by-side of the differing region:

```
RP500 : E3 00 00 00 00 00 75 DF CF 08 00 0E 06 20 28 0A 02 72 5C 67 53 5C
GSP   : C3 00 00 00 AA 0A 61 C7 03 10 00 12 14 02 16 18 08 72 5C 67 52 5C 5C 06
```

Tail (identical up to the four listed bytes):

```
RP500 : E0 00 C0 03 03 00 02 00 3F E7 FE FF FF 00 0B 01
GSP   : E0 00 C0 03 00 00 00 00 3F E7 FE F9 FF 00 8B 01
```

## 4. The 24-byte flash→DSP stream descriptor

| Image | bytes |
|---|---|
| RP500 | `C9 12 12 34 12 10 00 09 01 01 0C 50 0A 20 01 00 12 AB 02 0A ED 02 00 1F` |
| V20 | `DD 12 12 34 12 10 00 09 01 01 0C 50 0A 20 01 00 14 BD 02 0B 46 02 14 B0` |
| C48 | `01 01 0C 50 0A 20 01 00 14 BD 02 0B 46 02 14 B0 15 5E 74 A9 25 1C F8 E6` |
| C63 | `01 01 0C 50 0A 20 01 00 14 BD 02 0B 46 02 14 B0 15 5E 74 A9 25 1C F8 E6` |

- **RP500 vs V20: 17/24 identical.**
- The shared 17 bytes are the **entire 15-byte body** `12 12 34 12 10 00 09 01
  01 0C 50 0A 20 01 00` plus the two `02` separators in the tail.
- The 7 differing bytes are device-specific values in the same structure:
  `[C9|DD]` at offset 0, and the 8-byte tail `12 AB 02 0A ED 02 00 1F`
  (RP500) vs `14 BD 02 0B 46 02 14 B0` (GSP).
- C48/C63 stream the **same 16-byte tail as V20**, starting 8 bytes later in the
  same structure. The descriptor is stable V20 → C48 → C63.

---

## 5. What this shows

1. **Same host↔DSP interface family.** The stream routine, the `0xD070` data
   port, the `0xD06E` flow control, and 87/113 bytes of the register-init block
   are literally the same in the RP500 and the GSP.
2. **The IR firmware changed nothing on the DSP side that is visible in
   firmware.** C48 → C63 is byte-identical in the 113-byte init block, and the
   stream protocol (2 code-space + 32 XRAM sites) is unchanged.
3. **The variable-length channel is older than the IR feature.** V20 (2006)
   already has the 32 XRAM-sourced stores and the `0xF5` terminator.

## 6. What this does **not** show

- **Not** that the RP500's AudioDNA2 can convolve. The GSP has **two** AudioDNA2
  chips; the RP500 has **one**. The chip masks/part numbers were not compared
  (RP500 U25 reads `72-1002 GREEN / 7169170 / 1012 KOREA`; no GSP board
  photograph exists in the corpus).
- **Not** that the RP500's DSP accepts the `0xF5`-terminated variable-length
  block. The RP500 host never sends one, so there is no evidence either way.
- **Not** that the GSP's XRAM channel is used for user cabs specifically in
  V20 — V20 has no user-cab UI. What is proven is that the *channel* exists.
- **Not** which part of the 2048-byte record is streamed (the 512-byte
  coefficient part or the whole record). The staging routine at C63 bank 15
  `0xD7D1` copies a caller-sized buffer; the size is still an open question.

## 7. The remaining decisive test

Unchanged: a **logic-analyzer capture of the GSP host↔DSP bus during a user-cab
load**, or the DSP microcode/ISA. The block comparison narrows the question to
one chip-level fact — whether the RP500's single AudioDNA2 is the same mask as
one of the GSP's two — but it cannot answer it from firmware alone.
