# RP500 stock 1 MB firmware image for external programming

> **The image file is not included in this public repository.** It contains
> vendor firmware, so it is shared on request. The SHA-256 below lets the
> technician verify whatever copy they receive. The same bytes can also be
> reconstructed from the official DigiTech updater with `tools/digbin_pack.py`.

**Purpose:** restore the RP500 main firmware flash (board `80-0145-A`,
component side) after the failed S3b experiment. This is the **raw 1 MB**
image, not the `.DigBin` container.

| | |
|---|---|
| File | `stock_1mb.bin` |
| Size | **1,048,576 bytes** (1 MB) |
| SHA-256 | `718fda7de9206838d5e4945d7cff0c890c3573dc68c81142df23f7dab765fa11` |
| Source | `01_source_firmware/rp500_v20.bin` (flat image) |
| Container equivalent | `01_source_firmware/rp500V20.DigBin`, SHA-256 `01d94790963a8c282fb25b322da5247b0b4b8d9b6063132b52bcf3894820a070` |
| Verification | the flat image was reconstructed from the `.DigBin` records and is byte-identical |

## The target

- **U26**, TSOP-48 parallel NOR flash on the AudioDNA2 external bus.
- Part number under the label: **`SST29AL016J70TFI02`** (Spansion/Cypress).
  - **16 Mbit = 2 MB**, organised 2M x 8 in byte mode (1M x 16 in word mode).
  - **3.0-3.6 V**, 70 ns, TSOP-48.
- Factory label: `72-0089-12  V1.20  RP500  CS.8CD9`.
- The RP500 updater addresses only **16 x 64 KB = 1 MB**, so the stock image
  occupies the **first half** of the chip. The upper 1 MB is outside the
  updater's map.
- **Read the full 2 MB before erasing**, so the upper half can be preserved
  (or confirmed blank). Program `stock_1mb.bin` at `0x000000`.
- Use **3.3 V only**; do not use a 5 V programmer setting.

## Programming

1. Power off and disconnect the unit.
2. Desolder U26 (hot air) or use a proper TSOP-48 in-circuit clip only if the
   AudioDNA2 is held in reset.
3. Read the chip first and save it; compare its first bytes with the image.
4. Erase, then program `stock_1mb.bin` at address `0x000000`.
5. Verify the whole 1 MB against the SHA-256 above.
6. Reinstall U26, power on, and confirm the normal boot and USB MIDI.

## Do not

- Do **not** write the stock image through the `ffff:fffe` DFU device. That
  device is the **TAS1020B's ROM bootloader**, and its only target ("EEPROM")
  is the TAS1020B's I2C configuration EEPROM, not this flash.
- Do **not** use the 2.2 S3b image.
