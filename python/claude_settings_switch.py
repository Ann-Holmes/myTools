#!/usr/bin/env python3
"""Switch the active Claude Code ``settings.json`` between profiles.

Only the top-level ``env`` block is swapped. Every other field (``statusLine``,
``permissions``, ``enabledPlugins``, ``verbose``, ...) is taken from the
*current* active file and carried over unchanged, so non-env edits you make at
any time are preserved and shared across all profiles. The per-profile backups
also get their non-env mirrored from the active file, so each backup stays a
fresh full snapshot.

Files (under ``~/.claude/`` unless ``CLAUDE_SETTINGS_DIR`` is set):
    settings.json                    active file (source of truth for non-env)
    settings.json.backup-<profile>   per-profile env store (+ mirrored non-env)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

CLAUDE_DIR = Path(
    os.environ.get(key="CLAUDE_SETTINGS_DIR", default=os.path.expanduser("~/.claude"))
)
ACTIVE: Path = CLAUDE_DIR / "settings.json"
LOG: Path = CLAUDE_DIR / "settings_switch.log"

# Profiles whose non-env is mirrored from the active file on every switch,
# keeping each backup a current full snapshot. Extend as you add profiles.
MANAGED_PROFILES = ["zai", "deepseek"]


logger = logging.getLogger(name="claude_settings_switch")
logger.setLevel(logging.INFO)
logger.propagate = False
if not logger.handlers:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    _handler = logging.FileHandler(LOG, encoding="utf-8")
    _handler.setFormatter(
        logging.Formatter("[%(asctime)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    )
    logger.addHandler(_handler)


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def atomic_write_json(path: Path, data: dict) -> None:
    """Write JSON to a sibling temp file then atomically replace the target."""
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def backup_path(profile: str) -> Path:
    return CLAUDE_DIR / f"settings.json.backup-{profile}"


def detect_profile(env: dict) -> str:
    """Which managed profile's env matches the given env, else 'unknown'."""
    for p in MANAGED_PROFILES:
        bp = backup_path(p)
        if bp.exists():
            try:
                if read_json(bp).get("env") == env:
                    return p
            except Exception:
                continue
    return "unknown"


def mirror_nonenv(source: dict, profiles: list[str]) -> list[str]:
    """Copy source's non-env fields into each profile's backup, preserving each
    backup's own env. Returns the profiles whose content actually changed."""
    updated = []
    for p in profiles:
        bp = backup_path(p)
        if not bp.exists():
            continue
        try:
            b = read_json(bp)
        except Exception:
            continue
        new = {k: v for k, v in source.items() if k != "env"}
        new["env"] = b.get("env", {})
        if new != b:
            atomic_write_json(bp, new)
            updated.append(p)
    return updated


def switch(profile: str) -> int:
    if profile not in MANAGED_PROFILES:
        print(f"error: unknown profile {profile!r}. managed: {MANAGED_PROFILES}", file=sys.stderr)
        return 2

    target = backup_path(profile)
    if not ACTIVE.exists():
        print(f"error: active file not found: {ACTIVE}", file=sys.stderr)
        return 1
    if not target.exists():
        print(f"error: profile backup not found: {target}", file=sys.stderr)
        return 1

    try:
        active = read_json(ACTIVE)
        tgt = read_json(target)
    except Exception as e:
        print(f"error: failed to parse JSON: {e}", file=sys.stderr)
        logger.error("FAIL parse (%s): %s", profile, e)
        return 1

    if "env" not in active or "env" not in tgt:
        print("error: 'env' block missing in active or target file", file=sys.stderr)
        logger.error("FAIL no-env (%s)", profile)
        return 1

    before = detect_profile(active.get("env", {}))

    # Preserve all non-env from the active file; take env from the target.
    merged = {k: v for k, v in active.items() if k != "env"}
    merged["env"] = tgt["env"]

    try:
        atomic_write_json(ACTIVE, merged)
        mirrored = mirror_nonenv(merged, MANAGED_PROFILES)
    except Exception as e:
        print(f"error: failed to write: {e}", file=sys.stderr)
        logger.error("FAIL write (%s): %s", profile, e)
        return 1

    extra = f"; non-env mirrored to {', '.join(mirrored)}" if mirrored else ""
    logger.info("OK  %s -> %s  (active written%s)", before, profile, extra)
    return 0


def list_profiles() -> int:
    try:
        cur = detect_profile(read_json(ACTIVE).get("env", {}))
    except Exception:
        cur = "unknown"
    print(f"active: {ACTIVE}")
    print(f"current profile: {cur}")
    print("managed profiles:")
    for p in MANAGED_PROFILES:
        bp = backup_path(p)
        state = "OK" if bp.exists() else "MISSING"
        print(f"  {p:12s} [{state}]  {bp}")
    prefix = "settings.json.backup-"
    others = sorted(
        b.name[len(prefix) :]
        for b in CLAUDE_DIR.glob(prefix + "*")
        if not b.name.endswith(".tmp") and b.name[len(prefix) :] not in MANAGED_PROFILES
    )
    if others:
        print(f"other backups (not managed): {', '.join(others)}")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="claude_settings_switch.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "profile",
        nargs="?",
        choices=MANAGED_PROFILES,
        metavar="{profile}",
        help="profile to switch to (one of: %(choices)s)",
    )
    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="list managed profiles and the current one, then exit",
    )
    args: argparse.Namespace = parser.parse_args(args=argv[1:])

    if args.list:
        return list_profiles()
    if args.profile is not None:
        return switch(args.profile)
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
