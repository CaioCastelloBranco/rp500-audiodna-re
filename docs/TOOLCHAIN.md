# Toolchain and environment

Everything this project needs to be re-run, and how to restore it. Machine
state as of **2026-11-11**.

---

## System-installed (restore with winget / installer)

| Tool | Version | Install | Path | Used for |
|---|---|---|---|---|
| **SDCC** | 4.5.0 | `winget install SDCC.SDCC` | `C:\Program Files\SDCC\bin` | mcs-51 **compiler** (`sdcc.exe`), assembler (`sdas8051.exe`), linker (`sdld.exe`), uCsim simulator (`s51.exe` 0.8.15) |
| **Zig** | 0.17.1 | `winget install zig.zig` | `%LOCALAPPDATA%\Microsoft\WinGet\Packages\zig.zig_…\zig-x86_64-windows-0.17.1\zig.exe` | host C compiler (`zig cc`) — the test oracle for the "compile twice" build |
| **.NET runtimes** | 6.0.36 / 8.0.22 / 10.0.14 | pre-existing | `C:\Program Files\dotnet` | running `ilspycmd`, the .NET updater |
| **Ghidra** | 12.1.4 PUBLIC | pre-existing | `D:\Antigravity\ghidra_12.1.4_PUBLIC` | 8051 disassembly (`8051:BE:16:default`), headless analysis |
| **Python** | 3.13.2 | pre-existing | `%LOCALAPPDATA%\Programs\Python\Python313` | all analysis scripts |
| **PowerShell** | 5.1.19041 | pre-existing | — | Mono.Cecil resource extraction, `verify_all` glue |
| **REA** | — | MCP server | — | managed/binary analysis through the `tools.rea.*` interface |
| **Git** | 2.56.0 | `winget install Git.Git` | `C:\Program Files\Git\cmd` | version control for the whole archive |

> **No .NET SDK is installed** (only runtimes). The updater was therefore
> *patched*, not rebuilt — see `06_deliverable/rp500_firmware_roadmap.md`,
> "Updater integration". If a source rebuild is ever wanted, install the
> .NET 10 SDK; the reconstructed source in
> `07_open_source_tools/netupdaterclone_src/` is the starting point.
>
> **This folder IS a git repository** since 2026-11-11 (`git init -b main`).
> The repository is configured to store every file **byte-exact**
> (`core.autocrlf false`), so the analysis can be replayed against exactly the
> bytes that were analysed. The baseline commit is tagged
> `baseline-2026-11-11`. See "Version control" below.

## Version control

```powershell
cd D:\OPENCODE\RP500

git status                 # what changed since the last commit
git diff                   # the actual edits
git log --oneline --graph  # history
git show <rev>:<path>      # a file exactly as it was at that revision

# the normal loop: verify, then commit
python verify_all.py
python 04_analysis_scripts\audit_claims.py
python 04_analysis_scripts\prove_claims.py
git add -A
git commit -m "what changed and why"

# cut a version into 99_snapshot/ (manifest + bundle + notes + index)
python 04_analysis_scripts\cut_snapshot.py
python 04_analysis_scripts\cut_snapshot.py --check
```

| Setting | Value | Why |
|---|---|---|
| `core.autocrlf` | `false` | line endings are **not** rewritten — the archive stays byte-exact |
| `core.safecrlf` | `false` | no CRLF warnings on check-out |
| `core.fsmonitor` | `false` | reliable status on this filesystem |
| `gc.auto` | `0` | no background repacking mid-session |
| `user.name` / `user.email` | `RP500 Project` / `rp500-project@localhost` | **repository-local only**; change with `git config user.name "…"` |

Tracked: everything, including the firmware images, the shipped binaries and
the build outputs — they are the *inputs and results* of the analysis and
must not drift. Excluded by `.gitignore`: `ghidra_proj/` (Ghidra databases —
generated, binary, churn on every session; the importable per-bank dumps in
`08_ghidra_banks/` **are** tracked) and `__pycache__/`.

The repository is local to this machine; there is no remote. If one is wanted:
`git remote add origin <url>` + `git push -u origin main`.

**Versions are kept in the folder too**, in `99_snapshot/` (untracked, so a
snapshot never contains an older snapshot): one folder per version with a
SHA-256 manifest and notes, plus a single cumulative `project.bundle` carrying
the whole history. Cut and list them with
`04_analysis_scripts/cut_snapshot.py` (`--check`). Full procedure, the
copy-and-audit steps and the audit reading order: **`00_master/AUDIT_GUIDE.md`**.

## Archived in this project (no installation needed)

| Path | What | Version |
|---|---|---|
| `07_open_source_tools/at51/at51.exe` | 8051 RE toolkit (code/data map) | 1.1.1 |
| `07_open_source_tools/delsum/delsum.exe` | checksum toolbox | 1.0.0 |
| `07_open_source_tools/biodiff/biodiff.exe` | alignment hex diff | 1.2.1 |
| `07_open_source_tools/ilspycmd/` | .NET decompiler (+ `Mono.Cecil.dll`) | 9.1.0.7988 |
| `07_open_source_tools/gdigi/` | RP500 SysEx protocol reference source | — |

Hashes and licences: `07_open_source_tools/README.md`.

---

## How to run everything

```powershell
cd D:\OPENCODE\RP500

# 1. verify the whole archive (253 checks)
python verify_all.py

# 2. rebuild the firmware container and the patched image
python 04_analysis_scripts\digbin_pack.py verify 01_source_firmware\rp500V20.DigBin
python 04_analysis_scripts\patch_cab_name.py --old DIGISPKR --new CAIO4X12

# 3. rebuild the patched updater (2.1 revision)
python 04_analysis_scripts\patch_updater.py

# 4. bank map (bank select, code/data map, free space)
python 04_analysis_scripts\bank_map.py

# 5. 8051 test bench: assemble -> link -> run under uCsim -> compare with Python
python 04_analysis_scripts\ucsim_check.py

# 6. run a real firmware image in the simulator
python 04_analysis_scripts\rp500_ucsim_run.py --bank 0 --steps 200000 --extra ds

# 7. host build of the portable wire logic (needs zig)
zig cc -O2 -o %TEMP%\wire_host.exe 04_analysis_scripts\usercab_wire.c
%TEMP%\wire_host.exe

# 8. restore the updater's embedded resources into the reconstructed source
powershell -ExecutionPolicy Bypass -File 04_analysis_scripts\extract_updater_resources.ps1
```

`patch_updater.py`, `bank_map.py` and `ucsim_check.py` need SDCC on `PATH` for
the last one; add `C:\Program Files\SDCC\bin` first.

## Simulator notes (learned the hard way)

- uCsim: **all options must come before the image file**, otherwise they are
  parsed as filenames. Use `-t 52` (not `-t 51`) and `-X 12M`.
- uCsim's `dump`/`di`/`dx` commands address spaces that are **not** the ones
  the 8051 core actually uses for `MOVX` or for direct writes. Leave results in
  **registers** and read the simulator's final state dump — that channel is
  exact.
- SDCC's `crt0` startup does not cooperate with ucsim's split RAM model
  (IRAM `0x00-0x7F`, SFRs `0x80-0xFF`): its idata init loop spins. Use
  freestanding code (assemble + link, no C runtime) — which is what Phase 1
  needs anyway.
- `sdas8051` needs `-o file.rel`; `sdld -i out.ihx obj.rel` links cleanly when
  every address is an absolute immediate.
- uCsim keeps its console open after the `-e` commands; the harness scripts
  read the output and then kill the process.

## Ghidra

```
D:\Antigravity\ghidra_12.1.4_PUBLIC\support\analyzeHeadless.bat
```

Language for the 8051 images: `8051:BE:16:default`. REA cannot open raw 8051
binaries — Ghidra does that job. `d51.py` (in `04_analysis_scripts/`) is the
fast disassembler for spot checks; note its calling convention:
`disasm(data, base=0, start=<file_offset>)`.
