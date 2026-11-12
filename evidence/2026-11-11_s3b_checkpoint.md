# CHECKPOINT — 2026-11-11 — S3b flashed, unit in recovery bootloader

**Status:** updater 2.2 was **flashed at 21:51:24** and the log shows a clean,
complete transfer (`CloseMidi` → result page). The unit then shows `RP500`
and powers down. Windows sees it as a **stable DFU-class device**
`USB\VID_FFFF&PID_FFFE` (`Class FE/01/00`,
`STATUS_PNP_NO_COMPAT_DRIVERS`), not as a MIDI port — so the MIDI-only
updater cannot see it. The boot block is intact. Recovery is in progress.

---

## 0a. POST-FLASH STATE AND RECOVERY (2026-11-11 22:0x)

| Evidence | Value |
|---|---|
| 2.2 flash | **succeeded** 21:51:24; log ends `CloseMidi` / `UI: ShowPage(9)` |
| stock updater 2.1/2.3 run | 21:52:48 and 22:01:58 scans: **0 devices** (only the UMC204HD MIDI ports) |
| device node | `USB\VID_FFFF&PID_FFFE\6&38DD3522&0&7`, first install **21:51:29** (5 s after the flash) |
| status | `Error`, problem 28 `CM_PROB_FAILED_INSTALL`, status `0xC0000490` `STATUS_PNP_NO_COMPAT_DRIVERS` |
| compatible IDs | `USB\Class_FE&SubClass_01&Prot_00` (Application Specific / DFU) |
| real app descriptor (in image) | `VID 0x1210 / PID 0x0016`, USB 1.1, 352-byte config, 5 interfaces |
| conclusion | the app crashes in the boot DSP stream; the **bootloader/recovery USB stack** is what enumerates now. No MIDI, so the MIDI updater cannot enter update mode. |

**Recovery paths to try, in order:**

1. **Update mode by button at power-on.** The same updater's own XML documents
   the DigiTech pattern for the MX300/MX400: *power off → hold **Store +
   Effect Bypass** → power on → when the display reads **"UP"**, press Next*.
   The RP500 firmware contains the boot strings `RP 500`, `UPDATE`, `UPLOAD`
   (bank 15 offset `0x2D00`), so the same screen exists. On the RP500 the
   Effect Bypass is the **Bypass footswitch** (the tuner switch); the other
   candidate is the **Amp/Cabinet Bypass** button. If `UPLOAD` appears, run
   `updater_2.3_stock` (or `updater_2.1`) and flash.
2. **DFU path.** The `FFFF:FFFE` node is a valid, stable USB device. Bind a
   WinUSB/libusb driver and read its descriptors with `dfu-util -l` to learn
   the alternate settings and the expected image/format. Do not write until
   the descriptors are understood.
3. **External flash programming** is the guaranteed fallback (chip identity
   still to be confirmed from the board).

**Do not** reflash the 2.2 candidate.

---

## 0. State at shutdown (2026-11-11 17:11)

| | |
|---|---|
| unit | untouched; still the CAIO4X12 hello-world image; reports 2.0 |
| updater 2.2 | opened 17:11; log tail `[2026-11-11 17:11:20.549] UI: ShowPage(0)`; **no flash** |
| candidate | `09_builds/rp500_v20_s3b_impulse.DigBin`, SHA `be967671a8c8bd16388c6351c3a08626db508c43f5d07323ffbfee77b4838c4f` |
| IR | 128-tap unit impulse, tap 0 = `0x7FFFFF0`, rest zero |
| restore | `updater_2.1` (pre-gate CAIO4X12), `updater_2.3_stock` (stock, verified) |
| snapshot | `99_snapshot/project.bundle` + `99_snapshot/versions/2026-11-11_<head>/` |
| git | HEAD is this checkpoint commit; working tree clean |

**On resume:**

1. Run `09_builds/updater_2.2/Digitech.RP.Series.Firmware.Updater.exe`.
2. Record the **stock baseline** first: same known preset, **Direct** (570)
   and **CAIO4X12** (585).
3. Flash revision **2.2**; do not disconnect.
4. A/B: **GSP2101 Clean Tube → CAIO4X12** (impulse) vs **Direct** (dry).
5. If needed, restore with `updater_2.1` (CAIO4X12) or `updater_2.3_stock`
   (stock).

---

## 1. What is proved

| Item | Result |
|---|---|
| The RP500 always writes the paired cab when the amp changes | user-confirmed; the cab can only be changed after the amp |
| `GSP2101 Clean Tube` (amp 328) and `GSP2101 Sat Tube` (329) force **CAIO4X12** | cab index 24, cab ID **585** |
| The gate's stock path | sends the exact **24-byte descriptor**, no terminator, counter `0x0018`, 2 passes |
| The gate's IR path (test gate) | sends **512 bytes of the IR table in order, then `0xF5`**, counter `0x0200`, 2 passes |
| **Production scan, positive (585)** | the scan finds `00 02 49` → **512-byte impulse table + `0xF5`**, counter `0x0200`, 2 passes |
| **Production scan, negative (584)** | the scan rejects `00 02 48` → stock **24-byte descriptor**, no `0xF5`, counter `0x0018` |
| **Production scan, no cab value** | stock **24-byte descriptor**, no `0xF5`, counter `0x0018` |
| Boot cannot fire | the edit buffer at `0xF6AA` is zero at the boot stream |
| The DSP block | **still unmeasured** — uCsim's model always acknowledges |

The positive/negative scan tests use simulator-only gates that write the cab
value to `0xF6AA` and then run the **production scan code**; the production
gate (the payload) is unchanged.

Last full run: **`S3b host-logic: PASS`**. Before the final documentation edit,
the gates were `verify_all.py` 253/253, `audit_claims.py` 115/115,
`audit_software_probe.py` 31/31.

---

## 2. The build (candidate image layout)

Bank 15 hooks:

| Address | Stock | Patch |
|---|---|---|
| `0xBE97` byte-send entry | `MOV DPTR,#FF24` | `LJMP 0xE095` |
| `0xBE9E` source-base computation | `ADD A,#3B; MOV 82h,A; MOV A,#2E; ADDC A,R6; MOV 83h,A` | `LJMP 0xE800` + 6×`FF` |

Bank 15 free run:

| Address | Size | What |
|---|---|---|
| `0xE095` | 140 B | **production gate** — scans `0xF6AA`, chooses stock vs IR, terminates |
| `0xE800` | 26 B | source-base block — reads the RAM source cell |
| `0xE200` | 512 B | IR table — test pattern in the uCsim build; the hardware candidate carries the 128-tap impulse |

Free XRAM state cells:

| Cell | Meaning |
|---|---|
| `0xF8E0/1` | source base (lo/hi) |
| `0xF8E2/3` | length (lo/hi) |
| `0xF8E4` | terminator flag |

The production gate (`s3b_gate.asm`) contains the **real scan** for
`00 02 49` (585) in the 100 3-byte cells at `0xF6AA`. The test gate
(`s3b_gate_test.asm`, 71 B) hard-codes the IR cells and is **simulator-only**.

---

## 3. Files

| File | Role |
|---|---|
| `04_analysis_scripts/s3b_gate.asm` | production gate (140 B) |
| `04_analysis_scripts/s3b_gate_test.asm` | simulator-only test gate (71 B) |
| `04_analysis_scripts/s3b_source.asm` | source block (26 B) |
| `04_analysis_scripts/s3b_cab_trigger.py` | assembles, patches, runs both uCsim cases |
| `05_evidence/2026-11-11_s3b_cab_trigger.md` | design + measured results |
| `05_evidence/2026-11-11_amp_cab_pairs.md` | full amp/cab lists, behaviour, locked acoustic pair |
| `04_analysis_scripts/editbuf_probe.py` | uCsim edit-buffer dump (boot = zero) |
| `04_analysis_scripts/audit_software_probe.py` | 31 independent software checks |
| `06_deliverable/FINDINGS.md` | §9–§11 |
| `06_deliverable/rp500_preset_protocol.md` | `0xF912` correction |

---

## 4. Exact stopping point

**Stopped after:** the uCsim PASS for both cases, plus the candidate image
and updater 2.2 (both verified). **Not started:** the physical flash and the
listen test.

The candidate is the **CAIO4X12** last-known-good image plus the production
gate, source block and a **128-tap unit-impulse** table:

| | |
|---|---|
| flat image | `09_builds/rp500_v20_s3b_impulse.bin` (1 MB) |
| container | `09_builds/rp500_v20_s3b_impulse.DigBin` (0x100084) |
| sha256 | `be967671a8c8bd16388c6351c3a08626db508c43f5d07323ffbfee77b4838c4f` |
| delta | **684 bytes, all bank 15** |
| updater | `09_builds/updater_2.2/Digitech.RP.Series.Firmware.Updater.exe` (revision 2.2) |
| first tap | `07 ff ff f0` (`0x7FFFFF0`), rest zero |

The updater's embedded image was verified byte-for-byte against the candidate
(same SHA). The stock path on the CAIO4X12 base still sends the exact 24-byte
descriptor (uCsim PASS).

### Test results (last run)

| Case | At `0xD070` | First payload | Terminator | Counter | Passes |
|---|---|---|---|---|---|
| production gate, no cab value | 48 B | exact 24-byte descriptor | absent | `0x0018` | 2 |
| test gate, IR source | 1026 B | 512-byte table, in order | `0xF5` at 513 | `0x0200` | 2 |

Reproduce later with:

```
python 04_analysis_scripts/s3b_cab_trigger.py --runs 16000
```

---

## 5. What is *not* tested (the honest limits)

1. **The real scan.** The uCsim boot stream runs before any cab write, so the
   edit buffer is zero. The test gate proves the IR path; only the hardware can
   prove that the amp change leaves `585` at `0xF6AA`.
2. **The DSP.** uCsim's DSP model always acknowledges. Whether the AudioDNA2
   **renders** the 512-byte block is the actual S3b gate.
3. **The real IR.** The current table is a test pattern. A hardware candidate
   needs zeros, a unit impulse, or a real 128/208-tap IR.
4. **The cab value format.** The scan looks for the 3-byte value `00 02 49`
   (585). If the device stores the cab **index 24** instead, the scan will not
   match; the hardware test will show a silent no-fire, not a failure.

---

## 6. Exact next step (when we resume)

**The candidate is built. The next action is the physical flash (user).**

1. Power the RP500, connect USB, leave it in normal mode.
2. Run `09_builds/updater_2.2/Digitech.RP.Series.Firmware.Updater.exe`.
3. Scan → RP500 at **2.0** → select revision **2.2** → flash. Do not
   disconnect. Wait for the result page; the unit reboots.
4. On the unit, use a **known preset with an amp** (not Direct):
   * select **GSP2101 Clean Tube** (or Sat Tube) → cab **CAIO4X12** (585);
     the gate applies the impulse;
   * change the cab to **Direct** (570) → the gate does not fire → dry
     reference;
   * change back to **CAIO4X12** → the impulse again.
5. **Record** both (Direct and CAIO4X12). The impulse should make CAIO4X12
   **flat/dry**, like Direct, if the DSP renders it. The **stock CAIO4X12**
   (unpatched image) is the static-cab baseline.
6. **Interpret:**
   * patched CAIO4X12 == stock CAIO4X12 → the DSP ignored the block;
   * patched CAIO4X12 ≈ Direct → the IR replaced the cab model;
   * patched CAIO4X12 == stock + something → the IR was added on top;
   * silence/hang → the DSP rejected the block.
7. **Restore** if needed:

   | Goal | Updater | Notes |
   |---|---|---|
   | pre-gate CAIO4X12 | `09_builds/updater_2.1/...exe` | revision 2.1 > 2.0, default filter |
   | **stock 2.0** | `09_builds/updater_2.3_stock/...exe` | revision **2.3**, embedded image is the **stock** image (verified); default filter |
   | older 1.2/1.4 | original updater | tick **"Show all available versions"** |

   The 2.2 updater **replaced** the 2.0 revision with 2.2, so it cannot restore
   stock 2.0 directly. The 2.3 stock updater exists precisely for that; its
   embedded image is the stock `.DigBin`
   (`01d94790963a8c282fb25b322da5247b0b4b8d9b6063132b52bcf3894820a070`).
8. If no change, the next variant is **descriptor first, then IR**; if that
   also fails, compare the GSP's variable-length setup command to the RP500's
   descriptor setup.

The log lands next to the updater:
`09_builds/updater_2.2/Digitech RP Series Firmware Updater.log`.

---

## 7. Safety rules still in force

- No flash write in the experiment: the IR table is in **code space**; the
  only persistent change is the firmware image, restored by the same updater.
- Boot cannot fire: the edit buffer is zero at boot.
- The failure mode is contained to the **amp change** (not boot).
- Do not flash without the user's explicit go-ahead.
- Never test bootloader recovery destructively.

---

## 8. Git and snapshot

HEAD is this checkpoint commit; the working tree is clean. Recent history:

```
5c77553  Add a 2.3-labeled stock restore updater
0bddce6  Build the S3b hardware candidate: impulse IR on CAIO4X12
35eebcf  Add the WAV -> 44.1 kHz / 128-tap IR table converter
bb0739b  Reassess the roadmap after S3b host logic
0ee116a  Checkpoint S3b: cabinet-conditional gate passes in uCsim
194aa92  Record the full RP500 amp/cab lists and the locked acoustic pair
```

A version snapshot was cut with `04_analysis_scripts/cut_snapshot.py`; the
tag is `v2026-11-11.9`, the bundle is `99_snapshot/project.bundle`, and the
per-version manifest is under `99_snapshot/versions/2026-11-11_<head>/`.
Recover any version with `git clone 99_snapshot/project.bundle RP500-<tag>`.
