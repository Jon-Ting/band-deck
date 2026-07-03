"""Convert current search results into structured song YAML models."""

from __future__ import annotations

import re

from src.utils.chordpro_parser import ChordPosition, ChordProLine
from src.utils.search import get_semitone_shift, transpose_chord
from src.utils.yaml_models import SongSection, SongYAML

CHORD_TOKEN_RE = re.compile(
    r"[A-G][b#]?"
    r"(?:(?:m(?![a-z])|maj|min|dim|aug|sus[24]?|add[0-9]+|[0-9]+|b[0-9]+|#[0-9]+))*"
    r"(?:/[A-G][b#]?)?"
)


def infer_section_type(section_name: str) -> str:
    """Infer the schema-supported section type from a display section name."""
    normalized = section_name.strip().lower().rstrip(".")

    if normalized.startswith("verse"):
        return "verse"
    if normalized.startswith("pre-chorus") or normalized.startswith("chorus"):
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


def _extract_chord_positions(chord_line: str) -> list[ChordPosition]:
    """Return chord tokens from an aligned chord line with their start columns."""
    chords: list[ChordPosition] = []

    for token_match in re.finditer(r"\S+", chord_line.rstrip()):
        token = token_match.group(0)
        chord_match = CHORD_TOKEN_RE.fullmatch(token.strip("|"))
        if chord_match:
            token_offset = token.find(chord_match.group(0))
            chords.append(
                ChordPosition(
                    chord=chord_match.group(0),
                    position=token_match.start() + max(token_offset, 0),
                )
            )

    return chords


def _looks_like_chord_line(line: str) -> bool:
    """Return whether a row looks like aligned chord notation."""
    stripped_line = line.strip()
    if not stripped_line:
        return False

    tokens = re.findall(r"\S+", stripped_line)
    return bool(tokens) and all(CHORD_TOKEN_RE.fullmatch(token.strip("|")) for token in tokens)


def combine_chord_and_lyric_lines(chord_line: str, lyric_line: str) -> ChordProLine:
    """Combine aligned chord and lyric rows into positioned ChordPro data."""
    return ChordProLine(
        text=lyric_line.rstrip(),
        chords=_extract_chord_positions(chord_line),
    )


def _chord_only_line(chord_line: str) -> ChordProLine:
    """Represent an instrumental chord row against a spacing-only text row."""
    stripped_line = chord_line.rstrip()
    return ChordProLine(
        text=" " * len(stripped_line),
        chords=_extract_chord_positions(stripped_line),
    )


def parse_sections_from_content(content: str) -> dict[str, SongSection]:
    """Parse blank-line-separated current search content into song sections."""
    sections: dict[str, SongSection] = {}

    for section_block in re.split(r"\n\s*\n", content or ""):
        lines = [line.rstrip() for line in section_block.splitlines() if line.strip()]
        if not lines:
            continue

        section_name = lines[0].strip()
        body_lines = lines[1:]
        section_type = infer_section_type(section_name)
        parsed_lines: list[ChordProLine] = []

        index = 0
        while index < len(body_lines):
            current_line = body_lines[index]
            next_line = body_lines[index + 1] if index + 1 < len(body_lines) else ""

            if _looks_like_chord_line(current_line) and next_line and not _looks_like_chord_line(next_line):
                parsed_lines.append(combine_chord_and_lyric_lines(current_line, next_line))
                index += 2
            elif _looks_like_chord_line(current_line):
                parsed_lines.append(_chord_only_line(current_line))
                index += 1
            else:
                parsed_lines.append(ChordProLine(text=current_line.rstrip(), chords=[]))
                index += 1

        sections[section_name] = SongSection(
            name=section_name,
            type=section_type,
            lines=parsed_lines,
        )

    return sections


def transpose_chordpro_lines(
    lines: list[ChordProLine],
    from_key: str | None,
    to_key: str | None,
) -> list[ChordProLine]:
    """Transpose chords in parsed lines while preserving text and positions."""
    if not from_key or not to_key or from_key == to_key:
        return lines

    semitones = get_semitone_shift(from_key, to_key)
    if semitones == 0:
        return lines

    use_flats = "b" in to_key
    return [
        ChordProLine(
            text=line.text,
            chords=[
                ChordPosition(
                    chord=transpose_chord(chord_pos.chord, semitones, use_flats),
                    position=chord_pos.position,
                )
                for chord_pos in line.chords
            ],
        )
        for line in lines
    ]


def convert_to_yaml(song_data: dict, target_key: str | None = None) -> SongYAML:
    """Convert a current search result dictionary into structured YAML data."""
    sections = parse_sections_from_content(song_data.get("content", ""))

    original_key = song_data.get("original_key")
    content_key = song_data.get("key") or song_data.get("target_key") or original_key
    resolved_target_key = target_key or song_data.get("key") or original_key or "C"

    if content_key != resolved_target_key:
        for section in sections.values():
            section.lines = transpose_chordpro_lines(
                section.lines,
                from_key=content_key,
                to_key=resolved_target_key,
            )

    title = (song_data.get("search_name") or song_data.get("title") or "Unknown Title").strip()
    artist = (song_data.get("artist") or "").strip()
    source_url = (song_data.get("source_url") or "").strip()

    return SongYAML(
        title=title,
        authors=[artist] if artist else ["Unknown"],
        original_key=original_key,
        target_key=resolved_target_key,
        sections=sections,
        arrangement=list(sections),
        source_urls=[source_url] if source_url else [],
    )
