#!/usr/bin/env python3
"""Add a 2.1 RP500 revision to the NetUpdaterClone firmware updater bundle.

The supplied updater is a .NET single-file bundle:
  * host PE            0x000000
  * app assembly       0x052000  (PE, uncompressed, 3 sections)
  * UpdateTargets.xml  inside the app assembly's .text, ASCII
  * rp500V20.DigBin    inside the app assembly's .text, 0x100084 bytes

The revision table lives in that XML.  Bumping 2.0 -> 2.1 is a same-length
edit, so the manifest resource keeps its size and no metadata has to change.
The firmware image is swapped byte-for-byte with a build of identical length,
so its manifest resource is also untouched structurally.

Why 2.1 and not a rename to an older slot:
  MainForm.BuildRevisionList() filters with VersionComparer.IsNewer(revision,
  device.CurrentVersion).  The RP500 reports 2.0, so only a strictly greater
  version is offered by the default "Newest" filter.

Usage:
    python patch_updater.py [--exe ORIGINAL.exe] [--image BUILD.DigBin]
                            [--outdir 09_builds/updater_2.1]
                            [--version 2.1] [--date "Nov 10, 2026"] [--dry-run]
"""
import argparse
import hashlib
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from digbin_pack import unpack  # noqa: E402

# Stock rp500V20.DigBin, used to locate the embedded resource without relying
# on a hard-coded file offset.
STOCK_IMAGE_SHA256 = "01d94790963a8c282fb25b322da5247b0b4b8d9b6063132b52bcf3894820a070"

RP500_REVISION_PREFIX = (
    b'<Revision Version="'
)
RP500_MARKER = b'<Product Name="RP500" ProductID="0x5">'
RP500_URL = b'ImageUrl="http://www.lexiconpro.com/updater/digitech/firmware/rp500/rp500V20.DigBin"'


def find_rp500_revision(xml: bytes) -> int:
    """Return the offset of the RP500 revision element's Version attribute value."""
    prod = xml.find(RP500_MARKER)
    if prod < 0:
        raise SystemExit("RP500 product block not found in UpdateTargets.xml")
    end = xml.find(b"</Product>", prod)
    if end < 0:
        raise SystemExit("RP500 product block is not terminated")
    block = xml[prod:end]

    revs = []
    i = block.find(b"<Revision ")
    while i >= 0:
        revs.append(prod + i)
        i = block.find(b"<Revision ", i + 1)
    if not revs:
        raise SystemExit("RP500 product block has no revisions")

    matches = []
    for r in revs:
        end_of_rev = xml.find(b"/>", r)
        if end_of_rev < 0:
            continue
        if xml.find(RP500_URL, r, end_of_rev) >= 0:
            matches.append(r)
    if len(matches) != 1:
        raise SystemExit(f"expected exactly 1 revision with the rp500V20 ImageUrl, "
                         f"found {len(matches)}")
    return matches[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", default=r"02_source_binaries/Digitech.RP.Series.Firmware.Updater.exe")
    ap.add_argument("--image", default="09_builds/rp500_v20_caio4x12.DigBin")
    ap.add_argument("--outdir", default="09_builds/updater_2.1")
    ap.add_argument("--version", default="2.1")
    ap.add_argument("--date", default="Nov 10, 2026")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    exe = bytearray(open(args.exe, "rb").read())
    image = open(args.image, "rb").read()

    # --- sanity on the payload -------------------------------------------
    if len(image) != 0x100084:
        raise SystemExit(f"image is {len(image):#x} bytes, expected 0x100084")
    unpack(image)  # raises if the container is malformed
    if args.version.encode() == b"2.0":
        raise SystemExit("refusing to keep version 2.0; the Newest filter would hide it")

    # --- locate the embedded stock image ---------------------------------
    stock = open("01_source_firmware/rp500V20.DigBin", "rb").read()
    if hashlib.sha256(stock).hexdigest() != STOCK_IMAGE_SHA256:
        raise SystemExit("01_source_firmware/rp500V20.DigBin is not the expected stock image")
    hits = []
    start = 0
    while True:
        i = exe.find(stock[:64], start)
        if i < 0:
            break
        hits.append(i)
        start = i + 1
    if len(hits) != 1:
        raise SystemExit(f"expected exactly 1 embedded stock image, found {len(hits)}: "
                         f"{[hex(h) for h in hits]}")
    img_off = hits[0]
    if bytes(exe[img_off:img_off + len(stock)]) != stock:
        raise SystemExit("embedded image head matched but the full body did not")
    if len(image) != len(stock):
        raise SystemExit("replacement image must be the same length as the stock image")

    # --- locate the RP500 revision entry ---------------------------------
    xml_start = exe.find(b'<Config xmlns=')
    if xml_start < 0:
        raise SystemExit("UpdateTargets.xml not found in the bundle")
    rev = find_rp500_revision(bytes(exe))
    ver_at = exe.find(b'Version="', rev) + len(b'Version="')
    old_ver = bytes(exe[ver_at:ver_at + 3])
    if old_ver != b"2.0":
        raise SystemExit(f"RP500 revision is {old_ver!r}, expected b'2.0'")
    new_ver = args.version.encode()
    if len(new_ver) != 3:
        raise SystemExit("version must be 3 characters (e.g. 2.1) to keep the XML size fixed")

    date_at = exe.find(b'ReleaseDate="', rev) + len(b'ReleaseDate="')
    old_date = bytes(exe[date_at:date_at + 12])
    new_date = args.date.encode()
    if len(new_date) != 12:
        raise SystemExit("date must be 12 characters to keep the XML size fixed")

    # --- locate the two "rp500V20.DigBin" strings -------------------------
    # 1. the ImageUrl in UpdateTargets.xml
    # 2. the manifest resource name in the #Strings heap
    # Renaming both keeps the URL and the resource in agreement, and the new
    # name is the same length so no heap or metadata offset moves.
    xml_end = exe.find(b"</Config>", xml_start) + len(b"</Config>")
    if xml_end <= len(b"</Config>"):
        raise SystemExit("UpdateTargets.xml is not terminated")
    old_name = b"rp500V20.DigBin"
    new_name = b"rp500V21.DigBin"
    if len(old_name) != len(new_name):
        raise SystemExit("resource rename must preserve length")
    name_hits = []
    start = 0
    while True:
        i = exe.find(old_name, start)
        if i < 0:
            break
        name_hits.append(i)
        start = i + 1
    if len(name_hits) != 2:
        raise SystemExit(f"expected 2 rp500V20.DigBin strings (URL + resource), "
                         f"found {len(name_hits)}: {[hex(h) for h in name_hits]}")
    if not any(xml_start <= h < xml_end for h in name_hits):
        raise SystemExit("none of the rp500V20.DigBin strings is inside the XML")
    if not any(h >= xml_end for h in name_hits):
        raise SystemExit("no rp500V20.DigBin resource name outside the XML")

    print(f"exe                {args.exe}  ({len(exe):#x} bytes)")
    print(f"  xml start        0x{xml_start:X}")
    print(f"  RP500 revision   0x{rev:X}")
    print(f"  version          0x{ver_at:X}  {old_ver!r} -> {new_ver!r}")
    print(f"  release date     0x{date_at:X}  {old_date!r} -> {new_date!r}")
    print(f"  embedded image   0x{img_off:X}  {len(stock):#x} bytes")
    print(f"  replacement      {args.image}")
    print(f"  image sha256     {hashlib.sha256(image).hexdigest()}")
    print(f"  rename           {old_name.decode()} -> {new_name.decode()} "
          f"at {[hex(h) for h in name_hits]}")

    # --- patch ------------------------------------------------------------
    exe[img_off:img_off + len(image)] = image
    exe[ver_at:ver_at + 3] = new_ver
    exe[date_at:date_at + 12] = new_date
    for h in name_hits:
        exe[h:h + len(old_name)] = new_name

    # --- verify -----------------------------------------------------------
    out = bytes(exe)
    if out[img_off:img_off + len(image)] != image:
        raise SystemExit("FAIL: image was not written")
    if out[ver_at:ver_at + 3] != new_ver:
        raise SystemExit("FAIL: version was not written")
    if out.count(b'<Config xmlns=') != 1:
        raise SystemExit("FAIL: XML structure changed")
    if out.count(old_name) != 0 or out.count(new_name) != 2:
        raise SystemExit("FAIL: resource rename did not apply to both strings")
    if len(out) != len(open(args.exe, "rb").read()):
        raise SystemExit("FAIL: output length changed")
    changed = sum(1 for a, b in zip(open(args.exe, "rb").read(), out) if a != b)
    print(f"  bytes changed    {changed}")

    if args.dry_run:
        print("dry run: nothing written")
        return 0

    os.makedirs(args.outdir, exist_ok=True)
    out_path = os.path.join(args.outdir, os.path.basename(args.exe))
    open(out_path, "wb").write(out)
    print(f"wrote {out_path} ({len(out)} bytes)")
    print(f"sha256 {hashlib.sha256(out).hexdigest()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
