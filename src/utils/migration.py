"""Batch migration utility for legacy saved slides.

Slides saved before the multi-format refactor (and before PPTX export was
retired) only carried a single primary artefact plus metadata JSON. This
utility backfills YAML, Marp markdown, and HTML files for any slide that
lacks them so every saved slide participates in the modern multi-format
workflow.

Design notes:

* PPTX text extraction is deliberately skipped. Parsing rendered
  slide text back into structured sections/chords is
  brittle and was considered out of scope: the migration emits a placeholder
  ``Note`` section that carries song metadata and directs the user to
  re-generate from the chart source when the original lyrics and chords are
  missing. Any pre-existing ``.pptx`` filename listed in the metadata is
  kept as a tombstone entry so legacy tooling that still references it
  does not silently lose information.
* The migration is idempotent. Slides whose ``filenames`` already list every
  supported format are skipped unless ``force=True`` is passed. Slides with
  a partial format set always have every format regenerated so partial
  migrations self-heal on the next run.
* Marp CLI rendering failures are tolerated: a plain fallback HTML file is
  written so the slide stays loadable even when the Marp CLI is missing.
* The original ``updated_at`` (user edit timestamp) is preserved. A separate
  ``migrated_at`` field records when this utility last touched the slide.
"""

import json
import logging
import os
import re
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import yaml

from src.utils.chord_parser import normalize_chord_superscripts
from src.utils.html_renderer import RenderError, render_html
from src.utils.marp_generator import MarpOptions, generate_marp
from src.utils.slide_storage import _meta_path, _slide_path, list_slides
from src.utils.yaml_models import SongSection, SongYAML

logger = logging.getLogger(__name__)

SUPPORTED_FORMATS = ("yaml", "marp", "html")
PLACEHOLDER_NOTE = (
    "Lyrics and chords require manual entry or re-generation from the chart source."
)
MIGRATED_AT_KEY = "migrated_at"

# Match ``[ ... ]`` spans across one line so we can rewrite the inner
# chord text without touching other YAML bracket use. ``[^\]\n]+`` stops
# at the first ``]`` or newline; ``re.DOTALL`` is intentionally omitted
# so multi-line spans are never rewritten.
_BRACKETED_CHORD_RE = re.compile(r"\[([^\]\n]+)\]")


def _build_placeholder_song(meta: dict[str, Any]) -> SongYAML:
    """Build a minimal ``SongYAML`` from a legacy slide's stored metadata."""
    artist = (meta.get("artist") or "").strip()
    key = (meta.get("key") or "").strip() or "C"
    return SongYAML(
        title=(meta.get("title") or "Unknown Title").strip(),
        authors=[artist] if artist else ["Unknown"],
        license_number=meta.get("license_number") or meta.get("ccli_number"),
        original_key=key if meta.get("key") else None,
        target_key=key,
        bpm=meta.get("bpm"),
        time_signature=meta.get("time_signature"),
        sections={
            "Note": SongSection(
                name="Note",
                type="verse",
                lines=[],
                notes=[PLACEHOLDER_NOTE],
            )
        },
        arrangement=["Note"],
        practice_notes={"general": [PLACEHOLDER_NOTE]},
    )


def _has_full_format_set(meta: dict[str, Any]) -> bool:
    """Return whether ``meta`` already lists YAML, Marp, and HTML filenames."""
    files = meta.get("filenames") or {}
    return all(fmt in files for fmt in SUPPORTED_FORMATS)


def _write_yaml(slide_id: str, song: SongYAML) -> str:
    """Write the song as YAML and return the basename of the written file."""
    path = _slide_path(slide_id, "yaml")
    with open(path, "w", encoding="utf-8") as yaml_file:
        yaml.safe_dump(
            asdict(song),
            yaml_file,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
        )
    return os.path.basename(path)


def _write_marp(slide_id: str, marp_markdown: str) -> str:
    """Write the rendered Marp markdown and return the basename."""
    path = _slide_path(slide_id, "marp")
    with open(path, "w", encoding="utf-8") as marp_file:
        marp_file.write(marp_markdown)
    return os.path.basename(path)


def _write_html(slide_id: str, marp_markdown: str, song: SongYAML) -> str:
    """Render Marp markdown to HTML with a graceful fallback when Marp fails."""
    path = _slide_path(slide_id, "html")
    try:
        render_html(marp_markdown, output_path=path)
        return os.path.basename(path)
    except (RenderError, OSError, ValueError) as exc:
        # RenderError covers Marp CLI failures, OSError covers filesystem faults,
        # and ValueError covers empty/unsafe-markdown rejections that the batch
        # should tolerate rather than crash on.
        logger.warning(
            "Marp render failed for slide %s, writing fallback HTML: %s",
            slide_id,
            exc,
        )
        _write_html_fallback(path, song)
        return os.path.basename(path)


def _write_html_fallback(path: str, song: SongYAML) -> None:
    """Write a minimal HTML placeholder that still loads when Marp is absent."""
    authors = ", ".join(song.authors) if song.authors else "Unknown"
    body = (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        f"<head><meta charset=\"utf-8\"><title>{song.title}</title></head>\n"
        "<body>\n"
        f"  <h1>{song.title}</h1>\n"
        f"  <p><strong>Authors:</strong> {authors}</p>\n"
        f"  <section><p>{PLACEHOLDER_NOTE}</p></section>\n"
        "</body>\n"
        "</html>\n"
    )
    with open(path, "w", encoding="utf-8") as html_file:
        html_file.write(body)


def _write_metadata(slide_id: str, meta: dict[str, Any]) -> None:
    """Persist updated metadata back to its JSON file."""
    meta_path = _meta_path(slide_id)
    with open(meta_path, "w", encoding="utf-8") as meta_file:
        json.dump(meta, meta_file, indent=2, ensure_ascii=False)


def _migrate_one(meta: dict[str, Any]) -> bool:
    """Migrate a single slide and return ``True`` on success."""
    slide_id = meta.get("id")
    if not slide_id:
        raise RuntimeError("Slide metadata is missing an id field")

    song = _build_placeholder_song(meta)
    # Legacy placeholder songs carry only metadata (no real chords/lyrics),
    # so use the practice-style preset and explicitly force the metadata bar
    # so musicians can still see the song title, key, and authors on the
    # rendered placeholder deck.
    placeholder_options = MarpOptions(
        show_metadata=True,
        show_song_map=True,
        show_practice_notes=False,
    )
    marp_markdown = generate_marp(song, style="practice", options=placeholder_options)

    filenames = dict(meta.get("filenames") or {})
    filenames["yaml"] = _write_yaml(slide_id, song)
    filenames["marp"] = _write_marp(slide_id, marp_markdown)
    filenames["html"] = _write_html(slide_id, marp_markdown, song)

    meta["filenames"] = filenames
    # Record the migration timing separately so user-driven ``updated_at``
    # edits are not silently overwritten by a batch conversion.
    meta[MIGRATED_AT_KEY] = datetime.now(timezone.utc).isoformat()
    _write_metadata(slide_id, meta)
    return True


def normalize_chord_yaml_text(content: str) -> str:
    """Apply :func:`normalize_chord_superscripts` to bracketed chord content.

    Designed for canonical song YAML files: it only touches ``[...]``
    substrings so unrelated bracket use (e.g. inline YAML lists) is
    preserved. The transformation is idempotent — re-running the
    function on already-canonical text yields an identical string,
    which makes the on-disk migration no-op safe.
    """
    return _BRACKETED_CHORD_RE.sub(
        lambda match: f"[{normalize_chord_superscripts(match.group(1))}]",
        content,
    )


def has_legacy_chord_unicode(path: Path) -> bool:
    """Return whether ``path`` contains chord-style Unicode typography.

    Detects the same Unicode characters that
    :func:`src.utils.chord_parser.normalize_chord_superscripts` rewrites
    (superscript digits, music-typography sharp/flat, modifier letters) —
    but only those that appear inside ``[...]`` brackets so unrelated
    typographic characters in lyrics (e.g. ``é``) are ignored.
    """
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    for match in _BRACKETED_CHORD_RE.finditer(content):
        inner = match.group(1)
        if inner != normalize_chord_superscripts(inner):
            return True
    return False


def migrate_chord_yaml_file(path: Path, *, backup: bool = False) -> bool:
    """Normalise bracketed chords in a YAML song file to ASCII in place.

    Returns ``True`` iff the file was modified.

    Idempotent: a file already in canonical ASCII form is a no-op and
    is not rewritten, so callers can re-run the migration freely.

    Args:
        path: Path to the YAML song file.
        backup: When ``True``, write a ``.yaml.bak`` sibling containing
            the original content before rewriting. Defaults to ``False``.
    """
    original = path.read_text(encoding="utf-8")
    rewritten = normalize_chord_yaml_text(original)
    if rewritten == original:
        return False
    if backup:
        backup_path = path.with_name(path.name + ".bak")
        backup_path.write_text(original, encoding="utf-8")
    path.write_text(rewritten, encoding="utf-8")
    return True


def migrate_chord_yaml_files(
    paths: Iterable[Path], *, backup: bool = False
) -> dict[str, int]:
    """Apply :func:`migrate_chord_yaml_file` to many paths.

    Returns a stats dictionary with ``migrated``, ``skipped``, and
    ``errors`` counts. Errors are logged but do not abort the batch.
    """
    stats = {"migrated": 0, "skipped": 0, "errors": 0}
    for path in paths:
        try:
            if not path.is_file():
                stats["errors"] += 1
                logger.warning("Skipping non-file path: %s", path)
                continue
            if migrate_chord_yaml_file(path, backup=backup):
                stats["migrated"] += 1
                logger.info("Migrated chord YAML %s", path)
            else:
                stats["skipped"] += 1
        except Exception as exc:  # defensive: keep batch alive
            stats["errors"] += 1
            logger.error("Failed to migrate chord YAML %s: %s", path, exc)
    return stats


def default_song_yaml_paths(project_root: Path | None = None) -> list[Path]:
    """Return every song YAML file under ``data/songs/<song>/<song>.yaml``.

    Walks ``data/songs/*/<song>.yaml`` relative to ``project_root`` (the
    current working directory by default). Returns an empty list when
    the directory is missing.
    """
    base = (project_root or Path.cwd()) / "data" / "songs"
    if not base.is_dir():
        return []
    paths: list[Path] = []
    for song_dir in sorted(base.iterdir()):
        if not song_dir.is_dir():
            continue
        for yaml_path in sorted(song_dir.glob("*.yaml")):
            paths.append(yaml_path)
    return paths


def migrate_chord_yaml(project_root: Path | None = None) -> dict[str, int]:
    """Migrate every song YAML under ``data/songs/`` to ASCII chord content."""
    return migrate_chord_yaml_files(default_song_yaml_paths(project_root))


def migrate_existing_slides(force: bool = False) -> dict[str, int]:
    """Backfill YAML/Marp/HTML files for legacy saved slides.

    Args:
        force: Regenerate every format even when it already exists. Use with
            care because existing YAML/Marp/HTML files are overwritten.

    Returns:
        A stats dictionary with ``migrated``, ``skipped``, and ``errors``
        counts summarising what the function did to every slide under
        ``SLIDES_DIR``.
    """
    stats = {"migrated": 0, "skipped": 0, "errors": 0}

    for meta in list_slides():
        slide_id = meta.get("id") or "<unknown>"
        try:
            if not force and _has_full_format_set(meta):
                stats["skipped"] += 1
                logger.info("Skipping already-migrated slide %s", slide_id)
                continue

            _migrate_one(meta)
            stats["migrated"] += 1
            logger.info("Migrated slide %s (%s)", slide_id, meta.get("title"))
        except Exception as exc:  # defensive: keep batch alive on unforeseen errors
            stats["errors"] += 1
            logger.error("Failed to migrate slide %s: %s", slide_id, exc)

    return stats


def _cli(argv: list[str] | None = None) -> int:
    """Command-line entry point: ``python -m src.utils.migration [chord]``."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="python -m src.utils.migration",
        description=(
            "Migration utilities for the band-deck app. The ``chord`` "
            "subcommand rewrites Unicode chord typography inside [...] "
            "spans of every ``data/songs/<song>/<song>.yaml`` to its "
            "ASCII equivalent so downstream rendering and grep work over "
            "clean text."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    slide_parser = subparsers.add_parser(
        "slides",
        help="Backfill YAML/Marp/HTML for legacy saved slides.",
    )
    slide_parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate every format even when it already exists.",
    )
    chord_parser = subparsers.add_parser(
        "chord",
        help="Normalise bracketed chord text in data/songs/**/*.yaml to ASCII.",
    )
    chord_parser.add_argument(
        "--backup",
        action="store_true",
        help="Write a .bak sibling before rewriting each file.",
    )
    chord_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report which files would change without rewriting them.",
    )
    chord_parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Specific YAML files to migrate. Defaults to data/songs/*/*.yaml.",
    )

    args = parser.parse_args(argv)
    if args.command == "slides":
        stats = migrate_existing_slides(force=args.force)
        _emit_summary("slide migration", stats)
        return 0 if stats["errors"] == 0 else 1
    if args.command == "chord":
        targets = list(args.paths) if args.paths else default_song_yaml_paths()
        if not targets:
            print(
                "chord migration: no YAML files found ("
                "expected data/songs/<song>/<song>.yaml under the current working "
                "directory; pass paths explicitly to override)"
            )
            return 1
        if args.dry_run:
            mutable = [path for path in targets if has_legacy_chord_unicode(path)]
            print(
                f"dry run: {len(mutable)}/{len(targets)} files would change "
                f"(migrated={len(mutable)} skipped={len(targets)-len(mutable)})"
            )
            for path in mutable:
                print(str(path))
            return 0
        stats = migrate_chord_yaml_files(targets, backup=args.backup)
        _emit_summary("chord migration", stats)
        return 0 if stats["errors"] == 0 else 1
    return 2


def _emit_summary(label: str, stats: dict[str, int]) -> None:
    """Print a ``migrated=N skipped=N errors=N`` line on stdout.

    Falls back to logger only if stdout writing fails (so CI capture
    buffers, etc., still get the same diagnostic).
    """
    message = (
        f"{label}: migrated={stats['migrated']} "
        f"skipped={stats['skipped']} errors={stats['errors']}"
    )
    try:
        print(message)
    except OSError:
        logger.info(message)


if __name__ == "__main__":
    raise SystemExit(_cli())
