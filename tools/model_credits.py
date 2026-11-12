#!/usr/bin/env python3
"""List every model that worked on the RP500 project.

Source of truth: the OpenCode session database
``%USERPROFILE%\\.local\\share\\opencode\\opencode.db`` (SQLite). Every
assistant message row carries its model, so this reads the **complete**
history -- unlike the HTTP API, which caps a message page at 200 and exposes
no cursor (an earlier version of this script used the API and therefore
under-counted badly; DeepSeek was invisible that way).

The database is copied (with its WAL) to a temp directory before reading, so
the live session is never locked.

Usage:
    python model_credits.py [--dir D:\\OPENCODE\\RP500] [--json]
"""
import argparse
import collections
import datetime
import json
import os
import shutil
import sqlite3
import tempfile

DB = os.path.expanduser(r"~\.local\share\opencode\opencode.db")


def open_db():
    """Copy the live db (+wal/+shm) to a temp dir and open it read-only."""
    if not os.path.exists(DB):
        return None
    tmp = tempfile.mkdtemp(prefix="ocdb_")
    for suffix in ("", "-wal", "-shm"):
        src = DB + suffix
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(tmp, "opencode.db" + suffix))
    return sqlite3.connect(os.path.join(tmp, "opencode.db"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=r"D:\OPENCODE\RP500")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--export", default=None,
                    help="write the per-session/per-model summary to this JSON file")
    args = ap.parse_args()

    con = open_db()
    if con is None:
        print("FAIL: session database not found at", DB)
        return 1
    cur = con.cursor()

    cur.execute("SELECT id, directory, title, time_created FROM session_v2")
    sessions = cur.fetchall()
    target = args.dir.lower().rstrip("\\/")

    tally = collections.Counter()
    variants = collections.Counter()
    tokens = collections.Counter()
    per_session = []

    for sid, directory, title, tc in sessions:
        cur.execute("SELECT type, data FROM session_message WHERE session_id=?", (sid,))
        models = collections.Counter()
        sess_tokens = collections.Counter()
        for t, data in cur.fetchall():
            if t != "assistant":
                continue
            try:
                j = json.loads(data)
            except Exception:
                continue
            m = j.get("model") or {}
            if not m.get("id"):
                continue
            key = f"{m.get('providerID', '?')}/{m['id']}"
            models[key] += 1
            tally[key] += 1
            variants[f"{key} ({m.get('variant', 'default')})"] += 1
            tk = j.get("tokens") or {}
            n = (tk.get("input") or 0) + (tk.get("output") or 0)
            tokens[key] += n
            sess_tokens[key] += n
        when = datetime.datetime.fromtimestamp((tc or 0) / 1000).strftime("%Y-%m-%d %H:%M")
        per_session.append({
            "id": sid, "title": title, "directory": directory, "when": when,
            "models": dict(models), "tokens": dict(sess_tokens),
            "is_project": (directory or "").lower().rstrip("\\/") == target,
        })

    if args.export:
        with open(args.export, "w", encoding="utf-8") as f:
            json.dump({
                "source": DB,
                "note": "per-message model attribution from the OpenCode session "
                        "database; regenerate with model_credits.py",
                "total": dict(tally),
                "variants": dict(variants),
                "tokens": dict(tokens),
                "sessions": per_session,
            }, f, indent=2)
        print(f"\nwrote {args.export}")

    if args.json:
        print(json.dumps({"total": dict(tally), "variants": dict(variants),
                          "sessions": per_session}, indent=2))
        return 0

    print(f"source: {DB}")
    print(f"sessions: {len(sessions)}\n")
    for s in sorted(per_session, key=lambda x: x["when"]):
        flag = "  <-- project" if s["is_project"] else ""
        print(f"  {s['when']}  {s['title']}{flag}")
        print(f"      dir={s['directory']}")
        for k, v in sorted(s["models"].items(), key=lambda kv: -kv[1]):
            print(f"      {k:<48} {v:5d} messages   {s['tokens'][k]:>12,} tok")
    print("\n=== models that produced assistant output (complete history) ===")
    total = sum(tally.values())
    for k, v in tally.most_common():
        print(f"  {k:<48} {v:5d} messages  {100.0*v/total:5.1f}%   {tokens[k]:>12,} tok")
    print(f"  {'TOTAL':<48} {total:5d} messages")
    print("\n=== variants ===")
    for k, v in variants.most_common():
        print(f"  {k:<58} {v:5d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
