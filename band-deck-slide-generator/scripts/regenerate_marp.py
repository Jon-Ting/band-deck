#!/usr/bin/env python3
"""Regenerate marp.md files from canonical YAML deck files.

Usage (from project root):
    uv run python band-deck-slide-generator/scripts/regenerate_marp.py
    uv run python band-deck-slide-generator/scripts/regenerate_marp.py data/songs/goodness-of-god/goodness-of-god.yaml
"""

import argparse
import glob
import sys
from pathlib import Path

from band_deck_helpers import generate_practice_marp, load_yaml, write_text


def regenerate_all(songs_glob: str = "data/songs/**/*.yaml") -> list[Path]:
    paths: list[Path] = []
    for path in sorted(glob.glob(songs_glob, recursive=True)):
        src = Path(path)
        yaml_path = src.resolve()
        marp_path = yaml_path.with_suffix(".marp.md")

        try:
            deck = load_yaml(yaml_path)
        except (OSError, ValueError) as exc:
            print(f"ERROR loading {yaml_path}: {exc}", file=sys.stderr)
            continue

        try:
            marp = generate_practice_marp(deck)
        except (OSError, ValueError) as exc:
            print(f"ERROR generating Marp for {yaml_path}: {exc}", file=sys.stderr)
            continue

        write_text(marp_path, marp)
        print(f"Wrote {marp_path}")
        paths.append(marp_path)

    return paths


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "yaml_paths",
        nargs="*",
        metavar="YAML",
        type=Path,
        help="One or more canonical YAML deck files (default: all data/songs/**/*.yaml)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.yaml_paths:
        for yaml_path in args.yaml_paths:
            if not yaml_path.exists():
                print(f"ERROR: not found: {yaml_path}", file=sys.stderr)
                return 2
            marp_path = yaml_path.with_suffix(".marp.md")
            try:
                deck = load_yaml(yaml_path)
                marp = generate_practice_marp(deck)
                write_text(marp_path, marp)
                print(f"Wrote {marp_path}")
            except (OSError, ValueError) as exc:
                print(f"ERROR {yaml_path}: {exc}", file=sys.stderr)
                return 2
    else:
        regenerate_all()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
