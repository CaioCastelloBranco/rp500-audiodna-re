# RP500 Bank Map

Phase 0 item 1 of `rp500_firmware_roadmap.md`: the banking mechanism, the
entry trampoline, and the vectors. Everything here is re-derived by
`04_analysis_scripts/bank_map.py` from the stock images; nothing is asserted
from memory.

```
python 04_analysis_scripts/bank_map.py
```

---

## 1. Layout

| Fact | Value |
|---|---|
| Image | 1 MB = 16 banks x 64 KB (`0x10000` each) |
| Identical prefix across all 16 banks | **0x2C80** bytes (v2.0); 0x2B00 (v1.2, v1.4) |
| Identical suffix across all 16 banks | none (0 bytes) |
| Bank-select table | `0x0200`..`0x027B`, identical in **every** bank of **every** build |

The first ~11 KB of each bank is the same bytes in all 16 banks: the reset and
entry trampoline plus the bank-switch machinery, replicated by the build.
Everything past that point is bank-specific.

## 2. Bank select — P1 low nibble

At `0x0200` sits a 16-entry table, 8 bytes per entry:

```
0200  75 90 f0     MOV  P1,#0F0h      ; bank 0
0203  22           RET
0204  ff ff ff ff                      ; padding
0208  75 90 f1     MOV  P1,#0F1h      ; bank 1
...
0278  75 90 ff     MOV  P1,#0FFh      ; bank 15
027B  22           RET
027C  e5 90 ...                       ; code follows immediately (no padding)
```

Entries 0..14 are followed by 4 bytes of `0xFF` padding; entry 15 is followed
directly by the code at `0x027C`.

- **P1 (SFR `0x90`) low nibble = bank number**, high nibble held at `0xF`.
- The entries are callable: `LCALL 0x0200 + 8*n` selects bank *n* and returns.
- The active bank is also published **outward** to another chip:

```
00BF  e5 90        MOV  A,P1
00C1  54 0f        ANL  A,#0Fh
00C3  90 fd a2     MOV  DPTR,#FDA2h
00C6  f0           MOVX @DPTR,A       ; external reg 0xFDA2 = current bank
```

- `0x027C` reads P1 back and rotates the nibble (`SWAP A` / `RR A`) — a bank
  arithmetic helper (e.g. "next" / "half" bank).

## 3. The common prefix (`0x0000`..`0x2C7F`)

| Range | Content |
|---|---|
| `0x0000`..`0x00FF` | Entry stubs: `LJMP`/`AJMP`/`ACALL` with `0xFF` padding, one per call gate |
| `0x006D` | Dispatcher head: `MOV P1,#FF` -> `MOV DPTR,#0000` -> `MOVC A,@A+DPTR` -> `SUBB A,#EAh` -> `JZ 00A0` — tests whether the selected entry is an `LJMP` (`0xEA`) opcode (the direct-jump fast path) |
| `0x0091` | `MOV DPTR,#D01Fh; MOV A,#A0h; MOVX @DPTR,A` — DSP host-port write (registers `0xD01E`/`0xD01F`/`0xD020` are the host ports, see report appendix) |
| `0x00BF`..`0x01FF` | Bank publish to `0xFDA2`, then table walks (`MOVC` through DPTR) and `LCALL 0x03AC` |
| `0x0200`..`0x027B` | The bank-select table (§2) |
| `0x03AC` | Dispatcher helper called from the entry path |
| `0x03B5` | Call-gate table region (entries such as `02 00 73`) |

The `MOVC A,@A+DPTR` walks at `0x00CC`..`0x0119` read the call-gate table out
of code space and publish results to external registers `0xFDA0`/`0xFDA2`/
`0xFDA3`/`0xFDA4` — that is how a call site resolves a target that may live in
another bank.

## 4. Code / data map (`at51 stat`, 512-byte blocks)

`at51` classifies each block: **C** = all jumps aligned (pure 8051 code),
**M** = mixed (code with embedded tables), **D** = no jumps at all (data).

| Bank | C | M | D | Largest 0xFF run |
|---|---|---|---|---|
| 0 | 16 | 77 | 35 | `0x3942` @ `0xC6BE` |
| 1 | 16 | 58 | 54 | **`0x5FD0` @ `0xA030`** |
| 2 | 16 | 58 | 54 | `0x5FD0` @ `0xA030` |
| 3 | 15 | 1 | 112 | `0x0B64` @ `0xF49C` |
| 4 | 39 | 18 | 71 | `0x33EC` @ `0xCC14` |
| 5 | 81 | 28 | 19 | `0x169B` @ `0xE965` |
| 6 | 41 | 75 | 12 | `0x0C4D` @ `0xF3B3` |
| 7 | 85 | 24 | 19 | `0x1423` @ `0xEBDD` |
| 8 | 27 | 84 | 17 | `0x1738` @ `0xE8C8` |
| 9 | 19 | 89 | 20 | `0x1AD1` @ `0xE52F` |
| 10 | 17 | 93 | 18 | `0x19CF` @ `0xE631` |
| 11 | 27 | 92 | 9 | `0x0624` @ `0xF9DC` |
| 12 | 16 | 103 | 9 | `0x0700` @ `0xF900` |
| 13 | 16 | 97 | 15 | `0x12AA` @ `0xED56` |
| 14 | 60 | 15 | 53 | `0x5D7E` @ `0xA280` |
| 15 | 88 | 18 | 22 | `0x1F69` @ `0xE095` |

Bank 3 is almost entirely data (112 D blocks) — a pure data bank. Banks 5, 7
and 15 are code-heavy.

## 5. Free space (exact)

The biggest contiguous `0xFF` run in the whole image is **`0x5FD0` bytes at
bank 1 offset `0xA030`** (bank 2 has the identical run). That is the single
best place for Phase 1 stubs and for the user-cab store:

| Need | Size | Fits in `0x5FD0`? |
|---|---|---|
| 10 user slots x `0x800` | `0x5000` (20 KB) | yes, with `0xFD0` spare |
| Dispatcher stub + storage index | ~`0x100` | yes |
| Compact slots (`0x200` each) | `0x2000` | yes, comfortably |

`0x50000`..`0x54FFF` (the GSP1101 user window) is *not* where the RP500 keeps
free flash — that address range is inside bank 5. The `0x5FD0` run above is the
real RP500 free space, and it lives in banks 1 and 2.

## 6. The reset path, observed by execution

Running the real image in the uCsim 8051 simulator
(`04_analysis_scripts/rp500_ucsim_run.py --bank 0 --steps 20000000 --extra ds`)
shows the reset path in action:

```
0000  LJMP 0002            ; reset vector
0002  LJMP 006B            ; -> dispatcher
006B  MOV  P1,#0FFh        ; bank 15
...
00A0  LJMP 22FB
22FB  MOV  DPTR,#0D01Fh    ; DSP host port
22FE  MOV  A,#0A0h
2300  MOVX @DPTR,A         ; DSP reset/handshake write
2301  MOV  DPTR,#0F000h    ; clear XRAM 0xF000..0xFFFF
2310  MOV  R0,#0FEh        ; clear IRAM 0xFE down to 0x00
2319  MOV  SP,#3Fh
231C  LJMP 242B            ; into the app
```

**P1 = `0xFF` after the run, i.e. the reset path selects bank 15.** The bank
table is not theory — the firmware uses it on every reset.

### 7.1 Confirmed by execution (Stage A.1)

uCsim can attach a command to a breakpoint, so the simulator can perform the
bank switch itself: every `MOV P1,#imm` site becomes a breakpoint on the
instruction *after* the MOV, with `file "bankNN.hex"` attached. The whole
experiment is handed to uCsim as a command script.

| Fact | Value |
|---|---|
| `MOV P1,#imm` sites in the image | **27** (20 in the replicated prefix, 7 bank-specific) |
| Prefix sites | `0x006B` (→bank 15), `0x007C` (→12), `0x0093` (→14), `0x2348` (→15), and the 16-entry table at `0x0200` (→0…15) |
| Bank-specific sites | bank 5: `0x7CD4`→11, `0xE154`→13; bank 6: `0xF2AF`→13; bank 7: `0xAC73`→9; bank 14: `0x32CD`→15; bank 15: `0x3346`→15, `0x7162`→13 |
| Bank switches executed | **3,001** |
| Spurious hits (site was not a P1 write in the mapped bank) | **0** |
| Banks actually visited | 0 and 15 — the reset path selects 15, then the firmware polls inside it |
| Where the time goes | 2,999 of 3,000 stops are the bank-15 table entry (`0x027B`) — the main loop keeps re-selecting bank 15, i.e. it is **waiting for hardware** |

That last row is the next thing to attack: the firmware blocks on something in
bank 15 that does not exist in a simulator (the DSP handshake or the USB
endpoint), which is Stage A.2 — modelling the DSP host ports so the wait
loops terminate.

Tool: `04_analysis_scripts/rp500_ucsim_banks.py`. Log:
`05_evidence/2026-11-11_ucsim_bankswitch.log`.

The simulator has no P1-driven bank remap of its own, no DSP and no USB, so
execution past the first hardware touch is structurally right but electrically
wrong. It is a pre-flash validation bench, not a system emulator.

## 8. The DSP handshake the firmware is waiting for (Stage A.2)

With the bank switch modelled, the firmware still spun: 2,999 of 3,000 stops
were the bank-15 table entry at `0x027B`. The reason is visible in bank 15:

```
BE13  MOV  DPTR,#0D06Eh
BE16  MOVX A,@DPTR        ; read the DSP status register
BE17  MOV  2Fh,A
BE19  MOV  DPTR,#0FDFCh
BE1C  MOVX A,@DPTR
BE1D  ORL  A,#01h
BE1F  MOVX @DPTR,A        ; host command byte
BE20  MOV  DPTR,#0E000h
BE23  MOVX @DPTR,A        ; latch it into the DSP
BE44  MOV  DPTR,#0D06Eh
BE47  MOVX A,@DPTR        ; read the status again
BE48  MOV  2Fh,A
BE4A  SJMP BE29           ; loop until the status CHANGES
```

So the AudioDNA2T host protocol is: **write a command to `0xE000` (with the
command byte staged in `0xFDFC`), then poll the status register `0xD06E` until
the DSP changes it.** With no DSP present the status never changes, so the
firmware waits forever.

### The model

uCsim can attach a command to a breakpoint, so the simulator can play the DSP's
part:

```
break  xram w 0xe000
commands <nr> expression xram[0xd06e]=xram[0xd06e]+1
```

Every host command now bumps the status register, which is what a real DSP
does when it acknowledges.

| Run | Bank switches | DSP host writes | Outcome |
|---|---|---|---|
| model **off** | 300 | 2,701 | firmware **hangs** in the status poll |
| model **on** | 3,300 | 2,701 | firmware keeps running (main loop) |

The DSP write count is identical in both runs — that burst is the DSP init
sequence, which happens before the poll. The difference is what happens
*after*: without the acknowledgement the firmware never leaves the poll.

Other DSP host ports seen in the same region: `0xD01F` (handshake, written
`0xA0` at reset), `0xD020` (mailbox), `0xD070` (the DSP **parameter-descriptor**
stream — 24 bytes, code-sourced; corrected 2026-11-11, report §13.10),
`0xD05A`/`0xD05B`, `0xE200`/`0xE400`/`0xE800`.

Tool: `04_analysis_scripts/rp500_ucsim_dsp.py` (`--no-model` for the A/B).
Logs: `05_evidence/2026-11-11_ucsim_dspmodel.log`, `05_evidence/dsp_model.cmd`.

Caveat: the acknowledgement is crude — it bumps the whole status byte rather
than setting the exact bits a real AudioDNA2T would. It is enough to get the
firmware moving; a faithful DSP model is a later refinement.

## 9. Still open

1. Which P1 bits above the nibble do — `0xF0` base suggests bits 4-7 carry
   other selects (the DSP / USB / flash chips share the port).
2. Whether `0x006D` is the reset path or only the "call a gate" path.
3. The exact entry semantics of the LJMP table at `0x0000`.
4. **Bootloader location and validation** — Phase 0 item 4, still to do.
5. Which interrupt vectors are in use, and where the USB-MIDI endpoint code
   lives (does it run on this 8051 or on the DSP?).
6. Whether the free run in banks 1/2 is truly unused, or holds code that is
   only reached under conditions `at51` cannot see.
