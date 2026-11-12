#!/usr/bin/env python3
"""Extract text from the newly added service/schematic PDFs and grep for the
DSP/BOM keywords that matter to the two-chip question."""
import os
import re
import sys

from pypdf import PdfReader

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "03_docs")

FILES = [
    "DigiTech-GSP-2112-Schematics.pdf",
    "Digitech-GSP-2101-Schematics.pdf",
    "DigiTech-GNX-2-Service-Manual.pdf",
    "digitech_rp50_guitar_multi_effects_pedal.pdf",
]

KEYWORDS = re.compile(
    r"(72-1002|Audio\s*DNA|AudioDNA|DNA2|DSP|CPLD|EPM3032|EPM|SDRAM|"
    r"TAS1020|CS42426|AK4556|flash|74AC138|74HC574)",
    re.IGNORECASE,
)


def main():
    for name in FILES:
        path = os.path.join(DOCS, name)
        if not os.path.exists(path):
            print("MISSING:", name)
            continue
        print("=" * 78)
        print(name)
        print("=" * 78)
        try:
            reader = PdfReader(path)
            print("pages:", len(reader.pages))
            for i, page in enumerate(reader.pages):
                try:
                    text = page.extract_text() or ""
                except Exception as exc:  # noqa: BLE001
                    text = ""
                    print("  page %d: extract error %s" % (i + 1, exc))
                hits = sorted({m.group(0) for m in KEYWORDS.finditer(text)})
                if hits:
                    print("  page %d: %s" % (i + 1, ", ".join(hits)))
                    for line in text.splitlines():
                        if KEYWORDS.search(line):
                            print("      " + line.strip()[:160])
        except Exception as exc:  # noqa: BLE001
            print("  open error:", exc)
        print()


if __name__ == "__main__":
    main()
