# RP500 / AudioDNA2 — reverse-engineering notes

Reverse-engineering record for the **DigiTech RP500** guitar processor
(firmware 2.0), plus a comparison against the **GSP1101** user-cabinet
feature. The original goal was to port the GSP1101's user-IR cabinets to the
RP500 by patching the firmware.

**Result: the host side is fully recovered; the port itself is not
demonstrated.** A custom firmware image can be built, repacked and flashed.
The audio core is a *parametric* DSP cabinet model, and the 25 factory
cabinets are stored as models, not as coefficients. Whether the AudioDNA2 can
*also* accept a raw coefficient block is the one question the project never
settled — and it is the question that decides whether the port is possible at
all.

A candidate image was flashed during the experiment. It bricked the unit's
boot path. The unit was recovered by reprogramming the firmware flash
externally. Both the failure and the recovery are documented here.

> **What is in this repository.** The analysis, the tooling, the board
> photographs and the recovery procedure — everything written for this
> project.
>
> **What is not.** Vendor firmware images, vendor binaries, manuals and
> decompiled vendor code are deliberately excluded. The complete corpus is
> available on request (see section 6).

---

## 1. The short version

| Question | Answer |
|---|---|
| Is the RP500 firmware modifiable? | **Yes.** Images can be built, repacked into `.DigBin`, embedded in the stock updater, and flashed over MIDI. Proven three times. |
| Is the RP500's DSP emulatable enough to test patches? | **Yes, partly.** uCsim runs the 8051 host and can inspect the DSP mailbox. It does not model the DSP audio core. |
| Can the RP500 host user IR cabinets? | **Not as shipped.** The cabinet engine is parametric. |
| Can a user IR be made to work by patching the firmware? | **Only if** the AudioDNA2 accepts a 128-tap coefficient block. No evidence that it does; strong evidence that it does not. |
| Is there a working alternative? | **Yes.** Use the RP500 as a USB audio interface with the cab sim off and run an IR loader on the host. |
| Is the hardware recoverable after a bad flash? | **Yes**, by reprogramming **U26** with an external programmer. The boot ROM is untouched by the updater. |

---

## 2. What was proven

### 2.1 Firmware pipeline (works)

- The `.DigBin` container format: `>II` records of `(address, length)` plus a
  payload, covering 16 x 64 KB = 1 MB.
- A flat 1 MB image round-trips byte-identically through the container.
- A modified image can be re-embedded into the stock MIDI updater and flashed.
  Verified on hardware.

### 2.2 Platform map (works)

- 16 x 64 KB flash banks; bank 15 holds the area used by the experiment.
- XDATA layout, bank switching, and the DSP mailbox addresses.
- The preset/bulk protocol: `0x39 MOVE_PRESET` framing, flash geometry opcode
  `0x78`, and the 12 `gdigi` message IDs in the dispatch table.
- Amp/cabinet pairing rules and the full amp/cab list.

### 2.3 GSP1101 user-cab format (works)

- 2048-byte record, 128 or 208 signed 32-bit **big-endian** taps, tap count in
  the header, mono/left toggle bit.
- Wire framing: handshake, `0x7A` chunked writes, `0x73` commit, Super7 packing.
- `tools/wav_to_ir_table.py` converts a WAV to the 44.1 kHz / 128-tap table.

### 2.4 The DSP blocker (the actual result)

- The RP500 cabinet table entry is **24 bytes** and its 104-entry parameter
  table contains only `CAB_TYPE` — a selector, not a coefficient block.
- A strict scan for stored 128-tap coefficient tables across C48, C63, RP500
  and V20 found **zero** candidates. The 25 factory cabinets are parametric
  DSP models.
- The GSP1101's user-cab feature added **no new host-to-DSP command**; it rides
  an existing channel. The RP500's command set is different and its DSP has
  never been shown to accept a raw coefficient block.
- Therefore: *a DSP that only implements parametric cab models cannot render a
  user IR.* That conditional is proven. What is **not** proven is that the
  RP500's DSP is limited to parametric models — nobody has inspected its
  loaded microcode or watched the bus during a cabinet change.
- The decisive next experiment would be a **logic-analyzer capture of the DSP
  bus during a cabinet change**: one index byte means the models are
  DSP-resident and a host-side port is blocked; a multi-hundred-byte block
  means they are host-fed and a substitution is possible. This was never
  captured.

### 2.5 What this does **not** prove

- That the AudioDNA2 has no coefficient-convolution capability.
- That no firmware patch could ever feed it a coefficient block.
- That the 24-byte descriptor is the only way the host talks to the cabinet
  block.
- That the DSP microcode cannot be replaced.

Each of these would need a bus capture, a microcode dump, or the vendor
toolchain to settle. The project stopped before any of them.

---

## 3. Hardware

Board `80-0145-A`, component side.

| Ref | Part | Role |
|---|---|---|
| U25 | AudioDNA2 (DigiTech) | main DSP / CPU, external bus |
| U24 | Samsung K4S641632N | DSP SDRAM |
| U26 | **SST29AL016J70TFI02** | 2 MB parallel NOR flash, **3.3 V**, TSOP-48 — holds the firmware |
| U19 | TAS1020B | USB audio/MIDI controller |
| U10–U13 | 74HCT574 | address latches |

Photos: `evidence/`.

**Important:** the `FFFF:FFFE` DFU device that appears when the unit fails to
boot is the **TAS1020B's ROM bootloader**, and its only target ("EEPROM") is
the TAS1020B's own I2C configuration EEPROM. It is **not** the firmware flash.
Writing to it cannot repair the unit.

---

## 4. The failure and the recovery

**What happened.** The candidate gate scanned the boot-time DSP stream for
cabinet ID `585` and injected a 512-byte impulse record in place of the stock
24-byte descriptor. Cabinet `585` is a *stock* cabinet ID used by factory
presets, so the gate armed during normal boot. The DSP stream desynchronised
and the unit powered down after the splash screen. A factory reset did not
help, because the factory preset re-armed the gate.

**Why it was not recoverable in software.** The failure prevents boot, which
prevents the MIDI updater from running. The DFU device is unrelated (above).
The only route was external programming of U26.

**Recovery.** Read U26, erase, write the stock 1 MB image at `0x000000`,
verify, reinstall. Briefs: `recovery/` (`TECHNICIAN_BRIEF.md`,
`BRIEF_TECNICO_pt-BR.md`).

**The lesson.** The worst case was priced as "reflash stock with the updater."
That was wrong: the failure mode removed the updater. Before flashing anything,
the recovery path must not depend on the firmware booting.

---

## 5. Repository map

| Path | Contents |
|---|---|
| `docs/` | the written findings — start with `docs/FINDINGS.md` |
| `tools/` | 8051 disassembler, bank tools, uCsim harness, gate, IR converter, USB/DFU probes |
| `evidence/` | board photographs, uCsim logs, model credits |
| `recovery/` | the flash-recovery briefs (English and Portuguese) |

Key documents:

- `docs/FINDINGS.md` — the main record.
- `docs/gsp1101_to_rp500_feasibility.md` — the feasibility analysis and the
  DSP blocker, with the evidence for each claim.
- `docs/rp500_bank_map.md` — flash and XDATA map.
- `docs/rp500_preset_protocol.md` — the MIDI/bulk protocol.
- `docs/rp500_storage.md` — where presets live.
- `docs/CREDITS.md` — model and tool credits for the sessions that produced
  this work.

Stock image fingerprints (the images themselves are not in this repository):

| Image | SHA-256 |
|---|---|
| stock 1 MB firmware | `718fda7de9206838d5e4945d7cff0c890c3573dc68c81142df23f7dab765fa11` |
| stock `.DigBin` container | `01d94790963a8c282fb25b322da5247b0b4b8d9b6063132b52bcf3894820a070` |

---

## 6. What is not in this repository

Deliberately excluded, because it is vendor material rather than original
work:

- the stock firmware images and the `.DigBin` container;
- the vendor updater executables and DLLs;
- the X-Edit / GSP1101 manuals and datasheets;
- the decompiled vendor code used for the protocol comparison;
- the Ghidra project and the per-bank firmware slices.

The complete corpus — including the images, the decompiled comparison and the
raw analysis artifacts — is available **on request**. Open an issue or contact
the author. Please do not redistribute the vendor material.

---

## 7. Toolchain

Python 3 (standard library only, except where noted), plus:

- `ucsim` (SDCC's 8051 simulator) for the host-side tests.
- Ghidra for the static analysis.
- `dfu-util` / `zadig` only for the TAS1020B probe.
- ILSpy for the updater decompilation.

Start at `docs/FINDINGS.md`, then `docs/gsp1101_to_rp500_feasibility.md`.
Build notes are in `docs/TOOLCHAIN.md`; the audit method is in
`docs/AUDIT_GUIDE.md`.

---

## 8. Licence

The analysis code, the write-ups and the board photographs are released under
the MIT licence. See `LICENSE.md`. No vendor material is included or licensed.

---

## 9. Resumo em português

Objetivo: portar as caixas de usuário (IRs) do GSP1101 para o RP500 via
firmware. **Resultado: o lado host está todo documentado, mas o port não foi
demonstrado.** O motor de caixas do RP500 é um modelo paramétrico no DSP, não
um convoluidor de coeficientes. A pergunta que ficou em aberto é se o
AudioDNA2 aceita um bloco de coeficientes — e é isso que decide se o port é
possível. A alternativa prática é usar o RP500 como interface de áudio USB com
a simulação de caixa desligada e um carregador de IR no computador.

Durante o experimento a unidade foi brickada e recuperada regravando o flash
**U26** (`SST29AL016J`, TSOP-48, 3,3 V) com um gravador externo. O dispositivo
DFU `FFFF:FFFE` é o bootloader do **TAS1020B** e não tem relação com o firmware.

Este repositório público traz a análise, as ferramentas, as fotos e o
procedimento de recuperação. Imagens de firmware e material do fabricante não
estão incluídos; o acervo completo está disponível sob solicitação.
