#!/usr/bin/env python3
"""Cut a version snapshot into 99_snapshot/ and keep them all.

The project lives in one folder with no remote, so versions are kept *inside*
it.  This script makes each version self-describing and verifiable:

    99_snapshot/
        README.md                       index of every version cut
        project.bundle                  cumulative git history (all versions)
        versions/
            2026-11-11_941da76/
                MANIFEST.sha256         byte-exact content of that version
                NOTES.md                what the version asserts

The git history is cumulative, so **one** bundle serves every version: to get
any of them back, clone the bundle and check out its tag.  Per version we store
a manifest (small) rather than another 220 MB copy of the tree.

Usage:
    python cut_snapshot.py                 # cut the current HEAD
    python cut_snapshot.py --check         # verify every version folder
    python cut_snapshot.py --force         # cut even if the tree is dirty
"""
import argparse
import datetime
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SNAP = os.path.join(ROOT, "99_snapshot")
VERS = os.path.join(SNAP, "versions")
BUNDLE = os.path.join(SNAP, "project.bundle")

sys.path.insert(0, HERE)
import snapshot_manifest as sm  # noqa: E402


def git(*args):
    r = subprocess.run(["git"] + list(args), cwd=ROOT, capture_output=True,
                       text=True, timeout=120)
    if r.returncode != 0:
        raise RuntimeError("git %s failed: %s" % (" ".join(args), r.stderr.strip()))
    return r.stdout.strip()


def tree_clean():
    return git("status", "--porcelain") == ""


def index_versions():
    """Return [(folder, tag, commit, files, bytes, cut)] newest first."""
    out = []
    if not os.path.isdir(VERS):
        return out
    names = [n for n in os.listdir(VERS)
             if os.path.isdir(os.path.join(VERS, n))]
    # newest first by manifest mtime: commit hashes are not ordered by time
    def _mt(n):
        man = os.path.join(VERS, n, "MANIFEST.sha256")
        return os.path.getmtime(man) if os.path.exists(man) else 0
    for name in sorted(names, key=_mt, reverse=True):
        d = os.path.join(VERS, name)
        if not os.path.isdir(d):
            continue
        man = os.path.join(d, "MANIFEST.sha256")
        tag = commit = "?"
        files = nbytes = cut = "?"
        if os.path.exists(man):
            with open(man, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.startswith("#"):
                        continue
                    k, _, v = line[1:].partition(":")
                    k, v = k.strip(), v.strip()
                    if k == "tag":
                        tag = v
                    elif k == "commit":
                        commit = v
                    elif k == "files":
                        files = v
                    elif k == "bytes":
                        nbytes = v
                    elif k == "cut":
                        cut = v
        out.append((name, tag, commit, files, nbytes, cut))
    return out


def write_index():
    rows = index_versions()
    L = []
    L.append("# Version store")
    L.append("")
    L.append("Every version cut with `04_analysis_scripts/cut_snapshot.py`, newest")
    L.append("first. The project has no remote, so these live inside the folder.")
    L.append("")
    L.append("| version folder | tag | commit | files | bytes | cut |")
    L.append("|---|---|---|---|---|---|")
    for name, tag, commit, files, nbytes, cut in rows:
        L.append("| `%s` | `%s` | `%s` | %s | %s | %s |"
                 % (name, tag, commit[:12], files, nbytes, cut))
    L.append("")
    L.append("## Using it")
    L.append("")
    L.append("```powershell")
    L.append("# what versions exist")
    L.append("python 04_analysis_scripts/cut_snapshot.py --check")
    L.append("")
    L.append("# verify the CURRENT tree against a version's manifest")
    L.append("python 04_analysis_scripts/snapshot_manifest.py --verify \\")
    L.append("       --manifest 99_snapshot/versions/<folder>/MANIFEST.sha256")
    L.append("")
    L.append("# recover any version from the bundle")
    L.append("git clone 99_snapshot/project.bundle  RP500-<tag>")
    L.append("cd RP500-<tag> ; git checkout <tag>")
    L.append("```")
    L.append("")
    L.append("`project.bundle` carries the full history, so it is rewritten on every")
    L.append("cut rather than accumulated; the per-version manifests are what make")
    L.append("the old states auditable.")
    L.append("")
    open(os.path.join(SNAP, "README.md"), "w", encoding="utf-8", newline="\n").write(
        "\n".join(L))


def cut(force=False):
    os.makedirs(VERS, exist_ok=True)
    if not os.path.isdir(os.path.join(ROOT, ".git")):
        print("FAIL: not a git repository: %s" % ROOT)
        return 2
    if not tree_clean() and not force:
        print("FAIL: working tree is dirty. Commit first, or pass --force.")
        print(git("status", "--short"))
        return 2

    commit = git("rev-parse", "HEAD")
    short = commit[:7]
    tag = git("describe", "--tags", "--exact-match", "HEAD") if git(
        "tag", "--points-at", "HEAD") else ""
    if not tag:
        tag = "untagged"
    today = datetime.date.today().isoformat()
    name = "%s_%s" % (today, short)
    d = os.path.join(VERS, name)
    os.makedirs(d, exist_ok=True)

    # manifest of the tree as it stands
    man = os.path.join(d, "MANIFEST.sha256")
    rows = []
    total = 0
    for full, rel in sm.iter_files(ROOT):
        size = os.path.getsize(full)
        total += size
        rows.append("%s  %s" % (sm.sha256_of(full), rel))
    header = [
        "# RP500 project snapshot manifest",
        "# commit: %s" % commit,
        "# tag: %s" % tag,
        "# cut: %s" % today,
        "# files: %d" % len(rows),
        "# bytes: %d" % total,
        "# scope: every file except .git/, 99_snapshot/ and __pycache__/",
        "# verify: python 04_analysis_scripts/snapshot_manifest.py --verify"
        " --manifest <this file>",
    ]
    with open(man, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(header) + "\n")
        for r in rows:
            f.write(r + "\n")

    # cumulative history bundle
    try:
        git("bundle", "create", BUNDLE, "--all")
    except RuntimeError as e:
        print("WARN: bundle failed: %s" % e)

    # per-version notes
    gates = []
    for label, cmd in (("verify_all.py", [sys.executable, "verify_all.py"]),
                       ("audit_claims.py",
                        [sys.executable, os.path.join("04_analysis_scripts",
                                                      "audit_claims.py")]),
                       ("prove_claims.py",
                        [sys.executable, os.path.join("04_analysis_scripts",
                                                      "prove_claims.py")])):
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                           timeout=1800)
        tail = [l for l in r.stdout.splitlines() if "RESULT" in l
                or "AUDIT RESULT" in l or "new claims hold" in l]
        gates.append("| `%s` | %s | exit %d |"
                     % (label, (tail[-1].strip() if tail else "(no summary)"),
                        r.returncode))

    notes = [
        "# Version %s" % name,
        "",
        "| | |",
        "|---|---|",
        "| commit | `%s` |" % commit,
        "| tag | `%s` |" % tag,
        "| files | %d |" % len(rows),
        "| bytes | %d (%.1f MB) |" % (total, total / 1048576),
        "| cut | %s |" % today,
        "",
        "## Gates at this version",
        "",
        "| gate | result | |",
        "|---|---|---|",
    ] + gates + [
        "",
        "## Verify this version",
        "",
        "```powershell",
        "python 04_analysis_scripts/snapshot_manifest.py --verify ^",
        "       --manifest 99_snapshot/versions/%s/MANIFEST.sha256" % name,
        "```",
        "",
        "## Recover this version from history",
        "",
        "```powershell",
        "git clone 99_snapshot/project.bundle RP500-%s" % name,
        "cd RP500-%s" % name,
        "git checkout %s" % (tag if tag != "untagged" else commit),
        "```",
        "",
    ]
    open(os.path.join(d, "NOTES.md"), "w", encoding="utf-8", newline="\n").write(
        "\n".join(notes))

    write_index()
    print("cut %s" % name)
    print("  commit : %s (%s)" % (commit, tag))
    print("  files  : %d, %.1f MB" % (len(rows), total / 1048576))
    print("  folder : %s" % d)
    for g in gates:
        print("  " + g.strip("| "))
    return 0


def check():
    rows = index_versions()
    if not rows:
        print("no versions cut yet")
        return 0
    print("%-24s %-24s %-12s %8s %14s" %
          ("version", "tag", "commit", "files", "bytes"))
    for name, tag, commit, files, nbytes, _cut in rows:
        print("%-24s %-24s %-12s %8s %14s"
              % (name, tag, commit[:12], files, nbytes))
    print()
    bundle_ok = os.path.exists(BUNDLE)
    print("bundle: %s (%s)" % (BUNDLE,
                               ("%.1f MB" % (os.path.getsize(BUNDLE) / 1048576))
                               if bundle_ok else "MISSING"))
    if bundle_ok:
        r = subprocess.run(["git", "bundle", "verify", BUNDLE], cwd=ROOT,
                           capture_output=True, text=True, timeout=300)
        ok = "is okay" in (r.stdout + r.stderr)
        print("        git bundle verify: %s" % ("OK" if ok else "FAILED"))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    return check() if args.check else cut(force=args.force)


if __name__ == "__main__":
    sys.exit(main())
