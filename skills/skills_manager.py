#!/usr/bin/env python3
"""Manage Claude Code skills: pack from ~/.claude/skills into repo, or install from repo."""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path


def find_skills(root: Path) -> list[Path]:
    """Return list of skill directories (those containing SKILL.md) under root."""
    skills = []
    if not root.is_dir():
        return skills
    for entry in sorted(root.iterdir()):
        if entry.is_dir() and (entry / "SKILL.md").exists():
            skills.append(entry)
    return skills


def sync_skills(
    source: Path,
    target: Path,
    backup: bool = False,
    dry_run: bool = False,
    verbose: bool = False,
) -> None:
    """Sync skill directories from source to target.

    Args:
        source: Directory containing skill subdirectories.
        target: Destination directory.
        backup: If True, rename existing target dirs to .bak.TIMESTAMP before copying.
        dry_run: If True, only print what would be done.
        verbose: If True, print per-file details.
    """
    skills = find_skills(source)
    if not skills:
        print(f"No skills found in '{source}'")
        return

    target.mkdir(parents=True, exist_ok=True)

    for skill_dir in skills:
        name = skill_dir.name
        dest = target / name
        action = "UPDATE" if dest.exists() else "NEW"

        if dest.exists() and backup:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            backup_path = target / f"{name}.bak.{timestamp}"
            if dry_run:
                print(f"[DRY-RUN] BACKUP: {dest} -> {backup_path}")
            else:
                if verbose:
                    print(f"BACKUP: {dest} -> {backup_path}")
                shutil.move(str(dest), str(backup_path))

        if dry_run:
            print(f"[DRY-RUN] {action}: {skill_dir} -> {dest}")
        else:
            if dest.exists():
                shutil.rmtree(str(dest))
            shutil.copytree(str(skill_dir), str(dest))
            if verbose:
                for f in sorted(dest.rglob("*")):
                    if f.is_file():
                        print(f"  COPIED: {f.relative_to(target)}")
            print(f"{action}: {name}")


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
        do_backup = False
    else:
        source = args.source or script_dir
        target = args.target
        do_backup = True

    if args.verbose:
        print(f"Source: {source}")
        print(f"Target: {target}")
        print(f"Backup: {do_backup}")
        print()

    if not source.is_dir():
        print(f"Error: source directory '{source}' does not exist", file=sys.stderr)
        sys.exit(1)

    sync_skills(
        source=source,
        target=target,
        backup=do_backup,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    main()
