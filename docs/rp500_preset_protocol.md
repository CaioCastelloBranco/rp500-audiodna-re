# The RP500's preset protocol (roadmap S2b) — recovered from gdigi

**Result: the RP500 speaks the gdigi/HMG preset protocol, and "save preset" is
a single message whose framing is now known exactly.**

This closes S2b (the transport a user IR would use). It also **corrects** part
of S2's conclusion — see the last section.

---

## 1. The protocol match is exact, not circumstantial

gdigi (archived in `07_open_source_tools/gdigi/`, a third-party host tool for
DigiTech pedals) uses these message IDs:

| ID | gdigi name |
|---|---|
| `0x18` | `REQUEST_BULK_DUMP` |
| `0x19` | `RECEIVE_BULK_DUMP_START` |
| `0x1B` | `RECEIVE_BULK_DUMP_END` |
| `0x21` | `REQUEST_PRESET_NAMES` |
| `0x22` | `RECEIVE_PRESET_NAMES` |
| `0x28` | `REQUEST_PRESET_NAME` |
| `0x29` | `RECEIVE_PRESET_NAME` |
| `0x2A` | `REQUEST_PRESET` |
| `0x2B` | `RECEIVE_PRESET_START` |
| `0x2C` | `RECEIVE_PRESET_END` |
| `0x2D` | `RECEIVE_PRESET_PARAMETERS` |
| `0x39` | `MOVE_PRESET` |

The RP500 firmware has a **message dispatch table at bank 7 `0x699E`** whose
entries are `<id> <handler:16>`, and **all twelve gdigi IDs are in it**, each
with a handler in the `0x6Axx` thunk range:

```
bank 7 0x699E:  11 6a7b | 18 6a80 | 19 6a85 | 1b 6a76 | 20 6a16 |
               21 6a93 | 22 6a1b | 28 6a20 | 29 6a4e | 2a 6a53 |
               2b 6a58 | 2c 6a5d | 2d 6a62 | 39 6a67 | 3a 6a0c |
               40 6a11 | 41 6a93 | 51 6a8a | 55 6a2a | 71 6a49 | 72 6a3a
```

**12 of 12.** Checked by `audit_claims.py` §12c.

## 2. How gdigi saves a preset

`gdigi.c:1045` — *store_preset_name*:

```c
void store_preset_name(int x, const gchar *name)
{
    GString *msg = g_string_sized_new(6);
    g_string_append_printf(msg, "%c%c%c%c%s%c%c",
                           PRESETS_EDIT_BUFFER, 0, /* source */
                           PRESETS_USER, x,        /* destination */
                           name, 0,                /* name */
                           1);                     /* load */
    send_message(MOVE_PRESET, msg->str, msg->len);
}
```

⇒ **`MOVE_PRESET` (0x39) payload:**

| offset | size | field |
|---|---|---|
| 0 | 1 | source bank (`4` = edit buffer) |
| 1 | 1 | source index |
| 2 | 1 | destination bank (`1` = user) |
| 3 | 1 | destination index |
| 4 | n+1 | preset name, NUL-terminated |
| … | 1 | flags (`1` = load) |

`gdigi.c:1027` — *switch_preset* is the same message with the banks swapped
(source = the slot, destination = the edit buffer).

The parameters themselves are pushed separately with **`RECEIVE_PRESET_PARAMETERS`
(0x2D)**: a count (BE16) followed by `<paramId:BE16> <position> <value>` per
parameter (`gdigi.c:994`). The device answers a save with the notification
`NOTIFY_PRESET_STORED` (1) or `NOTIFY_PRESET_MOVED` (3).

The device can also **dump everything**: `REQUEST_BULK_DUMP` (0x18) →
`RECEIVE_BULK_DUMP_START` (0x19) → messages → `RECEIVE_BULK_DUMP_END` (0x1B);
gdigi writes that straight to a backup file (`create_backup_file`).

## 3. gdigi's bank list — the platform has several preset back-ends

| gdigi | value | meaning |
|---|---|---|
| `PRESETS_SYSTEM` | 0 | factory/system |
| `PRESETS_USER` | 1 | the user's own slots |
| `PRESETS_ARTIST` | 2 | artist presets |
| `PRESETS_MEDIA_CARD` | 3 | **on a card** |
| `PRESETS_EDIT_BUFFER` | 4 | the RAM copy being edited |
| `PRESETS_FACTORY2` | 5 | a second factory set |
| `PRESETS_EXTERNAL` | 6 | **external** storage |

And the firmware **branches on the bank code**: in the `MOVE_PRESET` handler
(bank 7 `0xABD2`) the bank is compared with `1`; the USER path sets
`R7 = 0x3B` and calls the routine at `0xD8AD`, while every other bank takes
`R7 = 3` (the media-card back-end):

```
AC03  MOV  A,@R1
AC04  XRL  A,#01h
AC06  DEC  R1
AC07  ORL  A,@R1
AC08  JZ   AC0F          ; bank == 1 (USER) ?
AC0A  MOV  R7,#03h       ; no  -> media card
AC0C  LJMP ACF2
AC0F  MOV  R7,#3Bh       ; yes -> USER
AC11  LCALL 0B4B         ; -> target 0xD8AD
```

The **preset descriptor index** is a table in **XRAM at `0xF912`**
(0x2D = 45 entries × 2 bytes), walked by the routine at bank 7 `0xD8B9`;
each non-empty entry points at a descriptor that is read with `MOVC` from
**code space**. So the volatile layer is: XRAM index → code-space descriptor.

> **Correction 2026-11-11.** This was previously written as `0xF9F2`. The
> walker at `0xD8C8` doubles the index with `ADD A,ACC` (`25 e0`), adds
> `#0x12`, then `ADDC #0xF9`, so the address is **`0xF912 + 2*i`**. The old
> audit check guarded this with `...count(...) >= 0`, which is always true;
> it now checks the actual arithmetic.

## 4. What this means for the port

| | Before | After |
|---|---|---|
| Transport for a user IR | "the GSP's Jcabinet protocol (`0x7A`/`0x73`, Super7, checksum)" | **the RP500's own preset protocol**: `RECEIVE_PRESET_PARAMETERS` (0x2D) to fill the edit buffer, then `MOVE_PRESET` (0x39) to commit it to a slot — framing now known exactly, and **no Super7, no checksum, no new protocol class** |
| Who else can talk to it | — | **gdigi already can** — a working, shipping client for the same service |
| Where the slots live | "a flash slot beside the presets" | still open, but the search is now confined to the `MOVE_PRESET` USER branch (bank 7 `0xABD2` → `LCALL 0B4B` → `0xD8AD`) and the `ERASE `/`FLERR `/`BUSY ` strings in bank 7 |

## 5. A correction to S2

S2 concluded "no external data device is driven" from the XDATA memory map.
That is **too strong**: the memory map only proves there is no **MOVX-visible**
device. A **bit-banged serial device (SPI/I²C) is invisible to it** — and the
firmware's own strings `ERASE ` (bank 7 `0x3FBD`), `FLERR ` (bank 15 `0x524C`),
`BUSY ` and `FACT RST  ` are exactly what such a driver emits.

Combined with gdigi's `PRESETS_MEDIA_CARD` (3) and `PRESETS_EXTERNAL` (6)
banks, the platform clearly has **more than one persistent back-end**, and the
RP500's user bank is one of them. The honest statement is therefore:

> The RP500 has **no MOVX-visible store**, but that does not rule out a
> serial one. The platform has at least three kinds of preset back-end
> (system, user, media-card/external) and the device implements at least two
> of them.

So the user-preset store is most likely an **external serial flash/EEPROM**
driven from bank 7 — not XRAM, and not the AudioDNA2 as S2 first suggested.
That is a **revision**, not a confirmation, and it is the one place where the
gdigi evidence overrules my earlier deduction.

## 6. Next step

Locate the serial driver in bank 7 — the routine behind `ERASE ` / `FLERR ` —
and read the USER-bank branch of `MOVE_PRESET` to find the physical device and
its address layout. With the framing now known, that is a bounded search, and
it is still purely static.
