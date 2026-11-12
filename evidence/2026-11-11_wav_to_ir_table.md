# WAV → 44.1 kHz / 128-tap IR table (2026-11-11)

## Why the C63 software is not used as the converter

The only WAV converter in the shipped C63/GSP tooling is
**`JUserCabUpdater vC59.exe`**. It is a **GUI / MIDI uploader**, not a batch
tool:

- it needs a MIDI device and a wizard interaction (select file, select slot,
  store);
- it builds a **2048-byte device record** and **sends it over SysEx** to the
  GSP1101 — it has no documented encode-only / CLI mode;
- it does not output a standalone **512-byte DSP coefficient table** for our
  firmware gate.

The C63 **X-Edit** does not convert WAVs; the **GSP updater** is firmware only.

So the batch converter is `04_analysis_scripts/wav_to_ir_table.py`, which
reproduces the loader's coefficient path (recovered from the vC59
disassembly): 44.1 kHz, left/mono channel, 16-bit `<<12` / 24-bit `<<4` /
32-bit `>>4`, optional gain dB, 4-byte big-endian signed taps. The optional
`--record` output matches the loader's 2048-byte record layout (header at 4,
coefficients at `0x10`, count at `0x0C`, name at `0x7E7`, trailer at `0x7FE`).

The loader itself still has the final say on the **full record** path (S4b);
this script is the offline batch version for the experiment.

## Usage

```
python 04_analysis_scripts/wav_to_ir_table.py in.wav out.bin --taps 128
python 04_analysis_scripts/wav_to_ir_table.py in.wav out.bin --taps 128 --record rec.bin
python 04_analysis_scripts/wav_to_ir_table.py --selftest
```

- 128 taps = **512 bytes**; 208 taps = **832 bytes**.
- Input: PCM WAV, mono/stereo, 8/16/24/32-bit. Non-44.1 kHz is linear-
  resampled (`--resample auto`); `--resample never` reproduces the loader's
  strict 44.1-only behaviour.
- The loader's **`mono/left toggle`** selects 128 or 208; the script's `--taps`
  overrides it for the experiment.

## Mesa conversion (first real run)

`IR/MesaV3022.wav`: 44.1 kHz, **mono, 24-bit, 208 samples**.

```
python 04_analysis_scripts/wav_to_ir_table.py IR/MesaV3022.wav IR/MesaV3022_128.bin --taps 128 --record IR/MesaV3022_128_record.bin --slot 1
```

- 128 taps, scale `<<4`, gain 0 dB.
- first coefficient `0x14690` = **5225 << 4** = the first sample (5225).
- table 512 bytes; record 2048 bytes; record count 128; record coefficients
  at `0x10` **match the table exactly**.
- The loader's mono path would take **208** samples; the experiment's gate
  uses 128, so the script takes the first 128 (the loader's stereo/left path).

## Selftest

```
case 1  44.1k stereo 128 taps OK   first = 0x7fff000
case 2  48k mono 208 taps resampled OK
case 3  bad WAV rejected OK
```

## Environment fix

`04_analysis_scripts/platform.py` **shadowed Python's stdlib `platform`**
module (the script directory is first on `sys.path`), so importing numpy ran
its module-level dump and printed unrelated output. It is renamed to
`rp500_platform_survey.py`; no script imported it by name.
