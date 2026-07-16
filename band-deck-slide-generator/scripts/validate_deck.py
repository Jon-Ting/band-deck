#!/usr/bin/env python3
"""Validate canonical band-deck YAML."""

import argparse
import logging
import sys
from pathlib import Path

from band_deck_helpers import (
    format_error_path,
    load_yaml,
    schema_errors,
    semantic_errors,
)


logger = logging.getLogger(__name__)


def default_schema_path() -> Path:
    """Return the packaged canonical song-deck schema path."""
    return Path(__file__).resolve().parents[1] / "schema/song-deck.schema.yaml"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for validating a canonical deck YAML file."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("deck_yaml", type=Path, help="Canonical song deck YAML")
    parser.add_argument(
        "--schema",
        type=Path,
        default=default_schema_path(),
        help="YAML JSON Schema to validate against",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Validate schema and semantic constraints, returning a process exit code."""
    args = parse_args(argv)

    try:
        deck = load_yaml(args.deck_yaml)
        schema = load_yaml(args.schema)
    except (OSError, ValueError) as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 2

    errors: list[str] = [
        f"{format_error_path(error)}: {error.message}"
        for error in schema_errors(deck, schema)
    ]
    errors.extend(semantic_errors(deck))

    if errors:
        for error in errors:
            sys.stderr.write(f"invalid: {error}\n")
        return 1

    sys.stdout.write(f"valid: {args.deck_yaml}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
