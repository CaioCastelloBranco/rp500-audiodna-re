# --- portable path resolution (added 2026-11-10) ---------------------------
import os as _os

_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_SW = _os.path.dirname(_os.path.abspath(__file__))


def _P(name):
    """Resolve an analysis artifact inside this archive (no absolute paths)."""
    _ALIAS = {"gsp_fw.bin": "gsp1101_fw.bin", "rp_fw.bin": "rp500_fw.bin"}
    name = _ALIAS.get(name, name)
    if name.endswith(".exe"):
        _dir = _os.path.join(_ROOT, "02_source_binaries")
    elif name.endswith(".pdf"):
        _dir = _os.path.join(_ROOT, "03_docs")
    else:
        _dir = _os.path.join(_ROOT, "01_source_firmware")
    p = _os.path.join(_dir, name)
    if _os.path.exists(p):
        return p
    q = _os.path.join(_SW, name)
    if _os.path.exists(q) or "%" in name or name.endswith(".txt"):
        return q
    return p
# ---------------------------------------------------------------------------

_FW = _os.path.join(_ROOT, "01_source_firmware")


def _OUT(name):
    """Route derived/output artifacts to the script directory."""
    return _os.path.join(_SW, name)


"""Re-derive C48/C63 addresses with the CORRECT body model.

exe image layout (verified): [body0 64K][desc1][body1 64K][desc2]...[desc15][body15 64K][trailer 8]
  desc_k at k*0x10000 + (k-1)*8
  body_k at k*0x10000 + k*8   (body0 at 0)
"""
import re, sys
sys.path.insert(0, _FW)
from d51 import disasm

S = _FW
def bodies(img):
    out = []
    for k in range(16):
        s = k*0x10000 + k*8
        out.append(img[s:s+0x10000])
    return out

c63 = bodies(open(S+r'\c63_fw.bin','rb').read())
c48 = bodies(open(S+r'\c48_fw.bin','rb').read())
v20 = [open(S+r'\v20_res_51E18.bin','rb').read()[k*0x10000:(k+1)*0x10000] for k in range(16)]
rp  = [open(S+r'\rp500_fw.bin','rb').read()[k*0x10000:(k+1)*0x10000] for k in range(16)]

def find(banks, s):
    res = []
    for k, b in enumerate(banks):
        for m in re.finditer(re.escape(s), b):
            res.append((k, m.start()))
    return res

print('=== key strings, correct offsets ===')
for nm, banks, keys in (
    ('c63', c63, [b'USER 1', b'USER %d', b'CAB_EN_XLR_LPF', b'USER_CAB %D', b'CHAMP1X8', b'USER 10']),
    ('c48', c48, [b'USER_CAB %D', b'CHAMP1X8', b'USER 1']),
):
    for s in keys:
        r = find(banks, s)
        print(' %-4s %-16s %s' % (nm, s.decode(), [( 'bank%d 0x%04X' % (k,o)) for k,o in r[:6]]))

print()
print('=== cab table pointers ===')
# C63 CHAMP1X8 pointer 0xD8EE? find BE pointer to CHAMP1X8 body offset
for nm, banks in (('c63', c63), ('c48', c48), ('rp', rp)):
    ch = find(banks, b'CHAMP1X8')[0]
    ptr = bytes([ch[1] >> 8, ch[1] & 0xFF])
    hits = []
    for k, b in enumerate(banks):
        for m in re.finditer(re.escape(ptr), b):
            hits.append((k, m.start()))
    print(' %-4s CHAMP1X8 @bank%d 0x%04X  ptr %s refs %s' % (nm, ch[0], ch[1], ptr.hex(), [('b%d 0x%04X'%(k,o)) for k,o in hits[:6]]))

print()
print('=== DSP register reference counts (correct bodies) ===')
def refs(banks, addr):
    pat = bytes([0x90, addr >> 8, addr & 0xFF])
    return [b.count(pat) for b in banks]
for addr in (0xE000, 0xEE00, 0xE200, 0xE400, 0xE800, 0xD070, 0xD06E, 0xFDFC, 0xE600):
    print('  %04X  v20=%s  c48=%s  c63=%s  rp=%s' % (addr,
        sum(refs(v20,addr)), sum(refs(c48,addr)), sum(refs(c63,addr)), sum(refs(rp,addr))))

print()
print('=== D066 write values (disassembled) ===')
for nm, banks in (('v20',v20),('c48',c48),('c63',c63),('rp',rp)):
    vals = []
    for k, b in enumerate(banks):
        for m in re.finditer(rb'\x90\xd0\x66', b):
            a = m.start()
            ins = list(disasm(b, 0, a, a+16))
            if len(ins) >= 2 and ins[1][2].startswith('MOV A,#'):
                vals.append((k, ins[1][2]))
    print(' ', nm, vals)

print()
print('=== E200/E400/E800 command values (disassembled) ===')
def cmd(banks, reg):
    out = []
    for k, b in enumerate(banks):
        for m in re.finditer(re.escape(bytes([0x90, reg>>8, reg&0xFF])), b):
            a = m.start()
            ins = list(disasm(b, 0, a, a+20))
            for j in range(1, min(4, len(ins))):
                if ins[j][2].startswith('MOV A,#'):
                    out.append((k, ins[j][2])); break
    return out
for reg in (0xE200, 0xE400, 0xE800):
    for nm, banks in (('v20',v20),('c48',c48),('c63',c63),('rp',rp)):
        print('  %04X %-4s %s' % (reg, nm, cmd(banks, reg)))

print()
print('=== free flash (contiguous 0xFF runs) ===')
def runs(banks, minlen):
    tot = 0; best = 0; n = 0
    for b in banks:
        for m in re.finditer(rb'\xff+', b):
            L = m.end()-m.start()
            if L >= minlen:
                tot += L; best = max(best, L); n += 1
    return tot, best, n
for nm, banks in (('v20',v20),('c48',c48),('c63',c63),('rp',rp)):
    for ml in (768, 4096):
        t, b, n = runs(banks, ml)
        print('  %-4s min=%-4d total=0x%X largest=0x%X runs=%d' % (nm, ml, t, b, n))
