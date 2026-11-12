# RP500 amp → cab pairing (user-observed, 2026-11-11)

The RP500 **always** assigns a cabinet when an amp is selected. The user can
change the cab **after** the amp, but the next amp change overwrites it. It is
not possible to choose a cab before an amp. This is a **MetaParam**
relationship in the model: the amp is `AmpType_1 = 2496` (position 8), the cab
is `CabType_1 = 2560` (position 9), and the cab is one of the amp's
**controlled parameters** (`RP500Preset.cs`, the `MetaParam` at line 195 and
`controlledParams3`).

The pairing is **RP500-specific** (each unit has its own amp/effect list), so
it must be taken from the RP500 device/manual, not from the GSP or RP1000.

## Observed pairs

Cab indices/IDs below are from the RP500 cab table (X-Edit / firmware agree on
the first 26; the firmware adds `DREAD AC` 607 and `JUMBO AC` 606).

| Amp (0-based index) | Amp ID | Cab | Cab index | Cab ID |
|---:|---:|---|---:|---:|
| 0 `'57 Tweed Champ` | 307 | Champ 1x8 | 0 | 571 |
| 1 `'57 Tweed Deluxe` | 308 | Deluxe 1x12 | 1 | 572 |
| 2 `'59 Tweed Bassman` | 309 | Bassman 4x10 | 9 | 579 |
| 3 `'62 Brown Bassman` | 310 | Blonde 2x12 | 5 | 577 |
| 4 `'65 Blackface Twin` | 311 | Twin 2x12 | 6 | 576 |
| 5 `'65 Blackface Deluxe` | 312 | Deluxe Reverb 1x12 | 2 | 573 |
| 6 `'65 Plexi JTM-45` (firmware `45 JTM`) | 313 | Greenback 4x12 | 11 | 616 |
| 7 `'68 Plexi Lead` | 314 | Vintage 4x12 | 14 | 622 |
| 8 `'68 Plexi Jump Panel` | 315 | Greenback 4x12 | 11 | 616 |
| 18 `'01 Dual Rectifier` | 321 | Vintage 4x12 | 14 | 622 |
| 24 `'60 GA-40` | 380 | GA 1x12 | 4 | 624 |
| 27 `'89 RG100` | 374 | Vintage 4x12 | 14 | 622 |
| 38 `DigiTech Spank` | 330 | DigiTech Spank 2x12 | 23 | 608 |
| **39 `GSP2101 Clean Tube`** | **328** | **CAIO4X12** | **24** | **585** |
| **40 `GSP2101 Sat Tube`** | **329** | **CAIO4X12** | **24** | **585** |
| 46 `DigiTech Dark Metal` | 369 | Recto 4x12 | 15 | 625 |

The user notes the order is the same as the manual/device/code; the pairs
above are the ones observed directly on the patched unit. The full table is
**many-to-one** (53 amps, 28 cabs).

## Why this matters for the experiment

- The pairing is not a contiguous byte/word/pointer table in the RP500 or C63
  image: the exact first-nine sequence was searched as 8-bit indices, 16-bit
  IDs (BE/LE), cab-name pointers and 3-byte `ampID+cabIdx` records - no match.
  It is therefore code or an encoded table (or lives in the amp-model data).
- **We do not need the full table.** **GSP2101 Clean Tube** and **GSP2101 Sat
  Tube** both select **CAIO4X12 (cab 24, ID 585)**. Selecting one of those amps
  is a deliberate, repeatable, non-boot event that **guarantees** the cab
  write - exactly the trigger option B needs.
- Because the cab can be changed after the amp, the gate should key on the
  **cab value** (`585`), not the amp value. Then:
  - amp change to GSP2101 Clean/Sat -> cab 585 -> fire;
  - manual cab selection to CAIO4X12 -> cab 585 -> fire;
  - any other cab -> no fire.
- At boot the edit-buffer table at `0xF6AA` is **zero** (measured in uCsim),
  so a gate that reads it cannot fire at boot.

## The remaining unknown

The **edit-buffer index** for the cab is not yet pinned. The name table puts
`CAB_TYPE` at index 26, but the preset descriptor order may be different: the
descriptor walker at bank 7 `0xD8B9` reads a 45-entry pointer table at
**XRAM `0xF912 + 2*i`** (corrected from the earlier `0xF9F2`; the walker
doubles the index with `ADD A,ACC`). The first hardware-safe build can scan
the 100 3-byte cells at `0xF6AA` for the 3-byte value `00 02 49` (585),
instead of assuming index 26. A false positive is unlikely (585 is large);
the gate can be narrowed once the unit confirms.

## Full manual lists (1-based, as printed)

**Amps (53).** The order matches the firmware pointer table at bank 4 `0x46B8`
and the X-Edit `MetaParamItem` list exactly.

| # | Amp | # | Amp | # | Amp |
|---:|---|---:|---|---:|---|
| 1 | '57 Tweed Champ | 19 | '01 Dual Rectifier | 37 | DigiTech Blues |
| 2 | '57 Tweed Deluxe | 20 | '02 Triple Rectifier | 38 | DigiTech Fuzz |
| 3 | '59 Tweed Bassman | 21 | '99 Legacy VL-100 | 39 | DigiTech Spank |
| 4 | '62 Brown Bassman | 22 | '96 Matchless HC30 | 40 | GSP2101 Clean Tube |
| 5 | '65 Blackface Twin | 23 | '88 Soldano 100 | 41 | GSP2101 Sat Tube |
| 6 | '65 Blackface Deluxe | 24 | '69 Supergroup | 42 | DigiTech Crunch |
| 7 | '65 Plexi JTM-45 | 25 | '60 GA-40 | 43 | DigiTech Monster |
| 8 | '68 Plexi Lead | 26 | '73 OR-120 | 44 | DigiTech Tweedface |
| 9 | '68 Plexi Jump Panel | 27 | '02 PV 5150II | 45 | DigiTech Blackbass |
| 10 | '77 Master Volume | 28 | '89 RG100 | 46 | DigiTech Stoner Rock |
| 11 | '83 JCM800 | 29 | '84 JC-120 Jazz | 47 | DigiTech Dark Metal |
| 12 | '93 JCM900 | 30 | '67 Solar 100 | 48 | DigiTech Transistor |
| 13 | '01 JCM2000 | 31 | DigiTech Solo | 49 | DigiTech Brown Sound |
| 14 | '62 AC-15 | 32 | DigiTech Metal | 50 | DigiTech Mosh |
| 15 | '63 AC-30 TB | 33 | DigiTech Bright Clean | 51 | Dread Acoustic |
| 16 | '69 Hiwatt 100 | 34 | DigiTech Chunk | 52 | Jumbo Acoustic |
| 17 | '81 Boogie Mark IIC | 35 | DigiTech Clean Tube | 53 | Direct |
| 18 | '93 Boogie Mark IV | 36 | DigiTech High Gain |  |  |

**Cabs (26 in the manual).** The firmware table adds `DREAD AC` (607) and
`JUMBO AC` (606) as entries 27–28, but these are **not selectable cabs**: they
are **locked pairs** for the `Dread Acoustic` / `Jumbo Acoustic` amps. Those
amps cannot use any other cab, and no other amp can use those two cabs. The
26-row list above is the full selectable set; the two locked entries explain
the 26-vs-28 difference between the manual/X-Edit list and the firmware table.

| # | Cab | # | Cab | # | Cab |
|---:|---|---:|---|---:|---|
| 1 | Champ 1x8 | 10 | Bassman 4x10 | 19 | DigiTech Metal 4x12 |
| 2 | Deluxe 1x12 | 11 | British 4x12 | 20 | DigiTech Rock 4x12 |
| 3 | Deluxe Reverb 1x12 | 12 | Greenback 4x12 | 21 | DigiTech Alt 4x12 |
| 4 | British 1x12 | 13 | Fane 4x12 | 22 | DigiTech Vintage 4x12 |
| 5 | GA 1x12 | 14 | Boutique 4x12 | 23 | DigiTech Chunk 4x12 |
| 6 | Blonde 2x12 | 15 | Vintage 4x12 | 24 | DigiTech Spank 2x12 |
| 7 | Twin 2x12 | 16 | Recto 4x12 | 25 | DigiTech Spkr Comp / CAIO4X12 |
| 8 | British 2x12 | 17 | DigiTech Solo 4x12 | 26 | Direct |
| 9 | Jazz 2x12 | 18 | DigiTech Bright 2x12 |  |  |

**Confirmed behavior (user test):** from `'60 GA-40` (cab GA 1x12), change the
cab to anything, then select `GSP2101 Clean Tube` -> the cab **always**
returns to CAIO4X12. The cab only changes when the cab or amp is changed; a
cab cannot be selected before an amp. This makes the amp change a
**guaranteed cab write**, and the cab value a **reliable trigger**.

**Exception:** `Dread Acoustic` and `Jumbo Acoustic` are locked to
`DREAD AC` / `JUMBO AC`; their cabs are not in the selectable list and cannot
be used by other amps. This does not affect the GSP2101 Clean/Sat ->
CAIO4X12 trigger.

## 208 vs 128 taps (loader)

The C59 loader has a **`mono/left toggle`**; its code clamps to `0x80` (128)
or `0xD0` (208). This is consistent with the user's note: mono -> 208 taps;
otherwise 128, with the mono/left signal duplicated. The archive's
`usercab_encode.py` currently **hard-codes 128** and reads the **left channel
only**, so it does not yet implement the stereo path. A mono WAV and a stereo
WAV should be run through the converter before the encoder is changed.
