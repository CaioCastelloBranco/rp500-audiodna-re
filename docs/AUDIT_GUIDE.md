# Version store and audit guide

The project has no remote, so **versions are kept inside this folder**, under
`99_snapshot/`. This file is the stable, tracked guide; the store itself is
untracked (`.gitignore`) so a snapshot never contains an older snapshot.

```
99_snapshot/
    README.md                      generated index of every version cut
    project.bundle                 cumulative git history (all versions)
    versions/
        2026-11-11_941da76/
            MANIFEST.sha256        byte-exact content of that version
            NOTES.md               commit, tag, sizes, gate results
```

**One bundle serves every version.** The history is cumulative, so rather than
storing another 220 MB copy of the tree per version, each version keeps a
**manifest** (a text file of SHA-256 hashes) and the bundle keeps the content.
Clone the bundle and check out a tag to get any version back exactly.

## The invariant that makes both recovery paths work

> **The tracked set is exactly the manifest set** — every file in the project
> except `__pycache__/` and `99_snapshot/`.

Two consequences, both verified end to end:

- a **folder copy** verifies against a version manifest, byte for byte;
- a **clone from the bundle** verifies against the *same* manifest — 0 missing,
  0 extra, 0 changed — and passes the three gates (253/253, 115/115, 7/7).

That is why `ghidra_proj/` is tracked (a bundle without it failed
`verify_all.py`) and why `.gitattributes` carries `* -text`: a fresh clone does
not inherit the repository-local `core.autocrlf=false`, and without the rule a
clone rewrites LF as CRLF (`usercab_encode.py` came out 8634 bytes instead of
8405). Both defects were found by recovering a version and running the gates on
it, not by inspection.

## Cutting a version

```powershell
cd D:\OPENCODE\RP500
python verify_all.py                        # 253/253
python 04_analysis_scripts\audit_claims.py  # 115/115
python 04_analysis_scripts\prove_claims.py  #   7/7

git add -A
git commit -m "what changed"
git tag -a v2026-11-11 -m "why this version matters"

python 04_analysis_scripts\cut_snapshot.py  # manifest + bundle + notes + index
```

`cut_snapshot.py` refuses to cut a dirty tree (use `--force` to override),
re-runs the three gates itself and records their results in `NOTES.md`.

## Listing and verifying

```powershell
python 04_analysis_scripts\cut_snapshot.py --check

# verify the CURRENT tree against one version's manifest
python 04_analysis_scripts\snapshot_manifest.py --verify `
       --manifest 99_snapshot\versions\2026-11-11_9144fe9\MANIFEST.sha256
```

`snapshot_manifest.py --verify` reports **missing / extra / changed** and ends
with `VERDICT: IDENTICAL` or `VERDICT: DIFFERS`. It works on a copy:

```powershell
python 04_analysis_scripts\snapshot_manifest.py --verify `
       --root E:\audit\RP500 `
       --manifest E:\audit\RP500\99_snapshot\versions\<folder>\MANIFEST.sha256
```

## Taking an audit copy off the machine

```powershell
robocopy D:\OPENCODE\RP500  E:\audit\RP500  /E /COPY:DAT /DCOPY:T /R:1 /W:1
cd E:\audit\RP500
python 04_analysis_scripts\snapshot_manifest.py --verify `
       --manifest 99_snapshot\versions\<folder>\MANIFEST.sha256
python verify_all.py
python 04_analysis_scripts\audit_claims.py
python 04_analysis_scripts\prove_claims.py
```

Byte-identical **and** behaviourally identical is the bar: the manifest covers
the bytes, the three gates cover the behaviour.

## Getting an old version back

```powershell
git clone 99_snapshot\project.bundle RP500-v2026-11-11
cd RP500-v2026-11-11
git checkout v2026-11-11          # or a version folder name: 2026-11-11_9144fe9
git log --oneline --graph
git show v2026-11-11:06_deliverable/FINDINGS.md
```

A bundle clone is byte-identical to the folder, so the **same manifest**
verifies it — and the three gates pass from it:

```powershell
python 04_analysis_scripts\snapshot_manifest.py --verify `
       --manifest <path to a version folder>\MANIFEST.sha256
python verify_all.py
python 04_analysis_scripts\audit_claims.py
python 04_analysis_scripts\prove_claims.py
```

## Reading order for an auditor

1. `00_master/PROJECT_STATE.md` — done, open, next.
2. `06_deliverable/FINDINGS.md` — findings and the corrected model.
3. `05_evidence/claims_ledger.md` — **what changed, with a test per claim**.
4. `06_deliverable/rp500_storage.md`, `rp500_preset_protocol.md` — the preset
   storage question: measured, revised, still open.
5. `06_deliverable/rp500_firmware_roadmap.md` — the plan and the one gate.
6. `00_master/TOOLCHAIN.md` — restoring the environment.

## Limitations to keep in mind

- **Pre-revision documents are not recoverable.** Version control starts at
  `baseline-2026-11-11`; `claims_ledger.md` is the substitute for that history.
- **The one open gate is the DSP** (G1/G2 in the roadmap): whether the RP500's
  AudioDNA2 accepts a variable-length block *and* convolves with it. No amount
  of firmware analysis answers it — it needs S3 on hardware.
- **The storage location was revised twice** in the 2026-11-11 revision:
  "inside the AudioDNA2" was withdrawn for "an external serial store, not yet
  located". Both are recorded in `rp500_storage.md` §4 and
  `rp500_preset_protocol.md` §5.
- **Everything was verified by one analyst's tooling**, in one session, with no
  second reviewer. The mitigations are listed in the roadmap's risk register,
  which puts the residual interpretation risk at 3–5%.
