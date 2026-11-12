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
import re
S = _FW
v20raw = open(S+r'\v20_res_51E18.bin','rb').read()
v20 = [v20raw[k*0x10000:(k+1)*0x10000] for k in range(16)]
def bodies(img):
    return [img[k*0x10000 + k*8 : (k+1)*0x10000 + k*8] for k in range(16)]
c63 = bodies(open(S+r'\c63_fw.bin','rb').read())

print('=== V20 "USER" occurrences ===')
for m in re.finditer(rb'USER[ -~]{0,20}', v20raw):
    print('  0x%06X %r' % (m.start(), m.group()[:40]))
print()
print('=== §9.4 per-bank D070 / E000 counts ===')
for nm, banks in (('v20', v20), ('c63', c63)):
    d70 = [b.count(b'\x90\xd0\x70') for b in banks]
    e00 = [b.count(b'\x90\xe0\x00') for b in banks]
    print(' ', nm, 'D070 per bank', d70, 'total', sum(d70))
    print(' ', nm, 'E000 per bank', e00, 'total', sum(e00))
print()
print('=== §2.2 cab block anchors ===')
print('  C63 DREAD ACOUSTIC bank11 0x%04X' % c63[11].find(b'DREAD ACOUSTIC'))
print('  C63 CHAMP1X8       bank11 0x%04X' % c63[11].find(b'CHAMP1X8'))
print('  C63 DIRECT         bank11 0x%04X' % c63[11].find(b'DIRECT  '))
print('  C63 USER 1         bank11 0x%04X' % c63[11].find(b'USER 1'))
print('  C63 USER 10 end    bank11 0x%04X' % (c63[11].find(b'USER 10')+8))
print('  V20 DREAD ACOUSTIC bank10 0x%04X' % v20[10].find(b'DREAD ACOUSTIC'))
print('  V20 CHAMP 1X8      bank10 0x%04X' % v20[10].find(b'CHAMP 1X8'))
print('  V20 USER_CAB       bank15 0x%04X' % v20[15].find(b'USER_CAB %D'))
print('  C63 USER_CAB       bank15 0x%04X' % c63[15].find(b'USER_CAB %D'))
print()
print('=== §12.5 RP500 DSP loader anchors (already verified) ===')
print('  bank15 0xBE97 loop, bank15 0xDBB3 helper, bank14 0x9A12 twin')
