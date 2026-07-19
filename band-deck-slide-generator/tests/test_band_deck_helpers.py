import sys
import unittest
from pathlib import Path

import yaml


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from band_deck_helpers import default_marp_style, generate_practice_marp, render_chordpro_line  # noqa: E402
from band_deck_generator.render_options import (  # noqa: E402
    DEFAULT_FONT_SIZE_PX,
    FONT_SIZE_MAX_PX,
    FONT_SIZE_MIN_PX,
    FONT_SIZE_OPTION_KEYS,
    render_font_size_schema,
)
from band_deck_generator.update_render_docs import planned_updates  # noqa: E402


class RenderChordproLineTests(unittest.TestCase):
    """Standalone tests for :func:`render_chordpro_line`.

    Split out from the Marp-integrated tests below so a regression in the
    rendering helper (e.g. a swallowed return that dropped the chord
    line) is reported independently from slide generation rather than
    buried inside deck-shaped integration outputs.
    """

    def test_brackets_present_render_chord_above_lyric(self) -> None:
        # Regression: the ``if not chord_cells:`` branch used to swallow
        # the ``chord_line`` assignment because both statements were
        # accidentally joined on a single line. Without the fix, only
        # ``<div class="lyric-line">`` was emitted for bracketed input.
        rendered = render_chordpro_line({"chordpro": "[G]Amazing [D/F#]grace"})

        assert '<div class="line-pair">' in rendered
        assert '<div class="chord-line">' in rendered
        assert '<div class="lyric-line">Amazing grace</div>' in rendered
        assert rendered.count('class="chord-line"') == 1

    def test_unicode_sharp_normalises_before_bracket_match(self) -> None:
        # ``D/F\u266f`` (music-typographic sharp) gets normalised to
        # ``D/F#`` before bracket matching so the ASCII grammar regex
        # sees a valid chord. The pretty renderer then turns the
        # accidental back into music typography so the slide renders
        # ``F\u266f`` while the underlying storage remains ``F#``.
        rendered = render_chordpro_line(
            {"chordpro": "[D/F\u266f]Amazing [G\u2077]grace"}
        )

        # ``G\u2077`` was unicode superscript 7; it demotes to ``7``
        # wrapped in ``<sup>`` so the extension still reads as raised.
        assert "<sup>7</sup>" in rendered
        # Slash bass is wrapped in ``<span class="bass">`` for visual
        # distinction and the accidental renders as music typography.
        assert '<span class="bass">/F\u266f</span>' in rendered
        # No literal Unicode superscript digits remain in the output.
        assert "\u2077" not in rendered

    def test_unicode_modifier_letters_in_chord_normalise_to_ascii(self) -> None:
        # The legacy ``Cmaj7``-style is sometimes written with four
        # modifier letters: ``C\u1d50\u1d43\u02b2\u2077`` (``m``, ``a``,
        # ``j``, superscript ``7``). After normalisation this should
        # render as ``Cmaj<sup>7</sup>`` (root + quality together in
        # the chord body; only the extension digit is superscripted).
        rendered = render_chordpro_line(
            {"chordpro": "[C\u1d50\u1d43\u02b2\u2077]Amazing grace"}
        )

        assert "Cmaj" in rendered
        assert "<sup>7</sup>" in rendered
        assert rendered.count('class="chord-line"') == 1
        # Unicode modifier letters should be stripped from output.
        for codepoint in ["\u1d50", "\u1d43", "\u02b2", "\u2077"]:
            assert codepoint not in rendered

    def test_no_brackets_render_lyric_only(self) -> None:
        rendered = render_chordpro_line({"chordpro": "plain lyric line"})

        assert rendered == '<div class="lyric-line">plain lyric line</div>'


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

    def test_instrumental_bars_render_with_spaces_and_allow_sustain_dashes(
        self,
    ) -> None:
        deck = {
            "request": {"title": "Bar Format Test"},
            "metadata": {
                "title": "Bar Format Test",
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
                        "bars": [
                            ["Em", "-", "E", "-"],
                            ["G", "D"],
                            [],
                            "| Custom Bar |",
                            "Plain bar text",
                        ],
                    }
                }
            },
            "arrangement": {"sequence": [{"section": "Intro"}]},
            "render": {"mode": "practice"},
        }

        marp = generate_practice_marp(deck)

        self.assertIn('<div class="bar-line">| Em - E - |</div>', marp)
        self.assertIn('<div class="bar-line">| G D |</div>', marp)
        self.assertIn('<div class="bar-line">| |</div>', marp)
        self.assertIn('<div class="bar-line">| Custom Bar |</div>', marp)
        self.assertIn('<div class="bar-line">Plain bar text</div>', marp)

    def test_bars_per_line_groups_consecutive_bars_into_single_div(
        self,
    ) -> None:
        deck = {
            "request": {"title": "Bars Per Line Test"},
            "metadata": {
                "title": "Bars Per Line Test",
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
                        "render": {"bars_per_line": 2},
                        "bars": [
                            ["Em", "-", "E", "-"],
                            ["A", "D", "G", "D"],
                            ["B", "E"],
                            ["C", "F"],
                        ],
                    }
                }
            },
            "arrangement": {"sequence": [{"section": "Intro"}]},
            "render": {"mode": "practice"},
        }

        marp = generate_practice_marp(deck)

        self.assertIn(
            '<div class="bar-line">| Em - E - | A D G D |</div>', marp
        )
        self.assertIn('<div class="bar-line">| B E | C F |</div>', marp)
        self.assertEqual(marp.count('<div class="bar-line">'), 2)

    def test_bars_per_line_falls_back_to_one_for_invalid_values(self) -> None:
        deck = {
            "request": {"title": "Bars Per Line Fallback Test"},
            "metadata": {
                "title": "Bars Per Line Fallback Test",
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
                        "render": {"bars_per_line": 0},
                        "bars": [["G", "D"], ["A", "E"]],
                    }
                }
            },
            "arrangement": {"sequence": [{"section": "Intro"}]},
            "render": {"mode": "practice"},
        }

        marp = generate_practice_marp(deck)

        self.assertIn('<div class="bar-line">| G D |</div>', marp)
        self.assertIn('<div class="bar-line">| A E |</div>', marp)

    def test_bar_cells_render_prettified_extensions_and_bass(self) -> None:
        # Bars hold the same kind of chord strings as lyric lines, so the
        # :func:`format_chord_inner` renderer should apply here too:
        # extensions in <sup>, slash bass wrapped in <span class="bass">,
        # and accidental-as-music-glyph when an ASCII ``#`` is given.
        deck = {
            "request": {"title": "Altered Bar Test"},
            "metadata": {
                "title": "Altered Bar Test",
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
                        "bars": [
                            "G7b9 D/F# - E",
                            ["Bm7b5", "A7b9"],
                        ],
                    }
                }
            },
            "arrangement": {"sequence": [{"section": "Intro"}]},
            "render": {"mode": "practice"},
        }

        marp = generate_practice_marp(deck)

        # String-bar cell with altered dominant renders the extension in
        # <sup> and the bass with a music-sharp glyph inside <span class="bass">.
        self.assertIn("<sup>7</sup>", marp)
        self.assertIn("<sup>\u266d9</sup>", marp)
        self.assertIn('<span class="bass">/F\u266f</span>', marp)

        # Sustain dashes still render as plain text (no <span>/<sup> wrapping).
        self.assertIn("- E", marp)

    def test_bar_cell_sustain_dashes_and_custom_strings_pass_through(self) -> None:
        # Non-chord content (sustain dashes, custom bar labels) goes through
        # ``format_chord_inner``'s invalid-input escape, so the final markup
        # is plain text — no spurious <sup> or <span class="bass"> wrapping.
        deck = {
            "request": {"title": "Bar Plain Text"},
            "metadata": {
                "title": "Bar Plain Text",
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
                        "bars": [
                            ["Em", "-", "E", "-"],
                            "| N.C. |",
                        ],
                    }
                }
            },
            "arrangement": {"sequence": [{"section": "Intro"}]},
            "render": {"mode": "practice"},
        }

        marp = generate_practice_marp(deck)

        # Existing plain-text bar expectations still hold.
        self.assertIn('<div class="bar-line">| Em - E - |</div>', marp)
        # ``N.C.`` is not a recognised chord; the renderer falls back to
        # escaped raw text. Critically it stays outside any <sup>/<span>.
        self.assertIn("N.C.", marp)

    def test_bar_cells_html_escape_user_strings(self) -> None:
        # A user-authored bar string that contains HTML-like characters
        # must be HTML-escaped, not rendered as raw markup. The renderer's
        # escape happens inside ``format_chord_inner`` via the invalid-
        # input fallback.
        from band_deck_helpers import render_section_lines

        rendered = render_section_lines(
            {"type": "instrumental", "bars": [["<script>alert(1)</script>"]]},
            [],
        )
        # No live <script> tag should reach the output.
        assert "<script>" not in "".join(rendered)
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in "".join(rendered)


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
