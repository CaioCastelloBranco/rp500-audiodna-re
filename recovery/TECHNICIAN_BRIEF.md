# RP500 firmware restore — technician brief

**Goal:** restore the RP500 main firmware by reprogramming one flash chip.
Nothing else on the board needs to be changed.

---

## 1. The chip

| Item | Value |
|---|---|
| Board | DigiTech RP500, **80-0145-A**, component side |
| Reference | **U26** |
| Part number (under the white label) | **`SST29AL016J70TFI02`** (Spansion / SST) |
| Package | **TSOP-48, 0.5 mm pitch** |
| Size | **16 Mbit = 2 MB** (2M x 8 byte mode) |
| Supply | **3.0–3.6 V (3.3 V)** — **never 5 V** |
| Speed | 70 ns |
| Factory label on top | `72-0089-12  V1.20  RP500  CS.8CD9` |

The chip sits between the **AudioDNA2** (large QFP, U25), the
**Samsung K4S641632N** SDRAM (U24) and the row of **74HCT574** latches.
Photos: `05_evidence/board/10_flash_SST29AL016J.jpg`,
`05_evidence/board/08_dsp_sdram_flash_label.jpg`,
`05_evidence/board/01_full_board_top.jpg`.

---

## 2. What the technician needs

| Item | Requirement |
|---|---|
| Programmer | **XGecu T48** (recommended) or **TL866II Plus** with `SST29AL016J` / `SST29AL016` in its device list |
| Adapter | **TSOP48 to DIP48 adapter, 0.5 mm pitch** (not TSOP56) |
| Voltage | **3.3 V** (set the programmer/adapter to 3.3 V, not 5 V) |
| Tools | Hot-air station, flux, solder paste or fine iron, Kapton tape, magnifier |
| Software | The programmer's own software; no special tool needed |

If the programmer's list has no `SST29AL016J`, use the **`SST29AL016`**
entry (same JEDEC family) or a programmer that lists the Spansion
`S29AL016J`.

---

## 3. The image files

All in `D:\OPENCODE\RP500\09_builds\recovery_stock_1mb\`:

| File | Size | SHA-256 |
|---|---|---|
| `stock_1mb.bin` | 1,048,576 | `718fda7de9206838d5e4945d7cff0c890c3573dc68c81142df23f7dab765fa11` |
| `stock_2mb_padded_ff.bin` | 2,097,152 | `01978cbfbe20fc565a3c8100b415798855fd90e6bb6580ad193f5df5ac507d8d` |

- `stock_1mb.bin` is the RP500 firmware, raw, **1 MB**.
- `stock_2mb_padded_ff.bin` is the same 1 MB followed by **1 MB of `0xFF`**,
  for programmers that insist on the chip's full 2 MB size.
- **Do not** use any `.DigBin` file directly; the programmer needs the raw
  `.bin` above.
- The first 16 bytes of the firmware are:

```
EA 00 02 00 6B 53 91 DF 32 00 FF 02 23 4E 01 1F
```

- Windows hash check:

```
certutil -hashfile stock_1mb.bin SHA256
```

---

## 4. Procedure

1. **Photograph U26 and note pin 1** before removal. Pin 1 is the small
   circular dot on the package; the board has a white corner marker.
2. **Desolder U26** with hot air. Protect the neighbouring SDRAM, DSP and
   latches with Kapton tape. Do not lift pads.
3. Clean the pads and place U26 in the **TSOP48 0.5 mm adapter**.
4. **Read the original chip completely (2 MB)** and save it as a backup
   (`orig_2mb.bin`). Check the first 16 bytes against the list above; the
   original may be the stock 2.0 image or the failed 2.2 image.
5. **Erase** the chip.
6. **Program** one of:
   - `stock_1mb.bin` at address **`0x000000`**, or
   - `stock_2mb_padded_ff.bin` at address **`0x000000`** if the programmer
     requires a full 2 MB file.
7. **Verify** the whole programmed area.
8. **Reinstall U26** in the original orientation (pin 1 dot aligned with the
   board marker).
9. Power on. The unit should boot the stock firmware and the display should
   show the normal RP500 start-up; USB should enumerate as
   **`VID_1210 / PID_0016`** (DigiTech RP500).

---

## 5. About the upper 1 MB

The RP500 updater addresses only **16 x 64 KB = 1 MB**, so the firmware lives
in the **first half** of the 2 MB chip. The upper 1 MB is outside the
updater's map.

- If the original upper 1 MB reads **all `0xFF`**, the padded file is correct.
- If the original upper 1 MB contains data, **do not overwrite it**: program
  the stock 1 MB into the lower half and restore the original upper half
  (merge `stock_1mb.bin` + `orig_2mb.bin[0x100000:0x200000]`).

---

## 6. Do not

- **Do not** use a 5 V setting.
- **Do not** touch **U19 (TAS1020B)** or its small I2C EEPROM. That is the
  USB controller and is not part of this repair.
- **Do not** program the failed 2.2 S3b image (`be9676…`).
- **Do not** power the unit with U26 removed.

---

## 7. What "success" looks like

- Display: normal RP500 boot, no immediate power-down.
- USB: `VID_1210 / PID_0016`.
- The unit accepts the stock 2.0 firmware and behaves normally.

If it does not boot, re-check pin 1, solder joints, and the verify result
before changing anything else.
