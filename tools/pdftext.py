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
    """Derived/output artifacts go to the script directory."""
    return _os.path.join(_SW, name)
_GLOB_PDFS = _os.path.join(_ROOT, "03_docs", "*.pdf")


from pypdf import PdfReader
import os, glob

for p in glob.glob(_GLOB_PDFS):
    print('=' * 80)
    print(os.path.basename(p))
    try:
        r = PdfReader(p)
        print('pages', len(r.pages))
        txt = []
        for i, pg in enumerate(r.pages):
            t = pg.extract_text() or ''
            txt.append(f'--- page {i+1} ---\n{t}')
        out = '\n'.join(txt)
        base = os.path.splitext(os.path.basename(p))[0]
        op = os.path.join(_FW, base + '.txt')
        open(op, 'w', encoding='utf-8').write(out)
        print('text chars', len(out), '->', op)
        print(out[:1500])
    except Exception as e:
        print('ERR', e)
