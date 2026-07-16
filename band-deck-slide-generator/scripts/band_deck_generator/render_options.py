"""Shared render option definitions for scripts, schema, and docs.

This module is the single source of truth for configurable render-option
bounds. Generator code imports these values at runtime, the schema sync script
writes them into ``schema/song-deck.schema.yaml``, and documentation snippets
are regenerated from the same constants.
"""

from typing import Any


FONT_SIZE_MIN_PX = 22
FONT_SIZE_MAX_PX = 38
DEFAULT_FONT_SIZE_PX = 28

FONT_SIZE_OPTION_KEYS = (
    "font_size_px",
    "chart_font_px",
    "lyric_font_px",
    "chord_font_px",
    "bar_font_px",
    "min_lyric_font_px",
    "min_chord_font_px",
)

SLIDE_RENDER_KEYS = (
    "max_line_pairs_per_slide",
    *FONT_SIZE_OPTION_KEYS,
)


def clamp_font_size_px(value: int) -> int:
    """Clamp a parsed font size to the supported practice-deck range."""
    return min(max(value, FONT_SIZE_MIN_PX), FONT_SIZE_MAX_PX)


def font_size_px_or_none(value: Any) -> int | None:
    """Parse an optional font-size value and return a clamped pixel size."""
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return clamp_font_size_px(parsed)


def render_font_size_schema() -> dict[str, int | str]:
    """Return the JSON Schema fragment used for all render font-size fields."""
    return {
        "type": "integer",
        "minimum": FONT_SIZE_MIN_PX,
        "maximum": FONT_SIZE_MAX_PX,
    }
