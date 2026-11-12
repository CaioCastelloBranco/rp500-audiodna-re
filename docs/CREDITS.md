# Credits

Everything in this archive was produced by an AI coding agent working from
static analysis and the user's hardware, plus a handful of open-source tools.
This file records exactly who did what.

---

## Models

Attribution comes from the OpenCode session database
(`%USERPROFILE%\.local\share\opencode\opencode.db`, SQLite). Every assistant
message row carries its model, so this is the **complete** history.

Retrieved with `04_analysis_scripts/model_credits.py`; the machine-readable
snapshot is archived at `05_evidence/model_credits.json` and can be regenerated
at any time (`python 04_analysis_scripts/model_credits.py --export ...`).

> The counts below are a snapshot taken on **2026-11-11**; they grow as the
> work continues. The archived JSON is the versioned record.

| Model | Provider | Messages | Share | Where it worked |
|---|---|---|---|---|
| **DeepSeek V4.1 Flash** (`deepseek-v4.1-flash-free`) | opencode | **767** | **38 %** | the largest single contributor: the reverse-engineering phase and a large share of the build phase |
| **MiniMax M3.1 Flash** (`minimax-m3.1-flash-free`) | opencode | **553** | 27 % | container packer, cab rename, updater patch, bank map, simulator work, flash verification, documentation |
| **Nemotron 3.5 Super VL** (`nemotron-3.5-super-vl-free`) | opencode | **201** | 10 % | early analysis and REA groundwork |
| **LongCat 2.5** (`longcat-2.5-free`) | opencode | **177** | 9 % | early analysis and REA groundwork |
| **Nemotron 3.5 Lightning** (`nemotron-3.5-lightning-free`) | opencode | **140** | 7 % | the first pass of the project, before the archive existed |
| **Crouton Alpha** (`crouton-alpha-free`) | opencode | **72** | 4 % | REA MCP bring-up and the heaviest reasoning load; the provider later deprecated this model |
| **GLM 5.3 Flash** (`glm-5.3-flash-free`) | opencode | **55** | 3 % | first pass of the project |
| **Flint 40B** (`flint-40b-free`) | opencode | **37** | 2 % | analysis and assembly work |
| **MiMo v2.6 Flash** (`mimo-v2.6-flash-free`) | opencode | **20** | 1 % | session bring-up and a few early turns |
| | | **2,022** | 100 % | |

> **2026-11-12 final consolidation.** The two-chip test, the GSP1101
> parts-list resolution (same `72-1002` AudioDNA2 in both units) and the
> documentation tidy-up were done by **DeepSeek V4.1 Flash**
> (`deepseek-v4.1-flash`) in the `D:\OPENCODE\RP500` session. The message
> counts above are the 2026-11-11 snapshot; this pass is not yet folded into
> them.

### Per session

| Session | Directory | Models (messages) |
|---|---|---|
| `Carregamento do REA MCP` — 2026-11-09 17:42 | `D:\` | crouton-alpha-free ×7 |
| `Greeting` — 2026-11-09 17:49 | `D:\` | crouton-alpha-free ×11, mimo-v2.6-flash-free ×3 |
| `Check rea status` — 2026-11-09 18:01 | `D:\` | **deepseek-v4.1-flash-free ×462**, longcat-2.5-free ×112, nemotron-3.5-super-vl-free ×63, crouton-alpha-free ×54, mimo-v2.6-flash-free ×15 |
| `Project folder lost pc` — 2026-11-10 14:42 | `%TEMP%\opencode` | nemotron-3.5-lightning-free ×140, minimax-m3.1-flash-free ×82, nemotron-3.5-super-vl-free ×61, glm-5.3-flash-free ×54, flint-40b-free ×31, mimo-v2.6-flash-free ×2 |
| `gsp1101 IR port to RP500` — 2026-11-10 18:38 → | `D:\OPENCODE\RP500` | **deepseek-v4.1-flash-free ×305**, minimax-m3.1-flash-free ×207, nemotron-3.5-super-vl-free ×77, longcat-2.5-free ×65, flint-40b-free ×6, glm-5.3-flash-free ×1 |

Variants used: everything ran on the `default` variant except
`crouton-alpha-free` and `flint-40b-free`, which ran on `high`.

All assistant output came from the `build` agent — **no sub-agents were used**.

> **Correction.** An earlier version of this file was produced from the
> OpenCode HTTP API, which caps a message page at 200 and exposes no cursor.
> That page only reached the tail of each session and missed DeepSeek
> entirely (and most of several other models). The numbers above come from
> the SQLite session database and are complete.

---

## Tools that are not models

These did the mechanical work and deserve equal credit.

| Tool | Role in this project |
|---|---|
| **Ghidra 12.1.4** | 8051 disassembly and function analysis (`8051:BE:16:default`); the decompiler behind REA's `ghidra` provider |
| **REA** (`rea-agents` 6.8.0) | agentic analysis interface. Its evidence bundles record the providers `ghidra`, `rea-analysis-view`, `rea-workflow` — **all static, none LLM-backed** |
| **SDCC 4.5.0** | mcs-51 compiler (`sdcc`), assembler (`sdas8051`), linker (`sdld`), and the **uCsim `s51` 8051 simulator** that runs the real firmware |
| **8051Enthusiast `at51`** | code/data map of every bank → the bank map |
| **8051Enthusiast `delsum`** | checksum toolbox (booted, for the bootloader-validation question) |
| **8051Enthusiast `biodiff`** | alignment hex diff |
| **ILSpy (`ilspycmd` 9.1.0.7988)** | decompilation of the updater → the reconstructed source in `07_open_source_tools/netupdaterclone_src/` |
| **Mono.Cecil** | manifest-resource extraction from the .NET bundle |
| **gdigi** (`desowin/gdigi`) | open-source RP500 SysEx protocol reference; the basis for the Super7 packing and checksum implementation |
| **Python 3.13** | all analysis and build tooling |
| **Zig 0.17.1** | host C compiler for the "compile twice" test oracle |

## People

- **The project owner** — supplied the hardware, the firmware binaries, the
  open-source uploader lineage, and every judgement call that mattered: what
  to flash, when to stop, and the decision to refuse the "flash something
  broken" experiment.
- **The author of the open-source RP500 uploader** — the source of the
  bootloader-fallback behaviour and of the claim that a bad image is not a
  brick.
- **The former DigiTech employee** who released the C48/C59/C63 GSP1101
  builds — without those three images the whole project has no reference
  implementation to diff against, and there is no vendor source for them.

## Original works

The firmware images, updater binaries and editors in `01_source_firmware/`
and `02_source_binaries/` are DigiTech/Harman/HMG products and are archived
here for interoperability research. `JUserCabUpdater vC59.exe`,
`JUpdater GSP1101vC48.exe` and `JUpdater Gsp1101vC63.exe` are unofficial
custom builds released by a third party.
