import sys
import unittest
from pathlib import Path

import yaml


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from band_deck_helpers import default_marp_style, generate_practice_marp  # noqa: E402
from band_deck_generator.render_options import (  # noqa: E402
    DEFAULT_FONT_SIZE_PX,
    FONT_SIZE_MAX_PX,
    FONT_SIZE_MIN_PX,
    FONT_SIZE_OPTION_KEYS,
    render_font_size_schema,
)
from band_deck_generator.update_render_docs import planned_updates  # noqa: E402


class GeneratePracticeMarpTests(unittest.TestCase):
    def test_chord_and_lyric_rows_share_the_same_monospace_column_width(self) -> None:
        style = default_marp_style()

        self.assertIn("--chart-font-size: 30px;", style)
        self.assertIn("--lyric-font-size: var(--chart-font-size);", style)
        self.assertIn("--chord-font-size: var(--chart-font-size);", style)
        self.assertIn(
            ".chord-line {\n  color: #c2410c;\n  font-size: var(--chord-font-size);",
            style,
        )
        self.assertIn(
            ".lyric-line {\n  color: #111827;\n  font-size: var(--lyric-font-size);",
            style,
        )

    def test_non_split_slides_keep_next_and_after_arrangement_context(self) -> None:
        deck = {
            "request": {"title": "Context Test"},
            "metadata": {
                "title": "Context Test",
                "authors": ["Example"],
                "target_key": "G",
                "bpm": "unknown",
                "time_signature": "4/4",
                "capo": "none",
            },
            "sources": {
                "metadata": [{"label": "test"}],
                "lyrics_chords": [{"label": "test"}],
            },
            "normalised_chordpro": {
                "sections": {
                    "Intro": {
                        "type": "instrumental",
                        "bars": [["G", "D"]],
                        "lines": [],
                    },
                    "Verse 1": {
                        "type": "verse",
                        "lines": [{"chordpro": "[G]licensed line"}],
                    },
                    "Chorus": {
                        "type": "chorus",
                        "lines": [{"chordpro": "[C]licensed chorus"}],
                    },
                }
            },
            "arrangement": {
                "sequence": [
                    {"section": "Intro"},
                    {"section": "Verse 1"},
                    {"section": "Chorus"},
                ]
            },
            "render": {"mode": "practice"},
        }

        marp = generate_practice_marp(deck)
        intro_slide = marp.split("## Intro\n", 1)[1].split("\n---", 1)[0]

        self.assertIn('<div class="context-value">Verse 1</div>', intro_slide)
        self.assertIn('<div class="context-value">Chorus</div>', intro_slide)

    def test_splits_long_lyric_sections_at_line_pair_boundaries(self) -> None:
        deck = {
            "request": {"title": "Long Section Test"},
            "metadata": {
                "title": "Long Section Test",
                "authors": ["Example"],
                "target_key": "G",
                "bpm": "unknown",
                "time_signature": "4/4",
                "capo": "none",
            },
            "sources": {
                "metadata": [{"label": "test"}],
                "lyrics_chords": [{"label": "test"}],
            },
            "normalised_chordpro": {
                "sections": {
                    "Verse 1": {
                        "type": "verse",
                        "lines": [
                            {"chordpro": f"[G]licensed line {line_number}"}
                            for line_number in range(1, 8)
                        ],
                    }
                }
            },
            "arrangement": {"sequence": [{"section": "Verse 1"}]},
            "render": {
                "mode": "practice",
                "overflow_strategy": "split",
                "max_line_pairs_per_slide": 3,
            },
        }

        marp = generate_practice_marp(deck)

        self.assertIn("## Verse 1\n", marp)
        self.assertIn("## Verse 1 cont.\n", marp)
        self.assertIn("## Verse 1 cont. 2\n", marp)
        self.assertLess(marp.index("licensed line 3"), marp.index("## Verse 1 cont."))
        self.assertLess(marp.index("licensed line 6"), marp.index("## Verse 1 cont. 2"))

    def test_arrangement_entries_can_override_line_count_and_font_size(self) -> None:
        deck = {
            "request": {"title": "Per Slide Render Test"},
            "metadata": {
                "title": "Per Slide Render Test",
                "authors": ["Example"],
                "target_key": "G",
                "bpm": "unknown",
                "time_signature": "4/4",
                "capo": "none",
            },
            "sources": {
                "metadata": [{"label": "test"}],
                "lyrics_chords": [{"label": "test"}],
            },
            "normalised_chordpro": {
                "sections": {
                    "Verse": {
                        "type": "verse",
                        "lines": [
                            {"chordpro": f"[G]licensed line {line_number}"}
                            for line_number in range(1, 5)
                        ],
                    }
                }
            },
            "arrangement": {
                "sequence": [
                    {
                        "section": "Verse",
                        "label": "Verse small",
                        "render": {
                            "max_line_pairs_per_slide": 2,
                            "font_size_px": 26,
                            "chord_font_px": 22,
                        },
                    },
                    {
                        "section": "Verse",
                        "label": "Verse large",
                        "render": {
                            "max_line_pairs_per_slide": 4,
                            "font_size_px": 34,
                            "lyric_font_px": 36,
                        },
                    },
                ]
            },
            "render": {
                "mode": "practice",
                "overflow_strategy": "split",
                "max_line_pairs_per_slide": 6,
            },
        }

        marp = generate_practice_marp(deck)

        self.assertIn("## Verse small cont.\n", marp)
        self.assertNotIn("## Verse large cont.\n", marp)
        self.assertIn(
            '<div class="chart-lines" style="--chart-font-size: 26px; '
            '--chord-font-size: 22px;">',
            marp,
        )
        self.assertIn(
            '<div class="chart-lines" style="--chart-font-size: 34px; '
            '--lyric-font-size: 36px;">',
            marp,
        )

    def test_chart_font_sizes_are_clamped_to_shared_bounds(self) -> None:
        deck = {
            "request": {"title": "Clamped Font Test"},
            "metadata": {
                "title": "Clamped Font Test",
                "authors": ["Example"],
                "target_key": "G",
                "bpm": "unknown",
                "time_signature": "4/4",
                "capo": "none",
            },
            "sources": {
                "metadata": [{"label": "test"}],
                "lyrics_chords": [{"label": "test"}],
            },
            "normalised_chordpro": {
                "sections": {
                    "Verse": {
                        "type": "verse",
                        "lines": [{"chordpro": "[G]licensed line"}],
                    }
                }
            },
            "arrangement": {
                "sequence": [
                    {
                        "section": "Verse",
                        "render": {
                            "font_size_px": 999,
                            "chord_font_px": 2,
                        },
                    }
                ]
            },
        }

        marp = generate_practice_marp(deck)

        self.assertIn(
            f'<div class="chart-lines" style="--chart-font-size: {FONT_SIZE_MAX_PX}px; '
            f'--chord-font-size: {FONT_SIZE_MIN_PX}px;">',
            marp,
        )

    def test_rejects_legacy_top_level_shape(self) -> None:
        legacy_deck = {
            "title": "Legacy Shape",
            "authors": ["Example"],
            "arrangement": ["Verse 1"],
            "sections": {
                "Verse 1": {
                    "type": "verse",
                    "lines": [{"chordpro": "[G]licensed line"}],
                }
            },
        }

        with self.assertRaisesRegex(ValueError, "canonical deck shape"):
            generate_practice_marp(legacy_deck)


class RenderOptionConfigurationTests(unittest.TestCase):
    def test_schema_font_size_definition_uses_shared_constants(self) -> None:
        schema_path = Path(__file__).resolve().parents[1] / "schema/song-deck.schema.yaml"
        schema = yaml.safe_load(schema_path.read_text(encoding="utf-8"))

        self.assertEqual(
            {
                "type": "integer",
                "minimum": FONT_SIZE_MIN_PX,
                "maximum": FONT_SIZE_MAX_PX,
            },
            schema["$defs"]["fontSizePx"],
        )

        render_properties = schema["$defs"]["renderOptions"]["properties"]
        for option_key in FONT_SIZE_OPTION_KEYS:
            self.assertEqual(
                {"$ref": "#/$defs/fontSizePx"},
                render_properties[option_key],
            )

    def test_render_font_size_schema_is_generated_from_shared_constants(self) -> None:
        self.assertEqual(
            {
                "type": "integer",
                "minimum": FONT_SIZE_MIN_PX,
                "maximum": FONT_SIZE_MAX_PX,
            },
            render_font_size_schema(),
        )

    def test_render_docs_updates_include_shared_font_numbers(self) -> None:
        updates = planned_updates()
        rendered_text = "\n".join(update.replacement for update in updates)

        self.assertIn(f"font_size_px: {DEFAULT_FONT_SIZE_PX}", rendered_text)
        self.assertIn(
            f"Supported chart font sizes: {FONT_SIZE_MIN_PX}–{FONT_SIZE_MAX_PX}px.",
            rendered_text,
        )


if __name__ == "__main__":
    unittest.main()
