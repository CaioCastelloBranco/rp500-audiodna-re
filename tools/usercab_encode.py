"""Reimplementation of the GSP1101 user-cab encoder (Jcabinet, vC59 format).

Recovered from FUN_00406ed0 in `JUserCabUpdater vC59.exe`.

Takes a 44.1 kHz, 16- or 24-bit PCM WAV and produces the 2048-byte
record the device stores in a user-cab slot:

    0x000  4   b'\\x00\\x5c\\x00\\x05'
    0x004  8   b'\\x00\\x05' + bytes([cab_idx*8]) + b'\\x00\\x00\\x00\\x08\\x00'
    0x00C  4   sample-count, BE32 (default 0x80 = 128)
    0x010  512 128 x signed 32-bit BE coefficients
    0x210  ..  0xFF fill
    0x7E7  23  filename record, NUL padded
    0x7FE  2   [cab_idx, flag]

Scaling: 16-bit sample << 12, 24-bit sample << 4  -> 28-bit full scale,
then * linear gain (10 ** (dB / 20)), rounded, clamped to int32.

Usage:
    python usercab_encode.py in.wav out.bin [--slot 1] [--gain-db 0] [--flag 0] [--taps 128]
    python usercab_encode.py --selftest
"""
import math
import struct
import sys

REC_SIZE = 0x800
N_TAPS = 128
MAX_TAPS = 208
COEF_OFF = 0x10
NAME_OFF = 0x7E7
NAME_LEN = 23
TAIL_OFF = 0x7FE
MAGIC = b"\x00\x5c\x00\x05"


def _read_frames(raw, ch, bps, n):
    """Return the first n left-channel samples as signed ints."""
    step = ch * (bps // 8)
    w = bps // 8
    out = []
    for i in range(n):
        off = i * step
        if off + w > len(raw):
            raise ValueError("not enough samples")
        b = raw[off:off + w]
        if bps == 16:
            v = int.from_bytes(b, "little", signed=True)
        elif bps == 24:
            v = int.from_bytes(b, "little", signed=True)
        else:  # 32-bit
            v = int.from_bytes(b, "little", signed=True)
        out.append(v)
    return out


def parse_wav(path, n_taps=N_TAPS):
    data = open(path, "rb").read()
    if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise ValueError("Invalid Impulse File, not 'WAVE'")

    fmt = None
    pcm = None
    pos = 12
    while pos + 8 <= len(data):
        cid = data[pos:pos + 4]
        size = struct.unpack_from("<I", data, pos + 4)[0]
        body = data[pos + 8:pos + 8 + size]
        if cid == b"fmt ":
            if size != 0x10:
                raise ValueError("fmt chunk size is not 0x10 (unsupported WAV)")
            tag, ch, sr, _br, ba, bps = struct.unpack_from("<HHIIHH", body, 0)
            if tag != 1:
                raise ValueError("not PCM (format tag %d)" % tag)
            if not 1 <= ch <= 2:
                raise ValueError("bad channel count %d" % ch)
            if sr != 44100:
                raise ValueError("Invalid Impulse File, not 44100 Hz")
            if bps not in (16, 24, 32):
                raise ValueError("Invalid Impulse File, bad bytes per sample")
            fmt = (ch, bps, ba)
        elif cid == b"data":
            if fmt is None:
                raise ValueError("data chunk before fmt chunk")
            ch, bps, _ba = fmt
            pcm = _read_frames(body, ch, bps, n_taps)
            break
        pos += 8 + size + (size & 1)

    if fmt is None:
        raise ValueError("no fmt chunk")
    if pcm is None:
        raise ValueError("no data chunk")
    return pcm, fmt[1]


def build_record(samples, bps, slot=1, gain_db=0.0, flag=0, count=None,
                 name="", sample_count_override=None):
    if not 1 <= slot <= 10:
        raise ValueError("slot must be 1..10")
    n = len(samples)
    if n not in (N_TAPS, MAX_TAPS):
        raise ValueError("tap count must be 128 or 208, got %d" % n)

    scale = {16: 1 << 12, 24: 1 << 4, 32: 1}[bps]
    gain = 10.0 ** (gain_db / 20.0)

    rec = bytearray(b"\xff" * REC_SIZE)
    rec[0x000:0x004] = MAGIC
    rec[0x004:0x00C] = bytes([0x00, 0x05, (slot * 8) & 0xFF,
                              0x00, 0x00, 0x00, 0x08, 0x00])

    cnt = n if sample_count_override is None else sample_count_override
    rec[0x00C:0x010] = struct.pack(">I", cnt)

    for i, s in enumerate(samples):
        if bps == 32:
            # original: (int)uStack_198 >> 4, arithmetic shift
            v = int(round((s >> 4) * gain))
        else:
            v = int(round(s * scale * gain))
        v = max(-0x80000000, min(0x7FFFFFFF, v))
        rec[COEF_OFF + 4 * i:COEF_OFF + 4 * i + 4] = struct.pack(">i", v)

    nm = name.encode("ascii", "replace")[:NAME_LEN]
    rec[NAME_OFF:NAME_OFF + NAME_LEN] = nm + b"\x00" * (NAME_LEN - len(nm))
    rec[TAIL_OFF:TAIL_OFF + 2] = bytes([slot & 0xFF, flag & 0xFF])
    return bytes(rec)


def encode_file(wav_path, out_path, slot=1, gain_db=0.0, flag=0, n_taps=N_TAPS):
    samples, bps = parse_wav(wav_path, n_taps=n_taps)
    rec = build_record(samples, bps, slot=slot, gain_db=gain_db, flag=flag,
                       name=wav_path.replace("\\", "/").split("/")[-1])
    open(out_path, "wb").write(rec)
    return rec


def _make_test_wav(path, bps=16, ch=1, n=512):
    """Synthetic decaying impulse, for the self-test."""
    frames = bytearray()
    for i in range(n):
        v = int(0.9 ** i * ((1 << (bps - 1)) - 1) * (1 if i % 2 == 0 else -1))
        frames += v.to_bytes(bps // 8, "little", signed=True)
        if ch == 2:
            frames += b"\x00" * (bps // 8)
    ba = ch * (bps // 8)
    fmt = struct.pack("<HHIIHH", 1, ch, 44100, 44100 * ba, ba, bps)
    body = (b"WAVE" + b"fmt " + struct.pack("<I", len(fmt)) + fmt +
            b"data" + struct.pack("<I", len(frames)) + bytes(frames))
    open(path, "wb").write(b"RIFF" + struct.pack("<I", len(body)) + body)


def _selftest():
    import os
    import tempfile
    tmp = os.path.join(tempfile.gettempdir(), "usercab_selftest.wav")

    # 1. 16-bit mono, 128 taps (the documented default)
    _make_test_wav(tmp, bps=16, ch=1)
    rec = encode_file(tmp, tmp + ".bin", slot=3, gain_db=0.0)
    assert len(rec) == REC_SIZE, len(rec)
    assert rec[:4] == MAGIC
    assert rec[0x004:0x00C] == bytes([0, 5, 24, 0, 0, 0, 8, 0]), rec[0x004:0x00C].hex()
    assert struct.unpack(">I", rec[0x00C:0x010])[0] == 0x80
    first = struct.unpack(">i", rec[0x10:0x14])[0]
    assert first == 0x7FFF << 12, hex(first)
    assert rec[0x210:0x7E7] == b"\xff" * (0x7E7 - 0x210)
    assert rec[0x7FE] == 3 and rec[0x7FF] == 0
    print("case 1  16-bit mono   128 taps OK   first coef = %s" % hex(first & 0xFFFFFFFF))

    # 2. 24-bit stereo, 128 taps (right channel must be ignored)
    _make_test_wav(tmp, bps=24, ch=2, n=512)
    rec = encode_file(tmp, tmp + ".bin", slot=7, gain_db=-6.0)
    assert struct.unpack(">I", rec[0x00C:0x010])[0] == 0x80
    assert rec[0x004:0x00C] == bytes([0, 5, 56, 0, 0, 0, 8, 0])
    first = struct.unpack(">i", rec[0x10:0x14])[0]
    exp = int(round((0x7FFFFF << 4) * (10 ** (-6.0 / 20.0))))
    assert first == exp, (hex(first), hex(exp))
    print("case 2  24-bit stereo 128 taps OK   first coef = %s (expected %s)" % (hex(first & 0xFFFFFFFF), hex(exp)))

    # 3. 16-bit mono, 208 taps (option-bit variant)
    _make_test_wav(tmp, bps=16, ch=1, n=512)
    rec = encode_file(tmp, tmp + ".bin", slot=1, n_taps=208)
    assert struct.unpack(">I", rec[0x00C:0x010])[0] == 0xD0
    assert rec[0x350:0x7E7] == b"\xff" * (0x7E7 - 0x350)
    assert rec[0x7FE] == 1 and rec[0x7FF] == 0
    print("case 3  16-bit mono   208 taps OK   last coef end 0x%03X" % (0x10 + 208 * 4))

    # 4. bad WAV must raise
    open(tmp, "wb").write(b"not a wav at all")
    try:
        encode_file(tmp, tmp + ".bin")
    except ValueError as e:
        print("case 4  bad WAV rejected OK   (%s)" % e)
    else:
        raise AssertionError("bad WAV was accepted")

    print("selftest OK: 3 record cases + rejection case")


def main(argv):
    if len(argv) >= 2 and argv[1] == "--selftest":
        _selftest()
        return 0
    if len(argv) < 3:
        print(__doc__)
        return 2
    wav, out = argv[1], argv[2]
    slot, gain_db, flag, n_taps = 1, 0.0, 0, N_TAPS
    i = 3
    while i < len(argv):
        if argv[i] == "--slot":
            slot = int(argv[i + 1]); i += 2
        elif argv[i] == "--gain-db":
            gain_db = float(argv[i + 1]); i += 2
        elif argv[i] == "--flag":
            flag = int(argv[i + 1], 0); i += 2
        elif argv[i] == "--taps":
            n_taps = int(argv[i + 1], 0); i += 2
        else:
            raise SystemExit("unknown option " + argv[i])
    rec = encode_file(wav, out, slot=slot, gain_db=gain_db, flag=flag, n_taps=n_taps)
    print("wrote %s (%d bytes)" % (out, len(rec)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
