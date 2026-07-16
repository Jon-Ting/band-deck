"""Generate Marp markdown slide decks from structured song data."""

import html
from dataclasses import dataclass

from src.utils.chordpro_parser import ChordProLine
from src.utils.yaml_models import SongSection, SongYAML


@dataclass
class MarpOptions:
    """Display options for Marp slide generation."""

    show_song_map: bool = True
    show_metadata: bool = True
    show_practice_notes: bool = True
    font_size: str = "22px"
    aspect_ratio: str = "16:9"


# Default toggle sets per style. Each style is a
# composition of the three display toggles plus per-style layout hints
# (font_size, sidebar ratio, song-map presence on title slide).
#
# The dict values are intentionally ``MappingProxyType``-style immutable at
# the application layer: callers go through :func:`_resolved_preset` which
# always returns a shallow ``dict`` copy so a caller mutating the result
# cannot corrupt shared state across slides / render calls.
STYLE_PRESETS: dict[str, dict[str, object]] = {
    # Practice: song map + metadata + practice notes; richer sidebar.
    "practice": {
        "show_song_map": True,
        "show_metadata": True,
        "show_practice_notes": True,
        "font_size": "22px",
        "sidebar_ratio": "0.9fr",
        "song_map_on_section_slides": True,
        "show_general_cue_box": True,
        "show_copyright": True,
    },
    # Performance: emphasize lyrics, minimize metadata.
    "performance": {
        "show_song_map": True,
        "show_metadata": False,
        "show_practice_notes": False,
        "font_size": "28px",
        "sidebar_ratio": "0.6fr",
        "song_map_on_section_slides": False,
        "show_general_cue_box": False,
        "show_copyright": True,
    },
    # Simple: minimal formatting, no metadata bar, no song map.
    "simple": {
        "show_song_map": False,
        "show_metadata": False,
        "show_practice_notes": False,
        "font_size": "30px",
        "sidebar_ratio": "0fr",
        "song_map_on_section_slides": False,
        "show_general_cue_box": False,
        "show_copyright": True,
    },
}


def _resolve_options(style: str, options: MarpOptions | None) -> MarpOptions:
    """Combine a style preset with any explicit MarpOptions overrides.

    The style preset supplies a baseline configuration. Explicit ``options`` field values that differ
    from the dataclass defaults (``MarpOptions()``) win so the
    SongEditor can override per song/band. Passing options that happen to
    match a default is treated the same as "no override": callers
    wanting to be explicit should hit the field directly via
    ``MarpOptions(show_metadata=False, ...)``.
    """
    preset = dict(_resolved_preset(style))  # copy — never mutate the global preset
    base = MarpOptions(
        show_song_map=bool(preset["show_song_map"]),
        show_metadata=bool(preset["show_metadata"]),
        show_practice_notes=bool(preset["show_practice_notes"]),
        font_size=str(preset["font_size"]),
    )
    if options is None:
        return base
    baseline = MarpOptions()
    for field in base.__dataclass_fields__:  # type: ignore[attr-defined]
        if getattr(options, field) != getattr(baseline, field):
            setattr(base, field, getattr(options, field))
    return base


def _resolved_preset(style: str) -> dict[str, object]:
    """Return a fresh shallow copy of the style preset so callers can
    safely read (and mutate if they need to) without corrupting the
    module-global ``STYLE_PRESETS`` for other render calls.
    """
    return dict(STYLE_PRESETS.get(style, STYLE_PRESETS["practice"]))


def generate_marp(
    song: SongYAML,
    style: str = "practice",
    options: MarpOptions | None = None,
) -> str:
    """Generate Marp markdown from structured song data.

    Honors the slide ``style`` preset and any
    explicit ``MarpOptions`` overrides supplied by the caller.
    """
    resolved_options = _resolve_options(style, options)
    preset = _resolved_preset(style)
    slides = [_generate_title_slide(song, resolved_options, preset)]

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
                options=resolved_options,
                preset=preset,
            )
        )

    return _assemble_marp_document(slides, resolved_options, style)


def format_chordpro_line(line: ChordProLine) -> str:
    """Render a ChordPro line as aligned chord and lyric rows."""
    rows: list[str] = []

    if line.chords:
        rows.append(
            '<div class="chord-row">'
            f'<span class="chord">{_escape(_format_chord_row(line))}</span>'
            "</div>"
        )

    if line.text or not line.chords:
        rows.append(
            '<div class="lyric-row">'
            f'<span class="lyric">{_escape(line.text)}</span>'
            "</div>"
        )

    return "".join(rows)


def _format_chord_row(line: ChordProLine) -> str:
    """Build a monospace chord row from character positions."""
    chord_parts: list[str] = []
    last_pos = 0

    for chord_pos in sorted(line.chords, key=lambda c: c.position):
        chord_parts.append(" " * max(chord_pos.position - last_pos, 0))
        chord_parts.append(chord_pos.chord)
        last_pos = chord_pos.position + len(chord_pos.chord)

    return "".join(chord_parts)


def _assemble_marp_document(slides: list[str], options: MarpOptions, style: str) -> str:
    sidebar_ratio = str(_resolved_preset(style).get("sidebar_ratio", "0.9fr"))
    frontmatter = "\n".join(
        [
            "---",
            "marp: true",
            "theme: default",
            "paginate: true",
            f"size: {options.aspect_ratio}",
            "---",
            "",
            _css_template(options, sidebar_ratio),
            "",
        ]
    )
    return frontmatter + "\n---\n".join(slides)


def _css_template(options: MarpOptions, sidebar_ratio: str) -> str:
    font_size_raw = str(options.font_size) if options.font_size is not None else "24"
    font_size_css = html.escape(font_size_raw, quote=False) or "24px"

    return f"""<style>
/* Override Marp's default theme ``body {{ background: #000; }}``. Our CSS is
appended after Marp's in document order, so this wins by cascade and keeps
the embedded preview iframe on a light surface even where slide SVGs don't
fully cover the viewport. */
body {{ background: #ffffff; color: #111827; }}
section {{ font-family: Arial, sans-serif; color: #111827; padding: 34px 42px; }}
h1 {{ color: #1d4ed8; font-size: 44px; margin: 0 0 12px; }}
h2 {{ color: #1d4ed8; font-size: 36px; margin: 0 0 10px; }}
.meta {{ display: flex; flex-wrap: wrap; gap: 18px; font-size: 18px; font-weight: 700; border-bottom: 2px solid #d1d5db; padding-bottom: 8px; margin-bottom: 16px; }}
.layout {{ display: grid; grid-template-columns: 2.1fr {sidebar_ratio}; gap: 22px; }}
.layout--solo {{ display: block; }}
.line {{ font-family: "Courier New", monospace; font-size: {font_size_css}; line-height: 1.25; margin: 10px 0; }}
.chord-row, .lyric-row {{ white-space: pre; }}
.chord-row {{ min-height: 1em; line-height: 1; }}
.lyric-row {{ line-height: 1.25; }}
.chord {{ color: #c2410c; font-weight: 800; }}
.lyric {{ color: #111827; }}
.song-map {{ font-size: 18px; line-height: 1.5; }}
.current {{ background: #dbeafe; color: #1d4ed8; font-weight: 800; padding: 2px 6px; border-radius: 4px; }}
.cue-box {{ background: #eef2ff; border-left: 6px solid #6366f1; padding: 12px 14px; font-size: 21px; line-height: 1.35; }}
.notes {{ margin-top: 14px; font-size: 20px; line-height: 1.35; }}
.navigation-strip {{ display: flex; flex-wrap: wrap; gap: 8px; font-size: 16px; background: #f1f5f9; padding: 8px 12px; border-radius: 6px; margin-bottom: 12px; }}
.navigation-strip .current {{ background: #1d4ed8; color: #ffffff; }}
</style>"""


def _generate_title_slide(
    song: SongYAML, options: MarpOptions, preset: dict[str, object]
) -> str:
    parts = [f"# {_escape(song.title)}"]

    if options.show_metadata:
        parts.append(_metadata_bar(song))

    parts.append(f"**Authors:** {_escape(_authors(song))}  ")

    if song.license_number:
        parts.append(f"**License: {_escape(song.license_number)}**  ")

    if options.show_song_map and song.arrangement:
        parts.append(f"**Song map:** {_render_song_map(song.arrangement)}")

    if options.show_practice_notes and preset.get("show_general_cue_box", True):
        general_notes = _practice_notes(song, "general")
        if general_notes:
            parts.append(_cue_box(general_notes))

    if preset.get("show_copyright", True) and song.copyright:
        parts.append(f'<div class="notes">{_escape(song.copyright)}</div>')

    return "\n\n".join(parts).strip()


def _generate_section_slide(
    song: SongYAML,
    section: SongSection,
    current_index: int,
    next_section: str | None,
    options: MarpOptions,
    preset: dict[str, object],
) -> str:
    parts = [f"## {_escape(section.name)}"]

    # Practice-mode navigation strip showing the full song map. This
    # is visible on all slides in practice style;
    # other styles either render it in the sidebar or hide it entirely
    # depending on their preset. The user's MarpOptions.show_song_map
    # toggle always wins so an explicit request to hide the map is
    # honoured even when the style preset would otherwise show it.
    show_strip = options.show_song_map and bool(
        preset.get("song_map_on_section_slides", True)
    )
    if show_strip and song.arrangement:
        parts.append(_navigation_strip(song.arrangement, current_index))

    if options.show_metadata:
        parts.append(_metadata_bar(song))

    lines_html = "\n".join(
        f'<div class="line">{format_chordpro_line(line)}</div>'
        for line in section.lines
    )

    sidebar_parts: list[str] = []

    if options.show_song_map:
        sidebar_parts.append(_render_song_map(song.arrangement, current_index))

    section_notes = _section_notes(song, section)
    if options.show_practice_notes and section_notes:
        sidebar_parts.append(f"Current cue: {_escape('; '.join(section_notes))}")

    sidebar_parts.append(f"Next: {_escape(next_section) if next_section else 'End'}")
    sidebar_ratio = str(preset.get("sidebar_ratio", "0.9fr"))
    has_sidebar = sidebar_ratio != "0fr"
    layout_class = "layout" if has_sidebar else "layout layout--solo"
    if has_sidebar:
        sidebar_html = "<br><br>\n".join(sidebar_parts)
        parts.append(
            "\n".join(
                [
                    f'<div class="{layout_class}">',
                    "<div>",
                    lines_html,
                    "</div>",
                    '<div class="song-map">',
                    sidebar_html,
                    "</div>",
                    "</div>",
                ]
            )
        )
    else:
        parts.append(
            "\n".join(
                [
                    f'<div class="{layout_class}">',
                    lines_html,
                    "</div>",
                ]
            )
        )

    return "\n\n".join(parts).strip()


def _metadata_bar(song: SongYAML) -> str:
    metadata = [
        ("Key", song.target_key),
        ("BPM", str(song.bpm) if song.bpm is not None else None),
        ("Time", song.time_signature),
        ("Capo", song.capo or "none"),
    ]
    spans = [
        f"<span>{label}: {_escape(value)}</span>" for label, value in metadata if value
    ]
    return f'<div class="meta">{"".join(spans)}</div>'


def _render_song_map(arrangement: list[str], current_index: int | None = None) -> str:
    rendered_sections = []

    for index, section_name in enumerate(arrangement):
        escaped_name = _escape(section_name)
        if current_index == index:
            rendered_sections.append(f'<span class="current">{escaped_name}</span>')
        else:
            rendered_sections.append(escaped_name)

    return " &rarr; ".join(rendered_sections)


def _navigation_strip(arrangement: list[str], current_index: int) -> str:
    """Compact song map strip placed at the top of each section slide."""
    items = []
    for index, section_name in enumerate(arrangement):
        escaped_name = _escape(section_name)
        if index == current_index:
            items.append(f'<span class="current">{escaped_name}</span>')
        else:
            items.append(escaped_name)
    return f'<div class="navigation-strip">{"".join(items)}</div>'


def _section_notes(song: SongYAML, section: SongSection) -> list[str]:
    notes: list[str] = []

    if section.notes:
        notes.extend(section.notes)

    if song.practice_notes:
        notes.extend(song.practice_notes.get(section.name, []))

    return notes


def _practice_notes(song: SongYAML, key: str) -> list[str]:
    if not song.practice_notes:
        return []

    return song.practice_notes.get(key, [])


def _cue_box(notes: list[str]) -> str:
    escaped_notes = "<br>".join(_escape(note) for note in notes)
    return f'<div class="cue-box">{escaped_notes}</div>'


def _authors(song: SongYAML) -> str:
    return ", ".join(song.authors) if song.authors else "Unknown"


def _escape(value: str) -> str:
    return html.escape(value, quote=True)
