# --- portable path resolution (added 2026-11-10) ---------------------------
import os as _os

_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_SW = _os.path.dirname(_os.path.abspath(__file__))

_FW = _os.path.join(_ROOT, "01_source_firmware")


def _OUT(name):
    """Route derived/output artifacts to the script directory."""
    return _os.path.join(_SW, name)



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
"""Fast verification of the report's key factual claims."""
import struct

SHARED = _FW
ok = True
def chk(name, cond, extra=''):
    global ok
    if not cond: ok = False
    print(('PASS ' if cond else 'FAIL ') + name + (('  ' + str(extra)) if extra else ''))

def payload16(img):
    return b''.join(img[k*0x10008+8:k*0x10008+0x10008] for k in range(16))

v20 = open(SHARED + r'\v20_res_51E18.bin','rb').read()
rp  = open(SHARED + r'\rp500_fw.bin','rb').read()
c48raw = open(SHARED + r'\c48_fw.bin','rb').read()
c63raw = open(SHARED + r'\c63_fw.bin','rb').read()
c63 = open(SHARED + r'\gsp1101_fw.bin','rb').read()

# --- 1. sizes / headers ---
chk('v20 size 1MB', len(v20) == 0x100000, hex(len(v20)))
chk('rp size 1MB', len(rp) == 0x100000, hex(len(rp)))
chk('c48 16x10008', len(c48raw) == 16*0x10008, hex(len(c48raw)))
chk('c63 16x10008', len(c63raw) == 16*0x10008, hex(len(c63raw)))
chk('v20 hdr', v20[:8].hex() == 'ea8068022ec55391', v20[:8].hex())
chk('rp  hdr', rp[:8].hex() == 'ea8068022ec55391', rp[:8].hex())
chk('c48 hdr', c48raw[:8].hex() == 'ea80680230835391', c48raw[:8].hex())
chk('c63 hdr', c63raw[:8].hex() == 'ea806802307a5391', c63raw[:8].hex())

# --- 2. rp500 == official V20 image? ---
chk('rp500 == v20 image byte-identical', v20 == rp,
    '%d/%d bytes equal' % (sum(a==b for a,b in zip(v20,rp)), len(v20)))

# --- 3. C63 image lives in gsp1101_fw.bin at 0x19F8 ---
chk('c63 embedded at 0x19F8', c63[0x19F8:0x19F8+0x10008*16] == c63raw)

# --- 4. C48 in the C48 updater exe ---
exe48 = open(SHARED + r'\JUpdater GSP1101vC48.exe','rb').read()
chk('c48 embedded at 0xBF5F0', exe48[0xBF5F0:0xBF5F0+0x10008*16] == c48raw)
exe63 = open(SHARED + r'\JUpdater Gsp1101vC63.exe','rb').read()
chk('c63 in vC63 updater @0xC0FF8', exe63[0xC0FF8:0xC0FF8+0x10008*16] == c63raw)

# --- 5. cab names / USER entries ---
D48, D63 = payload16(c48raw), payload16(c63raw)
DRP = rp
chk('C48 bank10 0x7618 = CHAMP1X8', D48[10*0x10000+0x7618:10*0x10000+0x7620] == b'CHAMP1X8')
chk('C48 has no USER', b'USER 1' not in D48 and b'USER %d' not in D48)
chk('C63 USER 1 @ bank11 0xD9D8', D63[11*0x10000+0xD9D8:11*0x10000+0xD9D8+6] == b'USER 1')
chk('C63 USER %d @ bank0 0xBFF4', D63[0xBFF4:0xBFF4+8] == b'USER %d')
chk('C63 CAB_EN_XLR_LPF @ bank8 0xE7F0',
    D63[8*0x10000+0xE7F0:8*0x10000+0xE7F0+13] == b'CAB_EN_XLR_LPF')
chk('RP bank4 0x3486 = CHAMP1X8', DRP[4*0x10000+0x3486:4*0x10000+0x3486+8] == b'CHAMP1X8')
chk('RP has no USER', b'USER 1' not in DRP and b'USER_CAB' not in DRP)
chk('RP 0x478E pointer table', DRP[4*0x10000+0x478E:4*0x10000+0x4790] == b'\x34\x53')

# --- 6. no IR magic in any firmware ---
for nm, d in (('v20',v20),('rp',rp),('c48',c48raw),('c63',c63raw)):
    chk('no 00 5C 00 05 in ' + nm, b'\x00\x5c\x00\x05' not in d)

# --- 7. DSP register refs ---
def dptr_refs(d, addr):
    pat = bytes([0x90, addr >> 8, addr & 0xFF])
    return d.count(pat)
for nm, d in (('v20',v20),('rp',rp),('c48',c48raw),('c63',c63raw)):
    refs = {r: dptr_refs(d, r) for r in (0xE000,0xEE00,0xE200,0xE400,0xE800,0xD070,0xD06E,0xFDFC)}
    print('  ', nm, refs)

# --- 8. DSP command value sets (MOV DPTR,#reg; MOV A,#imm) ---
import re
def cmdvals(d, reg):
    pat = bytes([0x90, reg >> 8, reg & 0xFF])
    vals = set()
    for m in re.finditer(re.escape(pat), d):
        w = d[m.start()+3:m.start()+14]
        for i in range(len(w)-1):
            if w[i] == 0x74:
                vals.add(w[i+1]); break
    return vals
for reg in (0xE200, 0xE400, 0xE800, 0xD066):
    sets = {}
    for nm, d in (('v20',v20),('c48',c48raw),('c63',c63raw),('rp',rp)):
        sets[nm] = sorted(cmdvals(d, reg))
    same = sets['v20'] == sets['c48'] == sets['c63']
    print('  ', hex(reg), sets, 'GSP-triple-identical' if same else 'DIFFERS')

# --- 9. free flash ---
def free(d):
    n = 0; best = 0; run = 0
    for b in d:
        if b == 0xFF:
            run += 1
        else:
            n += run; best = max(best, run); run = 0
    n += run; best = max(best, run)
    return n, best
for nm, d in (('v20',v20),('c48',c48raw),('c63',c63raw),('rp',rp)):
    n, best = free(d)
    print('  ', nm, 'free=0x%X largest=0x%X' % (n, best))

print()
print('ALL CHECKS PASS' if ok else 'SOME CHECKS FAILED')
