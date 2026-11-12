#!/usr/bin/env python3
"""WAV -> RP500 user-cab IR table (44.1 kHz, 128 or 208 taps).

The GSP1101's `JUserCabUpdater vC59` is the provided WAV converter, but it is a
**GUI / MIDI uploader**, not a batch tool: it needs a device, builds a 2048-byte
device record, and sends it over MIDI.  It cannot be scripted to produce a
standalone coefficient table, and the C63 X-Edit does not convert WAVs at all.
This script is the offline batch version of the loader's coefficient path
(recovered from `JUserCabUpdater vC59.exe`):

  * PCM WAV, mono or stereo, 8/16/24/32-bit
  * output at **44.1 kHz** (linear-resampled if the input is not; the loader
    itself rejects non-44.1)
  * **128 taps** = the loader's stereo/left path: first 128 samples of the
    left/mono channel, scaled to 28-bit, packed 4-byte big-endian signed
  * **208 taps** = the loader's mono path: first 208 samples
  * scaling: 8-bit <<20, 16-bit <<12, 24-bit <<4, 32-bit >>4; optional gain dB
  * output: a 512-byte (128) or 832-byte (208) IR table for the S3b gate

The loader's UI has a **mono/left toggle** that selects 128 or 208; this
script's `--taps` overrides it for the experiment.  `--resample never`
reproduces the loader's strict 44.1-only behaviour.

Usage:
    python wav_to_ir_table.py in.wav out.bin [--taps 128] [--gain-db 0]
    python wav_to_ir_table.py in.wav out.bin --record rec.bin [--slot 1]
    python wav_to_ir_table.py --selftest
"""
import argparse
import math
import os
import struct
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from usercab_encode import build_record, COEF_OFF, REC_SIZE

N_TAPS = 128
MAX_TAPS = 208
SR_TARGET = 44100


def read_wav(path):
    """Return (left_samples, sample_rate, channels, bits_per_sample)."""
    d = open(path, "rb").read()
    if len(d) < 12 or d[:4] != b"RIFF" or d[8:12] != b"WAVE":
        raise ValueError("Invalid Impulse File, not 'WAVE'")
    fmt = None
    pcm = None
    pos = 12
    while pos + 8 <= len(d):
        cid = d[pos:pos + 4]
        size = struct.unpack_from("<I", d, pos + 4)[0]
        body = d[pos + 8:pos + 8 + size]
        if cid == b"fmt ":
            tag, ch, sr, _br, _ba, bps = struct.unpack_from("<HHIIHH", body, 0)
            if tag != 1:
                raise ValueError("not PCM (format tag %d)" % tag)
            if not 1 <= ch <= 2:
                raise ValueError("bad channel count %d" % ch)
            if bps not in (8, 16, 24, 32):
                raise ValueError("bad bits per sample %d" % bps)
            fmt = (ch, sr, bps)
        elif cid == b"data":
            pcm = body
            break
        pos += 8 + size + (size & 1)
    if fmt is None or pcm is None:
        raise ValueError("no fmt or data chunk")
    ch, sr, bps = fmt
    w = bps // 8
    n = len(pcm) // (ch * w)
    # left/mono channel only: the loader reads the frame and uses the first
    # (left) sample for its coefficient path
    out = np.empty(n, dtype=np.int64)
    for i in range(n):
        b = pcm[i * ch * w:(i * ch * w) + w]
        out[i] = int.from_bytes(b, "little", signed=True)
    return out, sr, ch, bps


def linear_resample(x, sr_in, sr_out):
    """Linear interpolation to sr_out (the loader does not resample)."""
    if sr_in == sr_out:
        return x
    n_out = int(round(len(x) * sr_out / sr_in))
    if n_out < 2:
        return np.array([x[0]], dtype=np.int64)
    pos = np.linspace(0, len(x) - 1, n_out)
    i0 = np.floor(pos).astype(np.int64)
    i1 = np.minimum(i0 + 1, len(x) - 1)
    frac = pos - i0
    y = np.round(x[i0] * (1 - frac) + x[i1] * frac).astype(np.int64)
    return y


def convert(path, taps=N_TAPS, gain_db=0.0, resample="auto"):
    x, sr, ch, bps = read_wav(path)
    resampled = False
    if sr != SR_TARGET:
        if resample == "never":
            raise ValueError("Invalid Impulse File, not 44100 Hz (use --resample auto)")
        x = linear_resample(x, sr, SR_TARGET)
        resampled = True
    if len(x) < taps:
        raise ValueError("not enough samples: %d < %d taps" % (len(x), taps))
    samples = x[:taps]
    scale = {8: 1 << 20, 16: 1 << 12, 24: 1 << 4, 32: None}[bps]
    gain = 10.0 ** (gain_db / 20.0)
    vals = []
    for s in samples:
        v = int(round((s >> 4) * gain)) if bps == 32 else int(round(int(s) * scale * gain))
        vals.append(max(-0x80000000, min(0x7FFFFFFF, v)))
    return samples, vals, (sr, ch, bps, resampled)


def pack_table(vals):
    return b"".join(struct.pack(">i", v) for v in vals)


def _make_wav(path, sr, ch, bps, n):
    frames = bytearray()
    for i in range(n):
        v = int(0.9 ** i * ((1 << (bps - 1)) - 1) * (1 if i % 2 == 0 else -1))
        frames += v.to_bytes(bps // 8, "little", signed=True)
        if ch == 2:
            frames += b"\x00" * (bps // 8)
    ba = ch * (bps // 8)
    fmt = struct.pack("<HHIIHH", 1, ch, sr, sr * ba, ba, bps)
    body = (b"WAVE" + b"fmt " + struct.pack("<I", len(fmt)) + fmt +
            b"data" + struct.pack("<I", len(frames)) + bytes(frames))
    open(path, "wb").write(b"RIFF" + struct.pack("<I", len(body)) + body)


def _selftest():
    import tempfile
    tmp = os.path.join(tempfile.gettempdir(), "wav_to_ir_selftest")
    # 44.1 kHz, 16-bit stereo, 128 taps; right channel ignored
    _make_wav(tmp + ".wav", 44100, 2, 16, 256)
    _, vals, info = convert(tmp + ".wav", 128)
    assert len(vals) == 128 and info[:3] == (44100, 2, 16)
    assert vals[0] == 0x7FFF << 12, hex(vals[0])
    print("case 1  44.1k stereo 128 taps OK   first = %s" % hex(vals[0] & 0xFFFFFFFF))
    # 48 kHz -> 44.1 kHz resampled, mono, 208 taps
    _make_wav(tmp + ".wav", 48000, 1, 16, 256)
    _, vals, info = convert(tmp + ".wav", 208)
    assert len(vals) == 208 and info[3] is True and info[1] == 1
    print("case 2  48k mono 208 taps resampled OK   first = %s" % hex(vals[0] & 0xFFFFFFFF))
    # bad WAV
    open(tmp + ".wav", "wb").write(b"not a wav")
    try:
        convert(tmp + ".wav", 128)
    except ValueError as e:
        print("case 3  bad WAV rejected OK   (%s)" % e)
    else:
        raise AssertionError("bad WAV accepted")
    print("selftest OK")


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("wav", nargs="?")
    ap.add_argument("out", nargs="?")
    ap.add_argument("--taps", type=int, default=N_TAPS)
    ap.add_argument("--gain-db", type=float, default=0.0)
    ap.add_argument("--resample", choices=("auto", "never"), default="auto")
    ap.add_argument("--record", help="also write the full 2048-byte loader record")
    ap.add_argument("--slot", type=int, default=1)
    ap.add_argument("--flag", type=int, default=0)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return _selftest()
    if not a.wav or not a.out:
        print(__doc__)
        return 2
    if a.taps not in (N_TAPS, MAX_TAPS):
        raise SystemExit("taps must be 128 or 208")
    samples, vals, info = convert(a.wav, a.taps, a.gain_db, a.resample)
    table = pack_table(vals)
    open(a.out, "wb").write(table)
    sr, ch, bps, resampled = info
    print("input : %s  %d Hz  %d ch  %d-bit%s"
          % (os.path.basename(a.wav), sr, ch, bps, "  (resampled to 44.1k)" if resampled else ""))
    print("taps  : %d   scale: %s   gain: %g dB"
          % (a.taps, {8: "<<20", 16: "<<12", 24: "<<4", 32: ">>4"}[bps], a.gain_db))
    print("first : %s   last: %s   min: %s   max: %s"
          % (hex(vals[0] & 0xFFFFFFFF), hex(vals[-1] & 0xFFFFFFFF),
             hex(min(vals) & 0xFFFFFFFF), hex(max(vals) & 0xFFFFFFFF)))
    print("table : %s  (%d bytes)" % (a.out, len(table)))
    if a.record:
        # build_record applies the scaling itself, so it gets the RAW samples
        rec = build_record([int(s) for s in samples], bps, slot=a.slot,
                           gain_db=a.gain_db, flag=a.flag, name=os.path.basename(a.wav))
        open(a.record, "wb").write(rec)
        print("record: %s  (%d bytes, coefficients at 0x%03X)"
              % (a.record, len(rec), COEF_OFF))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
