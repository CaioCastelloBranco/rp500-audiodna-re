# RP500 Storage — where the 100 user presets live (roadmap S2)

**Question:** the RP500 stores 100 user presets and 100 factory presets. A user
cab would have to live somewhere too. Where?

**Answer:** **not in the RP500's flash and not in RAM.** The device has a
**bulk preset service** with several storage back-ends; "save preset" is one
`MOVE_PRESET` message (`0x39`), and its framing is now known exactly
(`rp500_preset_protocol.md`). The user bank's physical store is still open —
it is *not* the firmware flash and *not* XRAM, and the leading candidate is a
**serial (SPI/I²C) device**, which the XDATA map cannot see.

Everything below is re-derived by
`04_analysis_scripts/rp500_memmap.py` and `04_analysis_scripts/audit_claims.py`
and is checked against the archived flash log.

---

## 1. The device's flash is 1 MB, and a firmware update rewrites all of it

The device reports its own flash geometry during the update (opcode `0x78`,
archived in `05_evidence/2026-11-10_rp500_updater_flash.log`):

```
Flash map: maxBlock=256, segments=16
  segment addr=0x00000000 size=0x00010000 (65536 bytes)
  ...
  segment addr=0x000F0000 size=0x00010000 (65536 bytes)
Data to write: 1048576 bytes across segments (image bytes: 1048576)
```

16 × 64 KB = **exactly 1 MB** — the whole device flash is firmware.

Now the important detail: **which blocks does the updater actually write?**

| | count |
|---|---|
| 256-byte blocks in a 1 MB image | 4 096 |
| blocks the log sent (`0x7A` data frames) | **4 039** |
| all-`0xFF` blocks in the patched image | 606 |
| …of those, in segment 0 (the first 64 KB) | 58 |
| …of those, in segments 1–15 | **548** |

4 096 − 4 039 = **57 blocks skipped**, and segment 0 alone contains 58 empty
blocks. So the rule is exactly:

> **The all-`0xFF` skip applies only inside segment 0. Every empty block in
> segments 1–15 is written.**

That includes **bank 1's 24 528-byte free run at `0xA030`** — the `0x5FD0`
region the roadmap had provisionally earmarked for stub code. It is *not*
persistent storage: the next firmware update writes over it.

⇒ **There is no persistent space in the RP500's firmware flash.**

## 2. There is no RAM store either

`04_analysis_scripts/rp500_memmap.py` maps every XDATA access the firmware
makes (all 16 banks, instruction-aligned):

| XDATA band | writes | reads | what it is |
|---|---|---|---|
| `0x0000`–`0xCFFF` | **3** | 0 | stray writes only |
| `0xD000`–`0xDFFF` | 7 | 57 | the **AudioDNA2** window |
| `0xE000`–`0xEFFF` | 57 | 21 | the DSP **command** ports (`0xE000`, `0xE200`, `0xE400`, `0xE600`, `0xEE00`) |
| `0xF000`–`0xFFFF` | 715 | 2 531 | the 8051's own scratch |

215 distinct written addresses in total, and **nothing** in the first 48 KB of
XRAM. The firmware also uses `MOVX @R0` / `@R1` heavily (1 679 + 1 366 writes,
833 + 1 054 reads) — but every one of those is to the low XRAM scratch area,
not to a paged device.

⇒ **The firmware keeps no persistent data of its own.**

## 3. No **MOVX-visible** external device is driven

No `MOVX` in the firmware targets a paged or aliased range; the only external
devices the 8051 talks to *through the memory bus* are the **AudioDNA2**
(window `0xD000` and the command ports) and its own program memory (the 1 MB
flash, read with `MOVC`).

**This does not rule out a serial device.** A bit-banged SPI/I²C store never
appears in the XDATA map, and the firmware's own `ERASE ` (bank 7 `0x3FBD`),
`FLERR ` (bank 15 `0x524C`), `BUSY ` and `FACT RST  ` strings are exactly what
such a driver emits. See `rp500_preset_protocol.md` §5 for why this matters.

## 4. The deduction, and its revision

With (1) flash fully committed to firmware, (2) no RAM store and (3) no
MOVX-visible external device, the only place left *inside the MAP* was the
**AudioDNA2 DSP**. That was S2's first answer.

**It has since been revised — see `rp500_preset_protocol.md` §5.** gdigi (the
archived open-source host tool) speaks the RP500's preset protocol, and its
bank list contains `PRESETS_MEDIA_CARD` (3) and `PRESETS_EXTERNAL` (6) — i.e.
the platform has **more than one persistent preset back-end**. And fact (3)
above is **too strong as stated**: the XDATA map only proves there is no
**MOVX-visible** device. A **bit-banged serial store (SPI/I²C) is invisible to
it** — and the firmware's own strings `ERASE ` (bank 7 `0x3FBD`), `FLERR `
(bank 15 `0x524C`), `BUSY ` and `FACT RST  ` are exactly what such a driver
emits.

The corrected statement:

> The RP500 has **no MOVX-visible store**. That does not rule out a serial one.
> The platform has at least three kinds of preset back-end (system, user,
> media-card/external) and the device implements at least two — `MOVE_PRESET`
> branches on the bank code and sends the user bank to one routine and every
> other bank to another.

So the user-preset store is most likely an **external serial flash/EEPROM
driven from bank 7**, not XRAM and not the AudioDNA2. The DSP is still a data
*source* (below), but it is not where the presets are proven to live.

What *is* established about the DSP holds: it hands data back as well as
taking it.

- The **GSP1101 pulls blocks out of the DSP**: `MOVX A,@DPTR` on `0xD070`,
  storing into `XRAM 0x24FE+index` (C63 bank 15 `0x2F83`–`0x2F9F`).
- The **RP500 reads `0xD070` back** in its own stream routine: bank 15
  `0xBE8F`, bank 14 `0x9A9D`.

## 5. The carrier for a user IR exists — and it is now decoded

The RP500 firmware contains a **bulk preset service**, and gdigi proves it is
a working, shipping client of it. The firmware's message names
(`PRESET  `, `RESTORE   `, `RESTORED  `, `ALL DONE`, `BULKERR1`,
`PID %04X  `, `POS     %02X`) are the status side of that service; the
**message IDs and framing are in `rp500_preset_protocol.md`**:

- fill the edit buffer with `RECEIVE_PRESET_PARAMETERS` (`0x2D`), or pull a
  whole preset with `REQUEST_PRESET` (`0x2A`);
- commit a slot with `MOVE_PRESET` (`0x39`), payload
  `<srcBank> <srcIndex> <dstBank> <dstIndex> <name>\0 <flags>`;
- dump/restore everything with `REQUEST_BULK_DUMP` (`0x18`).

**That is the path a user IR should use** — the RP500's own protocol, not the
GSP's Jcabinet protocol: no Super7 packing, no checksum, no new protocol
class, and gdigi already speaks it.

## 6. What this changes in the port plan

| | Before S2 | After S2 + S2b |
|---|---|---|
| Where does the 2048-byte user-cab record live? | "a flash slot beside the presets" — **there is no such slot** | in whichever back-end the user bank uses. Not in the firmware flash (measured), not in XRAM (measured); the platform's user/media-card/external back-ends are the candidates |
| Transport for a user IR | the GSP's Jcabinet protocol (`0x7A`/`0x73`, Super7, XOR checksum) | **the RP500's own preset protocol** — `0x2D` to fill the edit buffer, `0x39` to commit. Framing known exactly; gdigi is a working client |
| Storage work in S4 | write 10 × 2048 B to a flash area | implement/reuse the preset transport; the *device* owns the slot storage |
| Is a new flash-write primitive needed? | assumed yes | **no** — the device already stores presets; the host never writes the store directly |
| What is the gate? | "can the DSP render an IR?" | **unchanged and now sharper** — the copy has to reach the DSP and be convolved with |

## 7. What is *not* proved here (honest limits)

- **Where the user bank physically lives is still open.** It is *not* the
  firmware flash and *not* XRAM (both measured), but the serial-back-end
  hypothesis is a *hypothesis*: no SPI/I²C driver was located. This is the
  single biggest open item after the DSP gate.
- The `MOVE_PRESET` **USER branch was not followed to the store.** It goes
  bank 7 `0xABD2` → `LCALL 0B4B` (with `R7 = 0x3B`) → target `0xD8AD`; the
  trail stops there.
- **S2's first answer ("inside the AudioDNA2") was wrong** — it rested on
  "no external device", which the MOVX map cannot establish. Recorded here
  rather than quietly dropped.
- The `RECEIVE_PRESET_PARAMETERS` payloads carry *parameter values*, so a
  user IR cannot ride the parameter path as-is; it needs its own message or a
  reserved parameter range. That is a design question for S4.

## 8. Next step

**Locate the serial store.** Read the USER branch of `MOVE_PRESET` (bank 7
`0xABD2` → `0x0B4B` → `0xD8AD`) through to the routine that emits `ERASE ` /
`FLERR `, and identify the physical device and its address layout. Bounded,
static, and it answers the last storage question.
