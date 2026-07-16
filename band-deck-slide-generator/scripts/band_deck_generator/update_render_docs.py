"""Synchronize render-option schema and docs from shared constants.

Use ``scripts/update_render_docs.py`` after changing values in
``render_options.py``. This module owns the implementation so it can also be
imported by tests to verify that generated snippets stay in sync.
"""

from dataclasses import dataclass
from pathlib import Path

from band_deck_generator.render_options import (
    DEFAULT_FONT_SIZE_PX,
    FONT_SIZE_MAX_PX,
    FONT_SIZE_MIN_PX,
)


PROJECT_DIR = Path(__file__).resolve().parents[2]
SCHEMA_PATH = PROJECT_DIR / "schema/song-deck.schema.yaml"
START_MARKER = "<!-- render-options:start -->"
END_MARKER = "<!-- render-options:end -->"


@dataclass(frozen=True)
class DocumentationUpdate:
    """A generated replacement block for one Markdown file."""

    path: Path
    replacement: str


def practice_defaults_snippet(
    include_full_options: bool,
    *,
    include_theme: bool = False,
    include_verification: bool = False,
) -> str:
    """Build a generated Markdown block for practice render defaults."""
    lines = [
        START_MARKER,
        "```yaml",
        "render:",
    ]
    if include_full_options:
        lines.extend(
            [
                "  mode: practice",
                "  chord_layout: above_lyrics",
                "  show_full_song_map: false",
                "  show_pagination: false",
                "  overflow_strategy: split",
            ]
        )
    lines.extend(
        [
            "  max_line_pairs_per_slide: 6",
            f"  font_size_px: {DEFAULT_FONT_SIZE_PX}",
        ]
    )
    if include_full_options:
        lines.append("  continuation_labels: true")
    if include_theme:
        lines.append("  theme: band_deck_light")
    if include_verification:
        lines.extend(
            [
                "",
                "verification:",
                "  lyrics: unverified",
                "  chords: unverified",
                "  ccli: unverified",
            ]
        )
    lines.extend(
        [
            "```",
            "",
            f"Supported chart font sizes: {FONT_SIZE_MIN_PX}–{FONT_SIZE_MAX_PX}px.",
            END_MARKER,
        ]
    )
    return "\n".join(lines)


def planned_updates() -> list[DocumentationUpdate]:
    """Return every Markdown file and replacement block managed by this script."""
    return [
        DocumentationUpdate(
            PROJECT_DIR / "README.md",
            practice_defaults_snippet(include_full_options=False),
        ),
        DocumentationUpdate(
            PROJECT_DIR / "SKILL.md",
            practice_defaults_snippet(
                include_full_options=True,
                include_verification=True,
            ),
        ),
        DocumentationUpdate(
            PROJECT_DIR / "docs/marp-style-guide.md",
            practice_defaults_snippet(
                include_full_options=True,
                include_theme=True,
            ),
        ),
    ]


def replace_marked_block(text: str, replacement: str) -> str:
    """Replace one managed Markdown block delimited by render-option markers."""
    start = text.find(START_MARKER)
    end = text.find(END_MARKER)
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"missing generated docs markers {START_MARKER} / {END_MARKER}")
    end += len(END_MARKER)
    return f"{text[:start]}{replacement}{text[end:]}"


def update_render_docs() -> list[Path]:
    """Rewrite managed Markdown blocks and return paths that changed."""
    changed: list[Path] = []
    for update in planned_updates():
        original = update.path.read_text(encoding="utf-8")
        updated = replace_marked_block(original, update.replacement)
        if updated != original:
            update.path.write_text(updated, encoding="utf-8")
            changed.append(update.path)
    return changed


def render_schema_block() -> str:
    """Build the YAML schema block for the shared font-size definition."""
    return (
        "  fontSizePx:\n"
        "    type: integer\n"
        f"    minimum: {FONT_SIZE_MIN_PX}\n"
        f"    maximum: {FONT_SIZE_MAX_PX}"
    )


def update_render_schema() -> list[Path]:
    """Rewrite the schema font-size definition and return paths that changed."""
    original = SCHEMA_PATH.read_text(encoding="utf-8")
    start = original.find("  fontSizePx:\n")
    end = original.find("\n\n  keyOrUnknown:", start)
    if start == -1 or end == -1:
        raise ValueError("missing fontSizePx schema block")
    updated = f"{original[:start]}{render_schema_block()}{original[end:]}"
    if updated == original:
        return []
    SCHEMA_PATH.write_text(updated, encoding="utf-8")
    return [SCHEMA_PATH]


def update_render_contract() -> list[Path]:
    """Update schema and Markdown render docs from shared constants."""
    return [*update_render_schema(), *update_render_docs()]
