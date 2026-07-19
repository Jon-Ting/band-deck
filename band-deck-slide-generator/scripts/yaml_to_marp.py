#!/usr/bin/env python3
"""Convert canonical band-deck YAML to Marp Markdown.

Usage:
    uv run python band-deck-slide-generator/scripts/yaml_to_marp.py SONG.yaml
    uv run python band-deck-slide-generator/scripts/yaml_to_marp.py SONG.yaml \\
        --output custom-name.marp.md
    uv run python band-deck-slide-generator/scripts/yaml_to_marp.py SONG.yaml \\
        --to-key G --output SONG-G.marp.md
    uv run python band-deck-slide-generator/scripts/yaml_to_marp.py SONG.yaml \\
        --to-key G --write-yaml SONG-G.yaml --output SONG-G.marp.md
    uv run python band-deck-slide-generator/scripts/yaml_to_marp.py SONG.yaml \\
        --to-key G --dry-run

Inputs:
    SONG.yaml must use the canonical band-deck slide-generator schema with
    top-level request, metadata, sources, normalised_chordpro, and arrangement
    mappings. Legacy app-side SongYAML is not accepted by this portable script.

Outputs:
    By default the generated Marp Markdown is written beside the input YAML as
    SONG.marp.md. Use --output/-o to choose a different .marp.md path. This
    script does not render HTML; use regenerate_outputs.py or render_marp.sh after
    generating Marp when an HTML deliverable is needed. When --dry-run is used
    without --output, Marp Markdown is printed to stdout instead of written.

Transposition:
    --to-key/-k transposes bracketed ChordPro chord tokens in memory before
    generating Marp. Unless --dry-run is used, the transposed YAML is also
    written back to the original file or to --write-yaml/-w when provided.
"""

import argparse
import logging
import re
import sys
from pathlib import Path

from band_deck_helpers import generate_practice_marp, load_yaml, write_text
from src.utils.chord_parser import (
    get_semitone_shift,
    normalize_chord_superscripts,
    transpose_chord_string,
)


logger = logging.getLogger(__name__)

# Bracketed ``[Chord]`` tokens using the unified grammar from
# ``src.utils.chord_parser``. Tighter than the legacy permissive matcher.
CHORD_BRACKET_RE = re.compile(
    r"\[([A-G][b#]?(?:m(?:aj|in)?|dim|aug|sus[24]?|add[0-9]+)?(?:[b#]?[0-9]+)*(?:/[A-G][b#]?)?)\]"
)

KEY_RE = re.compile(r"^(\s*)(target_key|requested_key):\s*\S+")


def _transpose_chord(chord: str, semitones: int) -> str:
    """Transpose a single chord token by semitone count.

    Delegates to :func:`src.utils.chord_parser.transpose_chord_string`,
    which preserves quality, extensions, alterations (``b9``, ``#11``,
    ``b5``, ``7b9#11b13``), and slash-bass structures while only
    shifting the root and bass notes. Legacy Unicode chord text (e.g.
    ``G\u2077``) is normalised to ASCII before parsing.
    """
    return transpose_chord_string(normalize_chord_superscripts(chord), semitones)


def _transpose_chordpro_text(text: str, semitones: int) -> str:
    """Transpose all bracketed ChordPro chord tokens in one text line."""
    def repl(m: re.Match[str]) -> str:
        return f"[{_transpose_chord(m.group(1), semitones)}]"

    return CHORD_BRACKET_RE.sub(repl, text)


def _semitone_shift(from_key: str, to_key: str) -> int:
    """Return the chromatic semitone offset from one key to another.

    Delegates to :func:`src.utils.chord_parser.get_semitone_shift` and
    raises :class:`ValueError` for unknown keys (matching the legacy
    contract this module exposed to callers).
    """
    shift = get_semitone_shift(from_key, to_key)
    if shift == 0 and from_key and to_key and from_key != to_key:
        raise ValueError(f"Unknown key: {from_key} or {to_key}")
    return shift


def _transpose_yaml_text(text: str, from_key: str, to_key: str) -> str:
    """Transpose chordpro lines and update keys in raw YAML text,
    preserving all formatting."""
    semitones = _semitone_shift(from_key, to_key)

    lines = text.split("\n")
    out: list[str] = []
    # Pattern: optional quote, then chord content, then optional quote + optional trailing space
    chordpro_re = re.compile(
        r"^(\s*- chordpro:\s*)(['\"]?)(.*?)(\2)(\s*)$"
    )

    for line in lines:
        # Transpose chordpro lines
        if line.lstrip().startswith("- chordpro:"):
            m = chordpro_re.match(line)
            if m:
                prefix = m.group(1)
                quote = m.group(2)
                content = m.group(3)
                suffix = m.group(5)
                content = _transpose_chordpro_text(content, semitones)
                out.append(f"{prefix}{quote}{content}{quote}{suffix}")
            else:
                # Fallback: unquoted chordpro value
                m2 = re.match(r"^(\s*- chordpro:\s+)(.*)", line)
                if m2:
                    prefix = m2.group(1)
                    content = _transpose_chordpro_text(m2.group(2), semitones)
                    out.append(f"{prefix}{content}")
                else:
                    out.append(line)
        # Update key fields
        elif KEY_RE.match(line):
            out.append(KEY_RE.sub(rf"\1\2: {to_key}", line))
        else:
            out.append(line)

    return "\n".join(out)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for YAML-to-Marp conversion and transposition."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("deck_yaml", type=Path, help="Canonical song deck YAML")
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output .marp.md path (default: beside input YAML as NAME.marp.md).",
    )
    parser.add_argument(
        "--to-key",
        "-k",
        type=str,
        metavar="KEY",
        help="Transpose chords to KEY (e.g. C, G, D). Updates target_key in YAML.",
    )
    parser.add_argument(
        "--write-yaml",
        "-w",
        type=Path,
        metavar="PATH",
        help="Write transposed YAML to PATH (default: update original file in-place).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print transposed YAML to stdout without modifying files.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Convert a canonical deck YAML file to Marp and return an exit code."""
    args = parse_args(argv)

    yaml_path: Path = args.deck_yaml
    transposed = args.to_key is not None

    try:
        deck = load_yaml(yaml_path)
    except (OSError, ValueError) as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 2

    if transposed:
        metadata = deck.get("metadata", {})
        from_key = metadata.get("target_key") or metadata.get("requested_key")
        if not from_key:
            sys.stderr.write("error: no target_key or requested_key found in YAML\n")
            return 2

        # Transpose in the dict for Marp generation
        try:
            semitones = _semitone_shift(from_key, args.to_key)
        except ValueError as exc:
            sys.stderr.write(f"error: {exc}\n")
            return 2

        sections = deck.get("normalised_chordpro", {}).get("sections", {})
        for section in sections.values():
            if not isinstance(section, dict):
                continue
            for line in section.get("lines") or []:
                if isinstance(line, dict) and "chordpro" in line:
                    line["chordpro"] = _transpose_chordpro_text(line["chordpro"], semitones)

        metadata["target_key"] = args.to_key
        if "requested_key" in deck.get("request", {}):
            deck["request"]["requested_key"] = args.to_key

        # Transpose in the raw text to preserve formatting
        try:
            original_text = yaml_path.read_text(encoding="utf-8")
            transposed_text = _transpose_yaml_text(original_text, from_key, args.to_key)
        except (OSError, ValueError) as exc:
            sys.stderr.write(f"error: {exc}\n")
            return 2

    try:
        marp_markdown = generate_practice_marp(deck)
    except (OSError, ValueError) as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 2

    # Write Marp output
    output_path = args.output or yaml_path.with_suffix(".marp.md")
    if args.dry_run and not args.output:
        sys.stdout.write(marp_markdown)
    else:
        write_text(output_path, marp_markdown)
        sys.stdout.write(f"wrote: {output_path}\n")

    # Write transposed YAML
    if transposed:
        if not args.dry_run:
            write_path = args.write_yaml or yaml_path
            write_text(write_path, transposed_text)
            sys.stdout.write(f"wrote: {write_path}\n")
        else:
            sys.stdout.write("\n--- transposed yaml (dry run) ---\n")
            sys.stdout.write(transposed_text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
