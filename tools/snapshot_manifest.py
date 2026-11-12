#!/usr/bin/env python3
"""Write or verify a byte-exact manifest of the whole project.

The archive has no remote, so a snapshot is a plain folder copy.  This script
makes that copy *auditable*: it hashes every file on disk (except the git
database, the snapshot folder itself and Python bytecode), and can re-check
those hashes after the copy has been moved to another machine.

Usage:
    python snapshot_manifest.py --write     # create 99_snapshot/MANIFEST.sha256
    python snapshot_manifest.py --verify    # re-check the manifest on this tree
    python snapshot_manifest.py --verify --root D:\\elsewhere\\RP500

Exit codes: 0 = clean, 1 = differences found, 2 = usage/environment error.
"""
import argparse
import hashlib
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ROOT = os.path.dirname(HERE)

EXCLUDE_DIRS = {".git", "99_snapshot", "__pycache__", ".pytest_cache"}
EXCLUDE_SUFFIX = (".pyc", ".pyo")

MANIFEST_REL = os.path.join("99_snapshot", "MANIFEST.sha256")


def iter_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in EXCLUDE_DIRS)
        for name in sorted(filenames):
            if name.endswith(EXCLUDE_SUFFIX):
                continue
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root).replace("\\", "/")
            yield full, rel


def sha256_of(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def git(*args, root):
    try:
        out = subprocess.run(["git"] + list(args), cwd=root, capture_output=True,
                             text=True, timeout=60)
        return out.stdout.strip() if out.returncode == 0 else ""
    except Exception:
        return ""


def write_manifest(root):
    out_path = os.path.join(root, MANIFEST_REL)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    rows = []
    total = 0
    for full, rel in iter_files(root):
        size = os.path.getsize(full)
        total += size
        rows.append("%s  %s" % (sha256_of(full), rel))
    commit = git("rev-parse", "HEAD", root=root) or "(not a git checkout)"
    tag = git("describe", "--tags", "--exact-match", "HEAD", root=root)
    header = [
        "# RP500 project snapshot manifest",
        "# commit: %s%s" % (commit, ("  tag: " + tag) if tag else ""),
        "# files: %d" % len(rows),
        "# bytes: %d" % total,
        "# scope: every file except .git/, 99_snapshot/ and __pycache__/",
        "# verify: python 04_analysis_scripts/snapshot_manifest.py --verify",
    ]
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(header) + "\n")
        for r in rows:
            f.write(r + "\n")
    print("wrote %s" % out_path)
    print("  commit : %s%s" % (commit, ("  (tag %s)" % tag) if tag else ""))
    print("  files  : %d" % len(rows))
    print("  bytes  : %d (%.1f MB)" % (total, total / 1048576))
    return 0


def verify_manifest(root, manifest_path=None):
    out_path = manifest_path or os.path.join(root, MANIFEST_REL)
    if not os.path.exists(out_path):
        print("FAIL: no manifest at %s" % out_path)
        return 2
    want = {}
    header = {}
    with open(out_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            if line.startswith("#"):
                if ":" in line:
                    k, v = line[1:].split(":", 1)
                    header[k.strip()] = v.strip()
                continue
            digest, rel = line.split("  ", 1)
            want[rel] = digest

    have = {rel: sha256_of(full) for full, rel in iter_files(root)}

    missing = sorted(set(want) - set(have))
    extra = sorted(set(have) - set(want))
    changed = sorted(r for r in want if r in have and have[r] != want[r])

    print("manifest : %s" % out_path)
    print("  recorded: %s files, %s bytes, commit %s"
          % (header.get("files", "?"), header.get("bytes", "?"),
             header.get("commit", "?")))
    print("  on disk : %d files" % len(have))
    ok = not (missing or extra or changed)
    print("  missing : %d" % len(missing))
    print("  extra   : %d" % len(extra))
    print("  changed : %d" % len(changed))
    for label, items in (("missing", missing), ("extra", extra), ("changed", changed)):
        for r in items[:20]:
            print("    %-7s %s" % (label, r))
        if len(items) > 20:
            print("    ... %d more %s" % (len(items) - 20, label))
    print()
    print("VERDICT: %s" % ("IDENTICAL" if ok else "DIFFERS"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--write", action="store_true")
    g.add_argument("--verify", action="store_true")
    ap.add_argument("--root", default=DEFAULT_ROOT)
    ap.add_argument("--manifest", default=None,
                    help="path to a manifest (default: 99_snapshot/MANIFEST.sha256)")
    args = ap.parse_args()
    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        print("FAIL: not a directory: %s" % root)
        return 2
    man = os.path.abspath(args.manifest) if args.manifest else None
    return write_manifest(root) if args.write else verify_manifest(root, man)


if __name__ == "__main__":
    sys.exit(main())
