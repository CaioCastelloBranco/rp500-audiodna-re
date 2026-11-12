import re, sys

KEYWORDS = ["ir", "cabinet", "cab", "convol", "impulse", "wav", "respon",
            "speaker", "mic", "mic ", "eq", "filter", "juce", "digitech",
            "dsp", "firmware", "version", "copyright", "arm", "flash",
            "sample", "rate", "gain", "drive", "preset", "factory",
            "linux", "u-boot", "kernel", "rootfs", "squash", "jffs",
            "0.0.0", "build", "v1", "version"]

def strings(data, minlen=4):
    out = []
    cur = bytearray(); start = 0
    for i, c in enumerate(data):
        if 32 <= c <= 126:
            if not cur: start = i
            cur.append(c)
        else:
            if len(cur) >= minlen:
                out.append((start, cur.decode('ascii')))
            cur = bytearray()
    return out

for path in sys.argv[1:]:
    print("="*80)
    print(path)
    data = open(path,'rb').read()
    print("size:", len(data), hex(len(data)))
    print("first32:", data[:32].hex(' '))
    allstr = strings(data)
    print("total ascii strings:", len(allstr))
    # keyword hits
    for (off, s) in allstr:
        low = s.lower()
        for kw in KEYWORDS:
            if kw.lower() in low:
                print(f"0x{off:06X} [{kw}] {s[:120]}")
                break
    # RIFF/WAV check
    print("RIFF count:", data.count(b'RIFF'))
    print("WAVE count:", data.count(b'WAVE'))
    idxs = [m.start() for m in re.finditer(b'RIFF', data)]
    print("RIFF offsets:", [hex(i) for i in idxs[:10]])
