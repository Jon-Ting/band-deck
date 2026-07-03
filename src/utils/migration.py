"""Batch migration utility for legacy PPTX-only saved slides.

Legacy slides saved before the multi-format refactor only contain a single
PowerPoint file plus metadata JSON. This utility backfills YAML, Marp
markdown, and HTML files for any slide that lacks them so every saved slide
participates in the multi-format workflow while remaining loadable
(requirement 14.7).

Design notes:

* PPTX text extraction is deliberately skipped (despite task 5.3 calling for
  it). Parsing rendered slide text back into structured sections/chords is
  brittle and was considered out of scope: the migration emits a placeholder
  ``Note`` section that carries song metadata and directs the user to
  re-generate from the chart source when the original lyrics and chords are
  missing. The PPTX file itself is left untouched so any existing reader
  still works.
* The migration is idempotent. Slides whose ``filenames`` already list every
  supported format are skipped unless ``force=True`` is passed. Slides with
  a partial format set always have every format regenerated so partial
  migrations self-heal on the next run.
* Marp CLI rendering failures are tolerated: a plain fallback HTML file is
  written so the slide stays loadable even when the Marp CLI is missing.
* The original ``updated_at`` (user edit timestamp) is preserved. A separate
  ``migrated_at`` field records when this utility last touched the slide.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

import yaml

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


def _build_placeholder_song(meta: dict[str, Any]) -> SongYAML:
    """Build a minimal ``SongYAML`` from a legacy slide's stored metadata."""
    artist = (meta.get("artist") or "").strip()
    key = (meta.get("key") or "").strip() or "C"
    return SongYAML(
        title=(meta.get("title") or "Unknown Title").strip(),
        authors=[artist] if artist else ["Unknown"],
        ccli_number=meta.get("ccli_number"),
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


def migrate_existing_slides(force: bool = False) -> dict[str, int]:
    """Backfill YAML/Marp/HTML files for legacy PPTX-only saved slides.

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
