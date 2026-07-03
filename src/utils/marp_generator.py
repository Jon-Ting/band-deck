"""Generate Marp markdown slide decks from structured song data."""

from __future__ import annotations

import html
from dataclasses import dataclass

from src.utils.chordpro_parser import ChordProLine, pretty_print_chordpro
from src.utils.yaml_models import SongSection, SongYAML


@dataclass
class MarpOptions:
    """Display options for Marp slide generation."""

    show_song_map: bool = True
    show_metadata: bool = True
    show_practice_notes: bool = True
    font_size: str = "24px"
    aspect_ratio: str = "16:9"


def generate_marp(
    song: SongYAML,
    style: str = "practice",
    options: MarpOptions | None = None,
) -> str:
    """Generate Marp markdown from structured song data."""
    resolved_options = options or MarpOptions()
    slides = [_generate_title_slide(song, resolved_options)]

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
            )
        )

    return _assemble_marp_document(slides, resolved_options)


def format_chordpro_line(line: ChordProLine) -> str:
    """Pretty print a ChordPro line with inline chord spans."""
    return pretty_print_chordpro(line, "html")


def _assemble_marp_document(slides: list[str], options: MarpOptions) -> str:
    frontmatter = "\n".join(
        [
            "---",
            "marp: true",
            "theme: default",
            "paginate: true",
            f"size: {options.aspect_ratio}",
            "---",
            "",
            _css_template(options),
            "",
        ]
    )
    return frontmatter + "\n---\n".join(slides)


def _css_template(options: MarpOptions) -> str:
    return f"""<style>
section {{ font-family: Arial, sans-serif; color: #111827; padding: 34px 42px; }}
h1 {{ color: #1d4ed8; font-size: 44px; margin: 0 0 12px; }}
h2 {{ color: #1d4ed8; font-size: 36px; margin: 0 0 10px; }}
.meta {{ display: flex; flex-wrap: wrap; gap: 18px; font-size: 18px; font-weight: 700; border-bottom: 2px solid #d1d5db; padding-bottom: 8px; margin-bottom: 16px; }}
.layout {{ display: grid; grid-template-columns: 2.1fr 0.9fr; gap: 22px; }}
.line {{ font-family: "Courier New", monospace; font-size: {html.escape(options.font_size)}; line-height: 1.3; margin: 10px 0; }}
.chord {{ color: #c2410c; font-weight: 800; }}
.lyric {{ color: #111827; }}
.song-map {{ font-size: 18px; line-height: 1.5; }}
.current {{ background: #dbeafe; color: #1d4ed8; font-weight: 800; padding: 2px 6px; border-radius: 4px; }}
.cue-box {{ background: #eef2f7; border-left: 6px solid #64748b; padding: 12px 14px; font-size: 21px; line-height: 1.35; }}
.notes {{ margin-top: 14px; font-size: 20px; line-height: 1.35; }}
</style>"""


def _generate_title_slide(song: SongYAML, options: MarpOptions) -> str:
    parts = [f"# {_escape(song.title)}"]

    if options.show_metadata:
        parts.append(_metadata_bar(song))

    parts.append(f"**Authors:** {_escape(_authors(song))}  ")

    if song.ccli_number:
        parts.append(f"**CCLI: {_escape(song.ccli_number)}**  ")

    if options.show_song_map and song.arrangement:
        parts.append(f"**Song map:** {_render_song_map(song.arrangement)}")

    general_notes = _practice_notes(song, "general")
    if options.show_practice_notes and general_notes:
        parts.append(_cue_box(general_notes))

    if song.copyright:
        parts.append(f"<div class=\"notes\">{_escape(song.copyright)}</div>")

    return "\n\n".join(parts).strip()


def _generate_section_slide(
    song: SongYAML,
    section: SongSection,
    current_index: int,
    next_section: str | None,
    options: MarpOptions,
) -> str:
    parts = [f"## {_escape(section.name)}"]

    if options.show_metadata:
        parts.append(_metadata_bar(song))

    lines_html = "\n".join(
        f'<div class="line"><span class="lyric">{format_chordpro_line(line)}</span></div>'
        for line in section.lines
    )

    sidebar_parts = []
    if options.show_song_map:
        sidebar_parts.append(_render_song_map(song.arrangement, current_index))

    section_notes = _section_notes(song, section)
    if options.show_practice_notes and section_notes:
        sidebar_parts.append(f"Current cue: {_escape('; '.join(section_notes))}")

    sidebar_parts.append(f"Next: {_escape(next_section) if next_section else 'End'}")
    sidebar_html = "<br><br>\n".join(sidebar_parts)

    parts.append(
        "\n".join(
            [
                '<div class="layout">',
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

    return "\n\n".join(parts).strip()


def _metadata_bar(song: SongYAML) -> str:
    metadata = [
        ("Key", song.target_key),
        ("BPM", str(song.bpm) if song.bpm is not None else None),
        ("Time", song.time_signature),
        ("Capo", song.capo or "none"),
    ]
    spans = [
        f"<span>{label}: {_escape(value)}</span>"
        for label, value in metadata
        if value
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
