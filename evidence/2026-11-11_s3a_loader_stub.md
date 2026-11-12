# S3a — the IR loader, proved in the simulator (no hardware)

**Result: PASS.** A 26-byte gate plus a 512-byte table, built on the *stock*
RP500 firmware, makes the DSP data port receive exactly:

```
512 bytes, in order, then 0xF5, then nothing — twice
```

Reproduce: `python 04_analysis_scripts/s3a_loader_stub.py`
Log: `05_evidence/2026-11-11_s3a_loader_stub.log` · script sent to uCsim:
`05_evidence/s3a.cmd`

---

## Why this matters

The port's host half is the part we can control. S3a proves it end to end
under uCsim, so a negative result on hardware (S3b) means *the DSP*, not our
code. Without this, a silent DSP is ambiguous between "no IR support" and "our
stub is wrong".

## What was built

539 bytes differ from stock, all inside provably-unused space:

| # | Edit | Bytes | Where |
|---|---|---|---|
| 1 | source base → the test table (`ADD A,#lo` / `MOV A,#hi`) | 2 | bank 15 `0xBE9F`, `0xBEA3` |
| 2 | byte-send entry → the gate (`LJMP 0xE095`) | 3 | bank 15 `0xBE97` |
| 3 | the gate | 26 | bank 15 `0xE095` |
| 4 | the 512-byte table | 512 | bank 15 `0xE100` |

The stock routine's **handshake, DSP setup helper and exit are untouched** —
only the source and the termination are ours.

## The gate (26 bytes)

```
E095  MOV  DPTR,#0FF24h      ; the stock 16-bit byte counter (high)
E098  MOVX A,@DPTR
E099  CJNE A,#02h,+4         ; high != 2  -> stock path
E09C  INC  DPTR
E09D  MOVX A,@DPTR           ; low
E09E  JZ   +6                ; high==2 and low==0 -> counter == 0x0200
E0A0  MOV  DPTR,#0FF24h      ; stock path: restore DPTR and rejoin
E0A3  LJMP 0BE9Ah
E0A6  MOV  DPTR,#0D070h      ; terminate
E0A9  MOV  A,#0F5h
E0AB  MOVX @DPTR,A
E0AC  LJMP 0BEB0h            ; the stock epilogue (INC 38h x2 ; RET)
```

## What the simulator showed

```
bytes captured at 0xD070: 1026  (2 complete passes of 512 + 0xF5)
  first 512 bytes are the table, in order : True
  byte 513 is 0xF5 (the terminator)       : True
  0xF5 appears only as a terminator      : True
  counter at exit was 0x0200 (= 512)      : True
  exit through the stock epilogue 0xBEB0 : True
```

The firmware invokes the stream routine **twice** (once per cabinet bank); each
pass is a clean 512 + `0xF5`. The table pattern excludes `0xF5` on purpose, so
the terminator cannot be confused with data.

## What it does not prove

- **Nothing about the DSP.** The model always acknowledges; it cannot say
  whether a real AudioDNA2 accepts or renders the block. That is S3b.
- Not the real handshake timing, and not that the DSP wants `0xF5` at all —
  that is the GSP's convention, applied by analogy.
- The simulator's copy of the image also has the *ready-flag read* redirected
  to a scratch cell (two DPTR immediates), because in the real DSP reading and
  writing `0xD070` are different registers. That patch is **simulator-only**
  and is not part of the candidate build.

## What S3b would reuse

Everything above except the ready-flag redirection, plus:

- a hook that fires on **one cabinet select** instead of at boot;
- a **real 128-tap IR** (`usercab_encode.py`, 128 × int32 BE) instead of the
  test pattern;
- the stock image kept on disk, restore via the same updater.

Then: select that cabinet and listen. Cab goes dry (zeros) or changes (real IR)
= the DSP accepted and applied the block; nothing changes = the DSP did not,
and the next variant is to send the descriptor first, as the GSP does.
