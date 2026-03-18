"""
strip_rootfs.py — Strip mandatory-deny paths from a VM rootfs directory.

Usage:
    python strip_rootfs.py <rootfs_dir> [--denies <mandatory_denies.yaml>]

The script:
  1. Reads mandatory_denies.yaml (default: same directory as this script).
  2. Walks the rootfs and removes any file, directory, or symlink whose
     path matches a deny pattern.
  3. Compiles every remaining .py file to .pyc (bytecode) and deletes the
     source .py file so agents run bytecode-only (harder to tamper with).
  4. Logs every removal to stdout.

Matching rules:
  - Entries ending with '/' are treated as directory names.
  - Entries starting with '.' are matched against basename (any depth).
  - All other entries are matched against basename.
  - Absolute deny paths (e.g. /etc/shadow) are matched against their path
    relative to rootfs_dir.
"""

from __future__ import annotations

import argparse
import compileall
import logging
import os
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

import yaml  # PyYAML — bundled with the enclaiv CLI deps


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [strip_rootfs] %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_DENIES_FILE: Final[Path] = Path(__file__).parent / "mandatory_denies.yaml"

# ---------------------------------------------------------------------------
# Immutable config
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class StripConfig:
    rootfs: Path
    deny_paths: tuple[str, ...]


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def load_deny_config(denies_file: Path, rootfs: Path) -> StripConfig:
    """Parse *denies_file* and return an immutable :class:`StripConfig`."""
    if not denies_file.exists():
        log.error("Deny-list file not found: %s", denies_file)
        sys.exit(1)

    with denies_file.open("r", encoding="utf-8") as fh:
        raw: object = yaml.safe_load(fh)

    if not isinstance(raw, dict) or "deny_paths" not in raw:
        log.error("Invalid deny-list YAML: missing 'deny_paths' key in %s", denies_file)
        sys.exit(1)

    entries = raw["deny_paths"]
    if not isinstance(entries, list):
        log.error("'deny_paths' must be a list in %s", denies_file)
        sys.exit(1)

    return StripConfig(
        rootfs=rootfs,
        deny_paths=tuple(str(e) for e in entries),
    )


# ---------------------------------------------------------------------------
# Matching helpers
# ---------------------------------------------------------------------------


def _normalise_deny(pattern: str) -> str:
    """Strip leading './' and trailing whitespace from a pattern."""
    return pattern.strip().lstrip("./")


def _is_denied(rel_path: Path, deny_patterns: tuple[str, ...]) -> bool:
    """
    Return True if *rel_path* (relative to rootfs) matches any deny pattern.

    Matching is done against:
      - The full relative path string (e.g. '.ssh/id_rsa' matches '.ssh/')
      - Any individual path component (basename match for dotfiles)
    """
    rel_str = str(rel_path)
    parts = rel_path.parts  # ('home', 'user', '.ssh', 'id_rsa')

    for raw_pattern in deny_patterns:
        pattern = _normalise_deny(raw_pattern)
        if not pattern:
            continue

        is_dir_pattern = raw_pattern.rstrip().endswith("/")
        pattern_name = pattern.rstrip("/")

        # 1. Exact relative path match (e.g. '.git/config')
        if rel_str == pattern or rel_str == pattern.rstrip("/"):
            return True

        # 2. Prefix match for directory patterns (catches children)
        if is_dir_pattern and (rel_str.startswith(pattern_name + "/") or rel_str == pattern_name):
            return True

        # 3. Basename match (catch dotfiles at any depth)
        for part in parts:
            if part == pattern_name:
                return True

    return False


# ---------------------------------------------------------------------------
# Stripping
# ---------------------------------------------------------------------------


def strip_denied_paths(config: StripConfig) -> int:
    """
    Walk the rootfs and remove every path matched by the deny list.

    Returns the count of removed entries.
    """
    rootfs = config.rootfs
    removed = 0

    # Collect candidates first to avoid modifying the tree while iterating.
    candidates: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(rootfs, topdown=True, followlinks=False):
        dp = Path(dirpath)

        # Check directories — if denied, add to removal list and prune from
        # os.walk so we don't descend into them.
        prune_indices: list[int] = []
        for i, d in enumerate(dirnames):
            full = dp / d
            rel = full.relative_to(rootfs)
            if _is_denied(rel, config.deny_paths):
                candidates.append(full)
                prune_indices.append(i)

        # Remove pruned dirs from dirnames in-place (controls os.walk descent).
        for i in sorted(prune_indices, reverse=True):
            del dirnames[i]

        # Check files and symlinks.
        for fname in filenames:
            full = dp / fname
            rel = full.relative_to(rootfs)
            if _is_denied(rel, config.deny_paths):
                candidates.append(full)

    # Now remove all collected candidates.
    for target in candidates:
        if not target.exists() and not target.is_symlink():
            continue  # already removed (e.g. parent dir removed first)
        try:
            if target.is_symlink() or target.is_file():
                target.unlink()
                log.info("REMOVED file      %s", target.relative_to(rootfs))
            elif target.is_dir():
                shutil.rmtree(target)
                log.info("REMOVED directory %s", target.relative_to(rootfs))
            removed += 1
        except OSError as exc:
            log.error("Failed to remove %s: %s", target, exc)

    return removed


# ---------------------------------------------------------------------------
# Bytecode compilation
# ---------------------------------------------------------------------------


def compile_to_bytecode(rootfs: Path) -> tuple[int, int]:
    """
    Compile all .py files under *rootfs* to .pyc and delete the sources.

    Returns (compiled_count, deleted_count).
    """
    compiled = 0
    deleted = 0

    # compileall.compile_dir writes .pyc files into __pycache__ subdirs.
    success = compileall.compile_dir(
        str(rootfs),
        quiet=1,          # suppress per-file output; we log ourselves
        force=True,
        workers=0,        # use all available CPU cores
    )
    if not success:
        log.warning("compileall reported failures; continuing anyway")

    # Walk again to delete .py sources (keep __pycache__/.pyc files).
    for dirpath, _dirnames, filenames in os.walk(rootfs, followlinks=False):
        for fname in filenames:
            if not fname.endswith(".py"):
                continue
            src = Path(dirpath) / fname
            # Verify the corresponding .pyc actually exists before deleting.
            pyc_dir = Path(dirpath) / "__pycache__"
            pyc_exists = any(pyc_dir.glob(f"{src.stem}.*.pyc")) if pyc_dir.is_dir() else False
            if pyc_exists:
                try:
                    src.unlink()
                    rel = src.relative_to(rootfs)
                    log.info("DELETED source    %s", rel)
                    deleted += 1
                except OSError as exc:
                    log.error("Failed to delete source %s: %s", src, exc)
            else:
                log.warning("No .pyc found for %s — keeping source", src.relative_to(rootfs))
            compiled += 1  # count regardless; compilation may have succeeded

    return compiled, deleted


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Strip mandatory-deny paths from a VM rootfs directory.",
    )
    parser.add_argument(
        "rootfs",
        type=Path,
        help="Path to the rootfs directory to sanitise.",
    )
    parser.add_argument(
        "--denies",
        type=Path,
        default=_DEFAULT_DENIES_FILE,
        metavar="FILE",
        help=f"Path to mandatory_denies.yaml (default: {_DEFAULT_DENIES_FILE})",
    )
    parser.add_argument(
        "--no-bytecode",
        action="store_true",
        default=False,
        help="Skip .py → .pyc compilation and source deletion.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    rootfs: Path = args.rootfs.resolve()
    if not rootfs.is_dir():
        log.error("rootfs path is not a directory: %s", rootfs)
        return 1

    log.info("Stripping rootfs: %s", rootfs)
    log.info("Deny-list file:   %s", args.denies)

    config = load_deny_config(args.denies, rootfs)

    removed = strip_denied_paths(config)
    log.info("Stripped %d path(s) from rootfs", removed)

    if not args.no_bytecode:
        log.info("Compiling Python sources to bytecode …")
        compiled, deleted = compile_to_bytecode(rootfs)
        log.info("Compiled %d .py file(s); deleted %d source(s)", compiled, deleted)

    log.info("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
