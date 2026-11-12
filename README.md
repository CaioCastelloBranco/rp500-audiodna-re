# RP500 / AudioDNA2 — reverse-engineering notes

Reverse-engineering record for the **DigiTech RP500** guitar processor
(firmware 2.0), plus a comparison against the **GSP1101** user-cabinet
feature. The original goal was to port the GSP1101's user-IR cabinets to the
RP500 by patching the firmware.

**Result: the host side is fully recovered; the port itself is not
demonstrated.** A custom firmware image can be built, repacked and flashed.
The audio core is a *parametric* DSP cabinet model, and the 25 factory
cabinets are stored as models, not as coefficients. Whether the AudioDNA2 can
*also* accept a variable-length coefficient block is the one question the
project has not settled — and it is the question that decides whether the port
is possible. **"Not demonstrated" is the finding; "impossible" is not.**

A candidate image was flashed during the experiment. It bricked the unit's
boot path. The unit was recovered by reprogramming the firmware flash
externally. Both the failure and the recovery are documented here.

---

## 0. What we did, in two minutes

1. **Recovered the platform.** The RP500 firmware was extracted, mapped,
   repacked into the stock `.DigBin` container, embedded in the stock updater
   and flashed on hardware. The unit was bricked once and recovered by
   external programming of the firmware flash (U26).
2. **Found what the DSP actually receives.** The RP500's cabinet payload is a
   **24-byte parameter descriptor**, identical in both cabinet banks and
   immediately followed by code — not an IR table. The factory cabinets are
   **parametric DSP models**; there are no factory impulse responses anywhere
   in the product family.
3. **Found how the GSP1101 does user IRs.** Its user cabinets ride a
   **variable-length, `0xF5`-terminated, XRAM-sourced stream** to the DSP data
   port `0xD070`. The RP500 firmware has **none** of that path.
4. **Showed the path is old, not an IR trick.** The oldest GSP1101 build
   (v11) already contains the identical transport, with only the scratch
   addresses moved. C48/C63 added the host-side feature, not the DSP primitive.
5. **Killed the "special chip" theory.** The GSP1101 firmware never selects
   between its two DSPs, and its parts list shows **2 × `72-1002` Audio DNA2
   Rev B** — the **same base part** as the RP500's single U25
   (`72-1002 GREEN`). The second chip is capacity, not a different instruction
   set. (`evidence/2026-11-12_gsp1101_parts_list.md`)
6. **Narrowed the gate to one measurement.** The same ASIC means the RP500's
   chip has the same *hardware* potential. What is unknown is whether its
   firmware can put the DSP into the variable-length block mode and make it
   convolve. That is testable on the unit; it is not a static-analysis
   question.

**What is left:** one controlled hardware experiment (send a known 512-byte
block and listen, with the recovery image ready), or a logic-analyzer capture
of a GSP1101 user-cab load, or the DSP microcode/ISA. The host-side loader is
already proven in the simulator
(`evidence/2026-11-11_s3a_loader_stub.md`).

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
| Can a user IR be made to work by patching the firmware? | **Not demonstrated either way.** The host side is buildable; the open question is whether the AudioDNA2 accepts a variable-length block and convolves. The GSP1101 uses the **same `72-1002` ASIC** and does convolve, so the remaining doubt is microcode/enablement, not chip identity. |
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

### 2.5 The two-chip question (settled 2026-11-12)

The GSP1101 has **two** AudioDNA2 chips and the RP500 has **one**, which raised
the hypothesis that only one GSP chip carries the convolution instructions.

- **The firmware never addresses them independently.** The GSP's "32 XRAM
  stores" are **2 interrupt handlers × 16 code banks**, both reading one stream
  and writing one port `0xD070`. `0xFDFC` — once claimed as the GSP's second-chip
  select — is **RP500-only** (49 refs; 0 in every GSP build).
- **The parts list closes it.** The GSP1101 BOM lists **2 × `72-1002` "IC Audio
  DNA2 Rev B ASIC 144 pin LQFP"**; the RP500's U25 is the same base part
  (`72-1002 GREEN`). The two GSP chips are the same revision as each other, so
  they cannot differ either. The second chip is **capacity** (two DSP + two
  64 Mbit SDRAM subsystems, with an EPM3032A CPLD for address decode), not a
  different instruction set.
- **The sibling BOMs show the pattern:** GNX 2 = 3 × `72-5433` (first-gen
  AudioDNA), RP50 = 1 × `72-5433`, GSP1101 = 2 × `72-1002`, RP500 =
  1 × `72-1002`. The DSP count is a tier choice.

Evidence: `evidence/2026-11-12_gsp_two_chip_test.md`,
`evidence/2026-11-12_gsp1101_parts_list.md`.

### 2.6 What this does **not** prove

- That the RP500's `72-1002` is a *different* chip from the GSP's — the parts
  list says it is the same base part.
- That the AudioDNA2 has no coefficient-convolution capability.
- That no firmware patch could ever feed it a coefficient block.
- That the 24-byte descriptor is the only way the host talks to the cabinet
  block.
- That the DSP microcode cannot be replaced.

What remains is **one measurement**: whether the RP500's `72-1002` can be put
into the variable-length block mode and made to convolve. A bus capture, a
microcode dump, or a bench test would settle it. The host-side half is already
proven in the simulator (`evidence/2026-11-11_s3a_loader_stub.md`).

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
firmware. **Resultado: o lado host está todo documentado e uma imagem
modificada pode ser gerada e gravada; a renderização do IR no DSP não foi
demonstrada.** O motor de caixas de fábrica do RP500 é um modelo paramétrico no
DSP. O GSP1101 usa o **mesmo ASIC `72-1002`** e faz convolução com IRs de
usuário, então a dúvida restante é de microcódigo/habilitação, não de
identidade do chip. Falta uma medição: se o `72-1002` do RP500 aceita um bloco
de comprimento variável e convolve com ele. A alternativa prática, se a medição
falhar, é usar o RP500 como interface de áudio USB com a simulação de caixa
desligada e um carregador de IR no computador.

Durante o experimento a unidade foi brickada e recuperada regravando o flash
**U26** (`SST29AL016J`, TSOP-48, 3,3 V) com um gravador externo. O dispositivo
DFU `FFFF:FFFE` é o bootloader do **TAS1020B** e não tem relação com o firmware.

Este repositório público traz a análise, as ferramentas, as fotos e o
procedimento de recuperação. Imagens de firmware e material do fabricante não
estão incluídos; o acervo completo está disponível sob solicitação.
