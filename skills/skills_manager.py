#!/usr/bin/env python3
"""Manage Claude Code skills: pack from ~/.claude/skills into repo, or install from repo."""

import argparse
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pack or install Claude Code skills"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # pack
    pack_parser = sub.add_parser("pack", help="Pack ~/.claude/skills into repo skills/")
    pack_parser.add_argument(
        "--source", type=Path,
        default=Path.home() / ".claude" / "skills",
        help="Source directory (default: ~/.claude/skills)",
    )
    pack_parser.add_argument(
        "--target", type=Path,
        default=None,
        help="Target directory (default: script's directory)",
    )
    pack_parser.add_argument("--dry-run", action="store_true")
    pack_parser.add_argument("-v", "--verbose", action="store_true")

    # install
    install_parser = sub.add_parser("install", help="Install repo skills/ into ~/.claude/skills")
    install_parser.add_argument(
        "--source", type=Path,
        default=None,
        help="Source directory (default: script's directory)",
    )
    install_parser.add_argument(
        "--target", type=Path,
        default=Path.home() / ".claude" / "skills",
        help="Target directory (default: ~/.claude/skills)",
    )
    install_parser.add_argument("--dry-run", action="store_true")
    install_parser.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args()
    script_dir = Path(__file__).resolve().parent

    if args.command == "pack":
        source = args.source
        target = args.target or script_dir
    else:
        source = args.source or script_dir
        target = args.target

    print(f"Source: {source}")
    print(f"Target: {target}")

    # Validate source exists
    if not source.is_dir():
        print(f"Error: source directory '{source}' does not exist", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
