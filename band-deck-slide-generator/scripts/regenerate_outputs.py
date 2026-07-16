#!/usr/bin/env python3
"""Regenerate marp.md and HTML files from canonical YAML deck files.

Usage (from project root):
    uv run python band-deck-slide-generator/scripts/regenerate_outputs.py
    uv run python band-deck-slide-generator/scripts/regenerate_outputs.py data/songs/goodness-of-god/goodness-of-god.yaml
"""

import argparse
import glob
import subprocess
import sys
from pathlib import Path

from band_deck_helpers import generate_practice_marp, load_yaml, write_text


def render_html(marp_path: Path) -> Path:
    """Render a Marp markdown file to HTML using the Marp CLI."""
    html_path = marp_path.with_suffix("").with_suffix(".html")
    subprocess.run(
        ["marp", "--html", str(marp_path), "-o", str(html_path)],
        check=True,
        capture_output=True,
        stdin=subprocess.DEVNULL,
        text=True,
    )
    return html_path


def regenerate_one(yaml_path: Path) -> tuple[Path, Path]:
    """Regenerate Marp and HTML files for one canonical YAML deck."""
    marp_path = yaml_path.with_suffix(".marp.md")
    deck = load_yaml(yaml_path)
    marp = generate_practice_marp(deck)
    write_text(marp_path, marp)
    html_path = render_html(marp_path)
    return marp_path, html_path


def regenerate_all(songs_glob: str = "data/songs/**/*.yaml") -> list[Path]:
    """Regenerate Marp and HTML files for every YAML path matched by ``songs_glob``."""
    paths: list[Path] = []
    for path in sorted(glob.glob(songs_glob, recursive=True)):
        src = Path(path)
        yaml_path = src.resolve()

        try:
            marp_path, html_path = regenerate_one(yaml_path)
        except (OSError, ValueError) as exc:
            print(f"ERROR generating deck for {yaml_path}: {exc}", file=sys.stderr)
            continue
        except subprocess.CalledProcessError as exc:
            detail = exc.stderr.strip() if exc.stderr else str(exc)
            print(f"ERROR rendering HTML for {yaml_path}: {detail}", file=sys.stderr)
            continue

        print(f"Wrote {marp_path}")
        print(f"Wrote {html_path}")
        paths.append(marp_path)

    return paths


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for bulk or targeted Marp regeneration."""
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
    """Regenerate requested Marp files and return a process exit code."""
    args = parse_args(argv)

    if args.yaml_paths:
        for yaml_path in args.yaml_paths:
            if not yaml_path.exists():
                print(f"ERROR: not found: {yaml_path}", file=sys.stderr)
                return 2
            try:
                marp_path, html_path = regenerate_one(yaml_path)
                print(f"Wrote {marp_path}")
                print(f"Wrote {html_path}")
            except (OSError, ValueError) as exc:
                print(f"ERROR {yaml_path}: {exc}", file=sys.stderr)
                return 2
            except subprocess.CalledProcessError as exc:
                detail = exc.stderr.strip() if exc.stderr else str(exc)
                print(f"ERROR rendering HTML for {yaml_path}: {detail}", file=sys.stderr)
                return 2
    else:
        regenerate_all()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
