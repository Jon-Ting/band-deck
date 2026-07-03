"""HTML compilation for saved slide decks.

Combines multiple saved slides into a single standalone HTML deck with a
clickable index slide at the front. Each song's first slide carries an HTML
anchor (``id="song-<index>"``) and the index lists each song with an anchor
link, so users can jump between songs using only standard browser navigation
(no scripts, no inline event handlers — keeps the deck safe and offline).

Selection and ordering are both encoded in the caller-provided slide_ids
list: the array position is the playback order.
"""

from __future__ import annotations

import logging
import os
from typing import Iterable

import yaml

import src.utils.slide_storage as storage_module
from src.utils.chordpro_parser import ChordPosition, ChordProLine
from src.utils.html_renderer import render_html
from src.utils.marp_generator import (
    MarpOptions,
    STYLE_PRESETS,
    _assemble_marp_document,
    _generate_section_slide,
    _generate_title_slide,
)
from src.utils.slide_storage import _slide_path, list_slides
from src.utils.yaml_models import SongSection, SongYAML


def _current_slides_dir() -> str:
    """Return the active SLIDES_DIR via the storage module so monkeypatching works."""
    return storage_module.SLIDES_DIR

logger = logging.getLogger(__name__)

COMPILED_HTML_FILENAME = "all_songs.html"
ANCHOR_ID_PREFIX = "song-"


class CompilationError(ValueError):
    """Raised when the caller request cannot be satisfied (e.g., empty list)."""


def _anchor_id(position: int) -> str:
    """Return the anchor id used to navigate from the index into a song."""
    return f"{ANCHOR_ID_PREFIX}{position}"


def _load_song_yaml(slide_id: str) -> SongYAML:
    """Read a saved YAML file back into a ``SongYAML`` dataclass tree."""
    yaml_path = _slide_path(slide_id, "yaml")
    with open(yaml_path, "r", encoding="utf-8") as yaml_file:
        raw = yaml.safe_load(yaml_file) or {}

    sections: dict[str, SongSection] = {}
    for section_name, section_payload in (raw.get("sections") or {}).items():
        lines = [
            ChordProLine(
                text=str(line_dict.get("text") or ""),
                chords=[
                    ChordPosition(
                        chord=str(chord_dict.get("chord") or ""),
                        position=int(chord_dict.get("position") or 0),
                    )
                    for chord_dict in (line_dict.get("chords") or [])
                    if isinstance(chord_dict, dict)
                ],
            )
            for line_dict in (section_payload.get("lines") or [])
            if isinstance(line_dict, dict)
        ]
        sections[section_name] = SongSection(
            name=str(section_payload.get("name") or section_name),
            type=str(section_payload.get("type") or "verse"),
            lines=lines,
            repeat=int(section_payload.get("repeat") or 1),
            notes=section_payload.get("notes"),
        )

    return SongYAML(
        title=str(raw.get("title") or "Unknown Title"),
        authors=list(raw.get("authors") or ["Unknown"]),
        license_number=raw.get("license_number") or raw.get("ccli_number"),
        copyright=raw.get("copyright"),
        original_key=raw.get("original_key"),
        target_key=str(raw.get("target_key") or "C"),
        bpm=raw.get("bpm"),
        time_signature=raw.get("time_signature"),
        capo=raw.get("capo"),
        sections=sections,
        arrangement=list(raw.get("arrangement") or []),
        practice_notes=raw.get("practice_notes"),
        source_urls=list(raw.get("source_urls") or []),
    )


def _build_index_slide(entries: Iterable[tuple[int, str]]) -> str:
    """Build a Marp slide listing each compiled song with anchor links."""
    lines = ["# Song Index", ""]
    for position, title in entries:
        lines.append(f"- [{title}](#{_anchor_id(position)})")
    return "\n".join(lines)


def _generate_combined_marp(ordered_songs: list[SongYAML]) -> str:
    """Assemble a single Marp document covering the index and every song."""
    options = MarpOptions()
    # Compiled decks want the full song map on every section slide so
    # musicians can see where they are without leaving the deck. The index
    # slide occupies the first slot and uses the ``practice`` style.
    style_preset = STYLE_PRESETS["practice"]
    entries = [(position, song.title) for position, song in enumerate(ordered_songs)]
    slides: list[str] = [_build_index_slide(entries)]

    for position, song in enumerate(ordered_songs):
        anchor_block = (
            f'<div id="{_anchor_id(position)}"></div>\n\n'
            '<span style="display:none">[anchor]</span>\n\n'
        )
        title_slide = anchor_block + _generate_title_slide(song, options, style_preset)
        slides.append(title_slide)

        for current_index, section_name in enumerate(song.arrangement):
            section = song.sections.get(section_name)
            if section is None:
                continue
            next_section = (
                song.arrangement[current_index + 1]
                if current_index + 1 < len(song.arrangement)
                else None
            )
            slides.append(
                _generate_section_slide(
                    song=song,
                    section=section,
                    current_index=current_index,
                    next_section=next_section,
                    options=options,
                    preset=style_preset,
                )
            )

    return _assemble_marp_document(slides, options, "practice")


def _resolve_output_path(output_path: str | None) -> str:
    """Return the destination path for the compiled HTML deck."""
    if output_path is not None:
        return output_path
    return os.path.join(_current_slides_dir(), COMPILED_HTML_FILENAME)


def compile_slides_html(
    slide_ids: list[str],
    *,
    output_path: str | None = None,
) -> str:
    """Combine saved slides into a single standalone HTML deck.

    Args:
        slide_ids: Ordered list of slide identifiers. The array position is
            both the playback order *and* the navigation anchor index. Slides
            whose id cannot be resolved are skipped with a warning; an empty
            input or an input where every id is invalid raises
            :class:`CompilationError`. Repeated ids collapse to a single
            entry while preserving the first appearance order.
        output_path: Destination file path. Defaults to
            ``SLIDES_DIR/all_songs.html``.

    Returns:
        The absolute path of the generated HTML deck.

    Raises:
        CompilationError: When no slides can be compiled.
        RenderError: When Marp CLI fails to render the combined document.
        OSError: When the destination file cannot be written.
    """
    if not slide_ids:
        raise CompilationError("slide_ids must contain at least one id")

    # Collapse repeats to the first occurrence so anchor ids stay unique.
    seen_ids: set[str] = set()
    ordered_unique_ids: list[str] = []
    for slide_id in slide_ids:
        if slide_id in seen_ids:
            logger.warning("Skipping duplicate slide id %s", slide_id)
            continue
        seen_ids.add(slide_id)
        ordered_unique_ids.append(slide_id)

    available = {meta["id"]: meta for meta in list_slides()}
    ordered_songs: list[SongYAML] = []
    resolved_titles: list[str] = []
    for slide_id in ordered_unique_ids:
        meta = available.get(slide_id)
        if meta is None:
            logger.warning("Skipping unknown slide id %s", slide_id)
            continue
        if "yaml" not in (meta.get("filenames") or {}):
            logger.warning(
                "Skipping slide %s because no YAML artefact is available", slide_id
            )
            continue
        ordered_songs.append(_load_song_yaml(slide_id))
        resolved_titles.append(meta.get("title") or "Untitled")

    if not ordered_songs:
        raise CompilationError("None of the supplied slide_ids resolved to a saveable song")

    combined_marp = _generate_combined_marp(ordered_songs)
    resolved_output = _resolve_output_path(output_path)
    os.makedirs(os.path.dirname(resolved_output), exist_ok=True)
    render_html(combined_marp, output_path=resolved_output)
    logger.info(
        "Compiled %d songs into %s (in order: %s)",
        len(ordered_songs),
        resolved_output,
        resolved_titles,
    )
    return resolved_output
