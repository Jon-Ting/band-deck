"""Reusable helpers for the portable band-deck skill scripts."""

from __future__ import annotations

import html
import logging
import re
from collections import Counter
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError


logger = logging.getLogger(__name__)

CHORD_TOKEN_RE = re.compile(r"\[([A-G](?:b|#)?[^\]\s]*)\]")


def load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML mapping from ``path``."""
    with path.open("r", encoding="utf-8") as yaml_file:
        data = yaml.safe_load(yaml_file) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return data


def write_text(path: Path, content: str) -> None:
    """Write UTF-8 text, creating parent directories when needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def schema_errors(
    deck: dict[str, Any], schema: dict[str, Any]
) -> list[ValidationError]:
    """Return sorted JSON Schema validation errors."""
    validator = Draft202012Validator(schema)
    return sorted(validator.iter_errors(deck), key=lambda error: list(error.path))


def format_error_path(error: ValidationError) -> str:
    """Return a compact dotted path for a jsonschema error."""
    parts = [str(part) for part in error.absolute_path]
    return ".".join(parts) if parts else "<root>"


def semantic_errors(deck: dict[str, Any]) -> list[str]:
    """Return cross-field errors that JSON Schema cannot express cleanly."""
    require_canonical_deck_shape(deck)
    sections = get_sections(deck)
    section_names = set(sections)
    errors: list[str] = []

    for index, entry in enumerate(get_arrangement_sequence(deck), start=1):
        section_name = arrangement_section_name(entry)
        if section_name and section_name not in section_names and not entry.get("cue"):
            errors.append(
                f"arrangement.sequence[{index}] references missing section "
                f"{section_name!r}"
            )

    return errors


def require_canonical_deck_shape(deck: dict[str, Any]) -> None:
    """Reject legacy top-level shapes and require the canonical deck contract."""
    request = deck.get("request")
    metadata = deck.get("metadata")
    sources = deck.get("sources")
    normalised = deck.get("normalised_chordpro")
    arrangement = deck.get("arrangement")

    if not isinstance(request, dict):
        raise ValueError(
            "Deck must use the canonical deck shape with a top-level 'request' mapping."
        )
    if not isinstance(metadata, dict):
        raise ValueError(
            "Deck must use the canonical deck shape with a top-level 'metadata' mapping."
        )
    if not isinstance(sources, dict):
        raise ValueError(
            "Deck must use the canonical deck shape with a top-level 'sources' mapping."
        )
    if not isinstance(normalised, dict) or not isinstance(
        normalised.get("sections"), dict
    ):
        raise ValueError(
            "Deck must use the canonical deck shape with "
            "'normalised_chordpro.sections'."
        )
    if not isinstance(arrangement, dict) or not isinstance(
        arrangement.get("sequence"), list
    ):
        raise ValueError(
            "Deck must use the canonical deck shape with 'arrangement.sequence'."
        )


def get_metadata(deck: dict[str, Any]) -> dict[str, Any]:
    """Return canonical metadata."""
    metadata = deck.get("metadata")
    if not isinstance(metadata, dict):
        raise ValueError("Deck metadata must be a mapping.")
    return metadata


def get_sections(deck: dict[str, Any]) -> dict[str, Any]:
    """Return the section map from canonical deck YAML."""
    normalised = deck.get("normalised_chordpro")
    if isinstance(normalised, dict) and isinstance(normalised.get("sections"), dict):
        return normalised["sections"]

    return {}


def get_arrangement_sequence(deck: dict[str, Any]) -> list[dict[str, Any]]:
    """Return canonical arrangement entries in normalised dict form."""
    arrangement = deck.get("arrangement") or {}
    raw_sequence: Any = (
        arrangement.get("sequence", []) if isinstance(arrangement, dict) else []
    )

    sequence: list[dict[str, Any]] = []
    for item in raw_sequence:
        if isinstance(item, str):
            sequence.append({"section": item})
        elif isinstance(item, dict):
            section = str(item.get("section") or item.get("name") or "").strip()
            entry = dict(item)
            if section:
                entry["section"] = section
            sequence.append(entry)
    return sequence


def arrangement_section_name(entry: dict[str, Any]) -> str:
    """Return the section name for an arrangement entry."""
    return str(entry.get("section") or "").strip()


def arrangement_label(entry: dict[str, Any]) -> str:
    """Return the display label for an arrangement entry."""
    return str(entry.get("label") or arrangement_section_name(entry)).strip()


def section_display_title(section_name: str, section: dict[str, Any]) -> str:
    """Return the human-facing title for a section."""
    return str(
        section.get("display_title")
        or section.get("label")
        or section_name.replace("Turn", " / Turnaround")
    ).strip()


def list_text(value: Any) -> list[str]:
    """Coerce string/list/null fields to a list of strings."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def metadata_value(
    metadata: dict[str, Any], *keys: str, default: str = "unknown"
) -> str:
    """Return the first non-empty metadata value as text."""
    for key in keys:
        value = metadata.get(key)
        if value not in (None, ""):
            if isinstance(value, list):
                return ", ".join(str(item) for item in value)
            return str(value)
    return default


def chordpro_text(line: Any) -> str:
    """Extract a ChordPro line from canonical line data."""
    if isinstance(line, str):
        return line
    if isinstance(line, dict):
        value = line.get("chordpro")
        if isinstance(value, str):
            return value
    return ""


def render_chordpro_line(line: Any) -> str:
    """Render one ChordPro line with chords above the exact lyric text."""
    source = chordpro_text(line)
    if not source:
        return ""

    chord_cells: list[tuple[int, str]] = []
    lyric_parts: list[str] = []
    index = 0
    lyric_column = 0
    for match in CHORD_TOKEN_RE.finditer(source):
        before = source[index : match.start()]
        lyric_parts.append(before)
        lyric_column += len(before)
        chord_cells.append((lyric_column, match.group(1)))
        index = match.end()

    lyric_parts.append(source[index:])
    lyric = "".join(lyric_parts)
    if not chord_cells:
        return f'<div class="lyric-line">{html.escape(lyric)}</div>'

    chord_line = [" "] * max(len(lyric), 1)
    for column, chord in chord_cells:
        if column >= len(chord_line):
            chord_line.extend(" " for _ in range(column - len(chord_line) + 1))
        for offset, character in enumerate(chord):
            position = column + offset
            if position >= len(chord_line):
                chord_line.append(" ")
            chord_line[position] = character

    return (
        '<div class="line-pair">'
        f'<div class="chord-line">{html.escape("".join(chord_line).rstrip())}</div>'
        f'<div class="lyric-line">{html.escape(lyric)}</div>'
        "</div>"
    )


def section_abbreviation(section_name: str) -> str:
    """Return a compact song-map label."""
    lower = section_name.lower()
    replacements = {
        "intro": "Intro",
        "verse": "V",
        "pre-chorus": "PC",
        "pre chorus": "PC",
        "chorus": "C",
        "bridge": "B",
        "tag": "Tag",
        "ending": "End",
        "instrumental": "Inst",
    }
    for prefix, abbreviation in replacements.items():
        if lower.startswith(prefix):
            suffix = section_name[len(prefix) :].strip()
            return f"{abbreviation} {suffix}".strip()
    return section_name


def song_map(sequence: list[dict[str, Any]], current_index: int | None = None) -> str:
    """Return an HTML song map with the current item highlighted."""
    labels: list[str] = []
    for index, entry in enumerate(sequence):
        label = section_abbreviation(arrangement_label(entry))
        escaped = html.escape(label)
        if current_index is not None and index == current_index:
            escaped = f'<span class="current">{escaped}</span>'
        labels.append(escaped)
    return " · ".join(labels)


def repeated_labels(sequence: list[dict[str, Any]]) -> dict[int, str]:
    """Return per-entry repeat labels for repeated section names."""
    counts = Counter(arrangement_section_name(entry) for entry in sequence)
    seen: Counter[str] = Counter()
    labels: dict[int, str] = {}
    for index, entry in enumerate(sequence):
        section_name = arrangement_section_name(entry)
        label = arrangement_label(entry)
        seen[section_name] += 1
        repeat = int(entry.get("repeat") or 1)
        if entry.get("label"):
            labels[index] = label
        elif repeat > 1:
            labels[index] = f"{label} x{repeat}"
        elif counts[section_name] > 1:
            labels[index] = f"{label} {seen[section_name]} of {counts[section_name]}"
        else:
            labels[index] = label
    return labels


def get_render_options(deck: dict[str, Any]) -> dict[str, Any]:
    """Return render options from top-level or deck-scoped config."""
    options: dict[str, Any] = {}
    deck_config = deck.get("deck")
    candidates = [deck.get("render")]
    if isinstance(deck_config, dict):
        candidates.append(deck_config.get("render"))
    for candidate in candidates:
        if isinstance(candidate, dict):
            options.update(candidate)
    return options


SLIDE_RENDER_KEYS = {
    "max_line_pairs_per_slide",
    "font_size_px",
    "chart_font_px",
    "lyric_font_px",
    "chord_font_px",
    "bar_font_px",
}


def get_slide_render_options(
    base_options: dict[str, Any], entry: dict[str, Any], section: Any
) -> dict[str, Any]:
    """Return render options for one arrangement entry/slide group."""
    options = dict(base_options)

    if isinstance(section, dict) and isinstance(section.get("render"), dict):
        options.update(section["render"])

    for key in SLIDE_RENDER_KEYS:
        if key in entry:
            options[key] = entry[key]

    entry_render = entry.get("render")
    if isinstance(entry_render, dict):
        options.update(entry_render)

    return options


def positive_int(value: Any, default: int) -> int:
    """Return a positive integer option value."""
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def positive_int_or_none(value: Any) -> int | None:
    """Return a positive integer option value, or None when absent/invalid."""
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def chart_style_attribute(render_options: dict[str, Any]) -> str:
    """Return inline CSS variables for chart font sizing."""
    base_font = positive_int_or_none(
        render_options.get("font_size_px") or render_options.get("chart_font_px")
    )
    style_values = {
        "--chart-font-size": base_font,
        "--lyric-font-size": positive_int_or_none(render_options.get("lyric_font_px")),
        "--chord-font-size": positive_int_or_none(render_options.get("chord_font_px")),
        "--bar-font-size": positive_int_or_none(render_options.get("bar_font_px")),
    }
    declarations = [
        f"{name}: {value}px;"
        for name, value in style_values.items()
        if value is not None
    ]
    return f' style="{" ".join(declarations)}"' if declarations else ""


def default_marp_style() -> str:
    """Return the default Marp CSS used by the portable generator."""
    return """
<style>
section {
  font-family: Arial, Helvetica, sans-serif;
  color: #111827;
  padding: 34px 42px;
}
h1, h2 {
  color: #1d4ed8;
  margin-top: 0;
}
.meta {
  display: flex;
  flex-wrap: wrap;
  gap: 18px;
  font-size: 18px;
  font-weight: 700;
  border-bottom: 2px solid #d1d5db;
  padding-bottom: 8px;
  margin-bottom: 16px;
}
.layout {
  display: grid;
  grid-template-columns: 2.1fr 0.9fr;
  gap: 22px;
}
.line {
  font-family: "Courier New", monospace;
  margin: 10px 0;
}
.chart-lines {
  --chart-font-size: 30px;
  --lyric-font-size: var(--chart-font-size);
  --chord-font-size: var(--chart-font-size);
  --bar-font-size: var(--chart-font-size);
}
.line-pair {
  font-family: "Courier New", monospace;
  white-space: pre;
  margin: 10px 0 18px;
}
.chord-line {
  color: #c2410c;
  font-size: var(--chord-font-size);
  font-weight: 800;
  line-height: 1.05;
}
.lyric-line {
  color: #111827;
  font-size: var(--lyric-font-size);
  line-height: 1.1;
}
.bar-line {
  font-family: "Courier New", monospace;
  color: #111827;
  font-size: var(--bar-font-size);
  font-weight: 800;
  line-height: 1.35;
  margin: 10px 0;
}
.chord {
  color: #c2410c;
  font-weight: 800;
}
.song-map {
  font-size: 21px;
  line-height: 1.45;
}
.current {
  background: #dbeafe;
  color: #1d4ed8;
  font-weight: 800;
  padding: 2px 6px;
  border-radius: 4px;
}
.cue-box {
  background: #eef2f7;
  border-left: 6px solid #64748b;
  padding: 12px 14px;
  font-size: 21px;
  line-height: 1.35;
}
.warning {
  background: #fee2e2;
  border-left-color: #dc2626;
  color: #991b1b;
  font-weight: 800;
}
.small {
  font-size: 18px;
}
.context-label {
  color: #475569;
  font-size: 16px;
  font-weight: 800;
  letter-spacing: 0;
  text-transform: uppercase;
}
.context-value {
  font-size: 24px;
  font-weight: 800;
  margin: 0 0 16px;
}
</style>
""".strip()


def generate_practice_marp(deck: dict[str, Any]) -> str:
    """Generate a practical Marp rehearsal deck from canonical YAML."""
    require_canonical_deck_shape(deck)
    metadata = get_metadata(deck)
    sequence = get_arrangement_sequence(deck)
    sections = get_sections(deck)
    repeat_labels = repeated_labels(sequence)
    render_options = get_render_options(deck)
    mode = str(render_options.get("mode") or "practice")
    paginate = "true" if render_options.get("show_pagination") is True else "false"
    overflow_strategy = str(render_options.get("overflow_strategy") or "split")

    title = metadata_value(metadata, "title")
    authors = metadata_value(metadata, "authors")
    key = metadata_value(metadata, "target_key", "requested_key")
    bpm = metadata_value(metadata, "bpm")
    time_signature = metadata_value(metadata, "time_signature")
    capo = metadata_value(metadata, "capo", default="none")
    overview_map = song_map(sequence)

    slides = [
        f"---\nmarp: true\ntheme: default\npaginate: {paginate}\nsize: 16:9\n---",
        default_marp_style(),
        "",
        f"# {html.escape(title)}",
        "",
        _meta_bar(key, bpm, time_signature, capo),
        "",
        f"**Mode:** {html.escape(mode)}  ",
        f"**Song map:** {overview_map}",
        "",
    ]
    if mode == "review":
        slides.extend(
            [
                f"**Authors:** {html.escape(authors)}  ",
                _source_summary(deck),
                "",
                _review_notes(deck),
            ]
        )
    else:
        review_notes = _review_notes(deck)
        if review_notes:
            slides.extend(["", review_notes])

    for index, entry in enumerate(sequence):
        section_name = arrangement_section_name(entry)
        section = sections.get(section_name, {})
        lines = section.get("lines", []) if isinstance(section, dict) else []
        display_title = section_display_title(
            section_name, section if isinstance(section, dict) else {}
        )
        rendered_lines = render_section_lines(section, lines)
        if not rendered_lines:
            cue = entry.get("cue") or "Cue-only or missing section content."
            rendered_lines = [f'<div class="cue-box">{html.escape(str(cue))}</div>']
        slide_render_options = get_slide_render_options(render_options, entry, section)
        max_lines_per_slide = positive_int(
            slide_render_options.get("max_line_pairs_per_slide"), default=6
        )
        line_chunks = chunk_rendered_lines(
            rendered_lines, overflow_strategy, max_lines_per_slide
        )
        chart_style = chart_style_attribute(slide_render_options)

        section_label = repeat_labels.get(index, display_title)
        chunk_labels = continuation_labels(section_label, len(line_chunks))
        for chunk_index, line_chunk in enumerate(line_chunks):
            next_label = context_label_for_offset(
                chunk_labels, chunk_index + 1, sequence, repeat_labels, index
            )
            after_label = context_label_for_offset(
                chunk_labels, chunk_index + 2, sequence, repeat_labels, index
            )

            slides.extend(
                [
                    "",
                    "---",
                    "",
                    f"## {html.escape(chunk_labels[chunk_index])}",
                    "",
                    _meta_bar(key, bpm, time_signature, capo),
                    "",
                    '<div class="layout">',
                    f'<div class="chart-lines"{chart_style}>',
                    *line_chunk,
                    "</div>",
                    '<div class="song-map">',
                    '<div class="context-label">Now</div>',
                    f'<div class="context-value">{html.escape(chunk_labels[chunk_index])}</div>',
                    '<div class="context-label">Next</div>',
                    f'<div class="context-value">{html.escape(next_label)}</div>',
                    '<div class="context-label">After</div>',
                    f'<div class="context-value">{html.escape(after_label)}</div>',
                    "</div>",
                    "</div>",
                ]
            )

            cue = entry.get("cue")
            if cue and chunk_index == 0:
                slides.extend(
                    ["", f'<div class="cue-box">{html.escape(str(cue))}</div>']
                )

    return "\n".join(slides).rstrip() + "\n"


def chunk_rendered_lines(
    rendered_lines: list[str], overflow_strategy: str, max_lines_per_slide: int
) -> list[list[str]]:
    """Split rendered lines into slide-sized chunks at line boundaries."""
    if overflow_strategy != "split" or len(rendered_lines) <= max_lines_per_slide:
        return [rendered_lines]
    return [
        rendered_lines[index : index + max_lines_per_slide]
        for index in range(0, len(rendered_lines), max_lines_per_slide)
    ]


def continuation_labels(base_label: str, chunk_count: int) -> list[str]:
    """Return section labels for continuation slides."""
    labels = [base_label]
    for index in range(1, chunk_count):
        suffix = "cont." if index == 1 else f"cont. {index}"
        labels.append(f"{base_label} {suffix}")
    return labels


def context_label_for_offset(
    chunk_labels: list[str],
    chunk_offset: int,
    sequence: list[dict[str, Any]],
    repeat_labels: dict[int, str],
    current_sequence_index: int,
) -> str:
    """Return a next/after label across continuation and arrangement items."""
    if chunk_offset < len(chunk_labels):
        return chunk_labels[chunk_offset]
    extra_sequence_steps = chunk_offset - len(chunk_labels) + 1
    target_index = current_sequence_index + extra_sequence_steps
    if target_index < len(sequence):
        return repeat_labels.get(
            target_index, arrangement_label(sequence[target_index])
        )
    return "End"


def render_section_lines(section: Any, lines: list[Any]) -> list[str]:
    """Render lyric/chord or instrumental section content. Honors YAML key order
    when both ``bars`` and ``lines`` are present on the same section."""
    rendered: list[str] = []
    rendered_bars: list[str] = []
    bars_first = True

    if isinstance(section, dict):
        bars = section.get("bars")
        repeat = int(section.get("repeat") or 1)

        if bars:
            section_keys = list(section.keys())
            bars_first = (
                "lines" not in section_keys
                or section_keys.index("bars") < section_keys.index("lines")
            )
            for _ in range(max(repeat, 1)):
                for row in bars:
                    if isinstance(row, list):
                        bar_text = "| " + " | ".join(str(chord) for chord in row) + " |"
                    else:
                        bar_text = str(row)
                    rendered_bars.append(
                        f'<div class="bar-line">{html.escape(bar_text)}</div>'
                    )

        if bars_first:
            rendered.extend(rendered_bars)

    for line in lines:
        rendered_line = render_chordpro_line(line)
        if rendered_line:
            rendered.append(rendered_line)

    if not bars_first:
        rendered.extend(rendered_bars)

    return rendered


def _meta_bar(key: str, bpm: str, time_signature: str, capo: str) -> str:
    return (
        '<div class="meta">'
        f"<span>Key: {html.escape(key)}</span>"
        f"<span>BPM: {html.escape(bpm)}</span>"
        f"<span>Time: {html.escape(time_signature)}</span>"
        f"<span>Capo: {html.escape(capo)}</span>"
        "</div>"
    )


def _source_summary(deck: dict[str, Any]) -> str:
    sources = deck.get("sources") or {}
    if not isinstance(sources, dict):
        return ""
    parts: list[str] = []
    for label in ("metadata", "lyrics_chords", "arrangement"):
        records = sources.get(label) or []
        if not isinstance(records, list):
            continue
        names = [str(item.get("label")) for item in records if isinstance(item, dict)]
        if names:
            parts.append(f"{label.replace('_', ' ').title()}: {', '.join(names)}")
    if not parts:
        return ""
    return '<div class="cue-box small">' + html.escape("; ".join(parts)) + "</div>"


def _review_notes(deck: dict[str, Any]) -> str:
    validation = deck.get("validation") or {}
    if not isinstance(validation, dict):
        return ""
    notes = list_text(validation.get("human_review_required"))
    if not notes:
        return ""
    escaped_notes = "; ".join(html.escape(note) for note in notes)
    return f'<div class="cue-box warning small">Human review: {escaped_notes}</div>'
