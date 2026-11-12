#!/usr/bin/env python3
"""Extract text and tables from a .docx without python-docx.

Usage: python docx_text.py FILE.docx
"""
import sys
import zipfile
import xml.etree.ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def cell_text(tc):
    return "".join(t.text or "" for t in tc.iter(W + "t")).strip()


def para_text(p):
    return "".join(t.text or "" for t in p.iter(W + "t"))


def main(path):
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml")
    root = ET.fromstring(xml)
    body = root.find(W + "body")

    for el in body:
        tag = el.tag.replace(W, "")
        if tag == "p":
            txt = para_text(el).strip()
            if txt:
                print(txt)
        elif tag == "tbl":
            print("\n[TABLE]")
            for tr in el.findall(W + "tr"):
                cells = [cell_text(tc) for tc in tr.findall(W + "tc")]
                print(" | ".join(cells))
            print("[/TABLE]\n")


if __name__ == "__main__":
    main(sys.argv[1])
