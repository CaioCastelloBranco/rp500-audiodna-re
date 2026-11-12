#!/usr/bin/env python3
"""Generate the simulator-only scan-test gates from the production gate.

s3b_gate_scan_test.asm : writes 00 02 49 (585) to 0xF6AA, then runs the REAL
                         production scan.  Positive control for the payload.
s3b_gate_scan_neg.asm  : writes 00 02 48 (584), then the same scan.  Negative
                         control: the gate must stay on the stock path.

The production gate (s3b_gate.asm) is never modified.  The test write is
appended AFTER stock_path, and both jumps are relative, so relocating the
block to 0xE095 cannot leave an internal absolute target behind.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
src = (ROOT / "04_analysis_scripts" / "s3b_gate.asm").read_text()
assert src.count("first_byte:\n") == 1

for name, val, module in (
        ("s3b_gate_scan_test", "0x49", "s3b_gate_scan_test"),
        ("s3b_gate_scan_neg", "0x48", "s3b_gate_scan_neg")):
    out = src.replace(".module s3b_gate", ".module " + module)
    # first_byte now jumps forward to the test write; the scan itself starts
    # at do_scan and is byte-identical to the production gate.
    out = out.replace("first_byte:\n",
                      "first_byte:\n\tsjmp\ttest_write\ndo_scan:\n", 1)
    test_write = (
        "\ntest_write:\n"
        "\t;; SIMULATOR-ONLY test write: cab value at 0xF6AA\n"
        "\tmov\tdptr, #0xF6AA\n"
        "\tmov\ta, #0x00\n"
        "\tmovx\t@dptr, a\n"
        "\tinc\tdptr\n"
        "\tmov\ta, #0x02\n"
        "\tmovx\t@dptr, a\n"
        "\tinc\tdptr\n"
        "\tmov\ta, #" + val + "\n"
        "\tmovx\t@dptr, a\n"
        "\tsjmp\tdo_scan\n"
    )
    out = out.rstrip() + "\n" + test_write
    path = ROOT / "04_analysis_scripts" / (name + ".asm")
    path.write_text(out)
    print("wrote", path.name)
