"""Preview generation helpers for HTML slide decks."""

from __future__ import annotations

import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any

from src.utils.chordpro_parser import ChordPosition, ChordProLine, parse_chordpro
from src.utils.html_renderer import render_html
from src.utils.marp_generator import MarpOptions, generate_marp
from src.utils.yaml_models import SongSection, SongYAML


def generate_preview(payload: dict[str, Any]) -> dict[str, Any]:
    """Generate rendered HTML preview content from request JSON."""
    if not isinstance(payload, dict):
        raise ValueError("JSON body is required")

    song = _song_from_payload(payload)
    return _render_song_preview(song, payload)


def generate_regeneration(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate edited song YAML and regenerate rendered HTML preview content."""
    if not isinstance(payload, dict):
        raise ValueError("JSON body is required")

    song = _song_from_payload(payload)
    validation = _validate_song_for_regeneration(song)
    if not validation["valid"]:
        raise SongValidationError(validation)

    result = _render_song_preview(song, payload)
    result["validation"] = validation
    return result


class SongValidationError(ValueError):
    """Raised when edited song YAML is structurally invalid."""

    def __init__(self, validation: dict[str, Any]):
        super().__init__("Invalid song YAML")
        self.validation = validation


def _render_song_preview(song: SongYAML, payload: dict[str, Any]) -> dict[str, Any]:
    options = _options_from_payload(payload.get("options"))
    style = str(payload.get("style") or "practice")
    warnings = _preview_warnings(song)

    marp_markdown = generate_marp(song, style=style, options=options)

    with tempfile.TemporaryDirectory(prefix="band-deck-preview-") as tmpdir:
        html_path = Path(tmpdir) / "preview.html"
        rendered_path = render_html(marp_markdown, output_path=html_path)
        html_content = Path(rendered_path).read_text(encoding="utf-8")

    return {
        "html_content": html_content,
        "marp_markdown": marp_markdown,
        "warnings": warnings,
        "slide_count": _slide_count(song),
    }


def _validate_song_for_regeneration(song: SongYAML) -> dict[str, Any]:
    from src.utils.yaml_api import validate_song_yaml_dict

    return validate_song_yaml_dict(asdict(song))


def _song_from_payload(payload: dict[str, Any]) -> SongYAML:
    song_payload = payload.get("song")

    if song_payload is None and "title" in payload:
        song_payload = payload

    if not isinstance(song_payload, dict):
        raise ValueError("Song data is required")

    merged_song = dict(song_payload)

    for key in ("sections", "arrangement", "practice_notes"):
        if key not in merged_song and key in payload:
            merged_song[key] = payload[key]

    sections = _sections_from_payload(merged_song.get("sections"))
    arrangement = _arrangement_from_payload(merged_song.get("arrangement"), sections)

    title = str(merged_song.get("title") or "").strip()
    if not title:
        raise ValueError("Song title is required")

    authors = _string_list(merged_song.get("authors")) or ["Unknown"]

    return SongYAML(
        title=title,
        authors=authors,
        ccli_number=_optional_string(merged_song.get("ccli_number")),
        copyright=_optional_string(merged_song.get("copyright")),
        original_key=_optional_string(merged_song.get("original_key")),
        target_key=str(merged_song.get("target_key") or "C"),
        bpm=merged_song.get("bpm"),
        time_signature=_optional_string(merged_song.get("time_signature")),
        capo=_optional_string(merged_song.get("capo")),
        sections=sections,
        arrangement=arrangement,
        practice_notes=_practice_notes_from_payload(merged_song.get("practice_notes")),
        source_urls=_string_list(merged_song.get("source_urls")),
    )


def _sections_from_payload(sections_payload: Any) -> dict[str, SongSection]:
    if not isinstance(sections_payload, dict) or not sections_payload:
        raise ValueError("Song sections are required")

    sections: dict[str, SongSection] = {}
    for section_key, section_payload in sections_payload.items():
        if not isinstance(section_payload, dict):
            raise ValueError(f"Section '{section_key}' must be an object")

        name = str(section_payload.get("name") or section_payload.get("label") or section_key)
        section_type = str(section_payload.get("type") or _infer_section_type(name))
        lines_payload = section_payload.get("lines") or []
        lines = [_line_from_payload(line_payload) for line_payload in lines_payload]

        sections[name] = SongSection(
            name=name,
            type=section_type,
            lines=lines,
            repeat=int(section_payload.get("repeat") or 1),
            notes=_string_list(section_payload.get("notes")) or None,
        )

    return sections


def _line_from_payload(line_payload: Any) -> ChordProLine:
    if isinstance(line_payload, str):
        return parse_chordpro(line_payload)

    if not isinstance(line_payload, dict):
        raise ValueError("Section lines must be objects or ChordPro strings")

    chordpro_line = line_payload.get("chordpro") or line_payload.get("raw")
    if chordpro_line is not None:
        return parse_chordpro(str(chordpro_line))

    text = str(line_payload.get("text") or "")
    chords = [
        ChordPosition(
            chord=str(chord_payload.get("chord") or ""),
            position=int(chord_payload.get("position") or 0),
        )
        for chord_payload in line_payload.get("chords") or []
        if isinstance(chord_payload, dict)
    ]

    return ChordProLine(text=text, chords=chords)


def _arrangement_from_payload(
    arrangement_payload: Any,
    sections: dict[str, SongSection],
) -> list[str]:
    if isinstance(arrangement_payload, dict):
        arrangement_payload = arrangement_payload.get("sequence")

    if arrangement_payload is None:
        return list(sections)

    if not isinstance(arrangement_payload, list):
        raise ValueError("Song arrangement must be a list")

    arrangement = [str(section_name) for section_name in arrangement_payload if section_name]
    if not arrangement:
        raise ValueError("Song arrangement is required")

    return arrangement


def _options_from_payload(options_payload: Any) -> MarpOptions | None:
    if options_payload is None:
        return None

    if not isinstance(options_payload, dict):
        raise ValueError("Preview options must be an object")

    allowed_keys = {
        "show_song_map",
        "show_metadata",
        "show_practice_notes",
        "font_size",
        "aspect_ratio",
    }
    return MarpOptions(
        **{key: value for key, value in options_payload.items() if key in allowed_keys}
    )


def _preview_warnings(song: SongYAML) -> list[str]:
    missing_sections = [
        section_name for section_name in song.arrangement if section_name not in song.sections
    ]
    return [
        f"Arrangement references missing section: {section_name}"
        for section_name in missing_sections
    ]


def _slide_count(song: SongYAML) -> int:
    return 1 + sum(1 for section_name in song.arrangement if section_name in song.sections)


def _practice_notes_from_payload(practice_notes_payload: Any) -> dict[str, list[str]] | None:
    if not isinstance(practice_notes_payload, dict):
        return None

    return {
        str(key): _string_list(value)
        for key, value in practice_notes_payload.items()
        if _string_list(value)
    }


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []

    if isinstance(value, list):
        return [str(item) for item in value if item is not None]

    if isinstance(value, str) and value.strip():
        return [value.strip()]

    return []


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None

    resolved = str(value).strip()
    return resolved or None


def _infer_section_type(section_name: str) -> str:
    normalized = section_name.strip().lower().rstrip(".")

    if normalized.startswith("chorus") or normalized.startswith("pre-chorus"):
        return "chorus"
    if normalized.startswith("bridge"):
        return "bridge"
    if normalized.startswith("intro"):
        return "intro"
    if normalized.startswith("outro"):
        return "outro"
    if normalized.startswith("interlude"):
        return "interlude"
    if normalized.startswith(("instrumental", "tag")):
        return "instrumental"

    return "verse"
