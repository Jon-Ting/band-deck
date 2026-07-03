from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from band_deck_helpers import default_marp_style, generate_practice_marp  # noqa: E402


class GeneratePracticeMarpTests(unittest.TestCase):
    def test_chord_and_lyric_rows_share_the_same_monospace_column_width(self) -> None:
        style = default_marp_style()

        self.assertIn("--chart-font-size: 30px;", style)
        self.assertIn(
            ".chord-line {\n  color: #c2410c;\n  font-size: var(--chart-font-size);",
            style,
        )
        self.assertIn(
            ".lyric-line {\n  color: #111827;\n  font-size: var(--chart-font-size);",
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


if __name__ == "__main__":
    unittest.main()
