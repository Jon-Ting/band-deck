"""Tests for generating Marp markdown from structured song YAML."""

import pytest

from src.utils.chordpro_parser import ChordPosition, ChordProLine
from src.utils.marp_generator import MarpOptions, generate_marp
from src.utils.yaml_models import SongSection, SongYAML


def make_song() -> SongYAML:
    return SongYAML(
        title="Example Song",
        authors=["Example Writer", "Second Writer"],
        ccli_number="1234567",
        copyright="Copyright 2026 Example Publisher",
        original_key="G",
        target_key="D",
        bpm=74,
        time_signature="6/8",
        capo="2",
        sections={
            "Verse 1": SongSection(
                name="Verse 1",
                type="verse",
                lines=[
                    ChordProLine(
                        text="Placeholder lyric line",
                        chords=[ChordPosition(chord="D", position=0)],
                    )
                ],
                notes=["Keep the first pass restrained"],
            ),
            "Chorus": SongSection(
                name="Chorus",
                type="chorus",
                lines=[
                    ChordProLine(
                        text="Lift the placeholder hook",
                        chords=[
                            ChordPosition(chord="G", position=0),
                            ChordPosition(chord="A", position=9),
                        ],
                    )
                ],
            ),
        },
        arrangement=["Verse 1", "Chorus", "Verse 1"],
        practice_notes={"general": ["Watch the push into the chorus"]},
        source_urls=["https://example.test/song"],
    )


def test_generate_marp_includes_frontmatter_css_and_title_slide_metadata():
    result = generate_marp(make_song())

    assert result.startswith("---\nmarp: true\n")
    assert "size: 16:9" in result
    assert "<style>" in result
    assert ".chord" in result
    assert ".lyric" in result
    assert ".meta" in result
    assert ".song-map" in result
    assert ".current" in result
    assert ".cue-box" in result
    assert "# Example Song" in result
    assert "Example Writer, Second Writer" in result
    assert "CCLI: 1234567" in result
    assert "Copyright 2026 Example Publisher" in result
    assert "Key: D" in result
    assert "BPM: 74" in result
    assert "Time: 6/8" in result
    assert "Capo: 2" in result
    assert "Verse 1" in result
    assert "Chorus" in result
    assert "Watch the push into the chorus" in result


def test_generate_marp_creates_section_slides_with_inline_chords_and_cues():
    result = generate_marp(make_song())

    assert result.count("\n---\n##") == 3
    assert "## Verse 1" in result
    assert "## Chorus" in result
    assert '<span class="chord">D</span>Placeholder lyric line' in result
    assert (
        '<span class="chord">G</span>Lift the '
        '<span class="chord">A</span>placeholder hook'
    ) in result
    assert '<span class="current">Verse 1</span> &rarr; Chorus &rarr; Verse 1' in result
    assert 'Verse 1 &rarr; <span class="current">Chorus</span> &rarr; Verse 1' in result
    assert "Next: Chorus" in result
    assert "Next: Verse 1" in result
    assert "Next: End" in result
    assert "Keep the first pass restrained" in result


class TestTitleSlideStructure:
    """Unit tests for title slide completeness (Requirement 8.2)."""

    def test_title_slide_contains_title_and_authors(self):
        song = make_song()
        result = generate_marp(song)

        assert "# Example Song" in result
        assert "Example Writer, Second Writer" in result

    def test_title_slide_contains_ccli_when_present(self):
        song = make_song()
        result = generate_marp(song)

        assert "CCLI: 1234567" in result

    def test_title_slide_omits_ccli_when_missing(self):
        song = make_song()
        song.ccli_number = None
        result = generate_marp(song)

        assert "CCLI:" not in result

    def test_title_slide_contains_copyright_when_present(self):
        song = make_song()
        result = generate_marp(song)

        assert "Copyright 2026 Example Publisher" in result

    def test_title_slide_omits_copyright_when_missing(self):
        song = make_song()
        song.copyright = None
        result = generate_marp(song)

        assert "Copyright 2026 Example Publisher" not in result

    def test_title_slide_contains_song_map_by_default(self):
        song = make_song()
        result = generate_marp(song)

        assert "Song map:" in result
        assert "Verse 1" in result
        assert "Chorus" in result

    def test_title_slide_hides_song_map_when_disabled(self):
        song = make_song()
        options = MarpOptions(show_song_map=False)
        result = generate_marp(song, options=options)

        assert "Song map:" not in result

    def test_title_slide_hides_metadata_when_disabled(self):
        song = make_song()
        options = MarpOptions(show_metadata=False)
        result = generate_marp(song, options=options)

        assert '<div class="meta">' not in result
        assert "Key: D" not in result

    def test_title_slide_shows_metadata_by_default(self):
        song = make_song()
        result = generate_marp(song)

        assert '<div class="meta">' in result
        assert "Key: D" in result
        assert "BPM: 74" in result
        assert "Time: 6/8" in result
        assert "Capo: 2" in result

    def test_title_slide_shows_general_practice_notes_by_default(self):
        song = make_song()
        result = generate_marp(song)

        assert "Watch the push into the chorus" in result
        assert '<div class="cue-box">' in result

    def test_title_slide_hides_practice_notes_when_disabled(self):
        song = make_song()
        options = MarpOptions(show_practice_notes=False)
        result = generate_marp(song, options=options)

        assert "Watch the push into the chorus" not in result
        assert '<div class="cue-box">' not in result

    def test_title_slide_handles_empty_arrangement(self):
        song = make_song()
        song.arrangement = []
        result = generate_marp(song)

        assert "# Example Song" in result
        assert "Song map:" not in result

    def test_title_slide_escapes_html_special_characters(self):
        song = make_song()
        song.title = "Song <script> & Test"
        result = generate_marp(song)

        assert "<script>" not in result
        assert "&lt;script&gt;" in result
        assert "&amp;" in result


class TestSectionSlideStructure:
    """Unit tests for section slide completeness (Requirement 8.3)."""

    def test_section_slide_contains_section_heading(self):
        song = make_song()
        result = generate_marp(song)

        assert "## Verse 1" in result
        assert "## Chorus" in result

    def test_section_slide_contains_lyrics_with_inline_chords(self):
        song = make_song()
        result = generate_marp(song)

        assert '<span class="chord">D</span>Placeholder lyric line' in result
        assert '<span class="lyric">' in result
        assert '<div class="line">' in result

    def test_section_slide_contains_metadata_bar_by_default(self):
        song = make_song()
        result = generate_marp(song)

        assert '<div class="meta">' in result
        assert "Key: D" in result

    def test_section_slide_hides_metadata_when_disabled(self):
        song = make_song()
        options = MarpOptions(show_metadata=False)
        result = generate_marp(song, options=options)

        # Title slide still has authors, but metadata bar should not appear
        # anywhere after the frontmatter CSS block
        after_css = result.split("</style>")[1]
        assert '<div class="meta">' not in after_css

    def test_section_slide_contains_song_map_with_current_highlight(self):
        song = make_song()
        result = generate_marp(song)

        # First section (Verse 1) should be highlighted
        assert '<span class="current">Verse 1</span> &rarr; Chorus &rarr; Verse 1' in result
        # Second section (Chorus) should be highlighted
        assert 'Verse 1 &rarr; <span class="current">Chorus</span> &rarr; Verse 1' in result

    def test_section_slide_hides_song_map_when_disabled(self):
        song = make_song()
        options = MarpOptions(show_song_map=False)
        result = generate_marp(song, options=options)

        assert '<span class="current">' not in result
        assert "&rarr;" not in result

    def test_section_slide_shows_next_section_cue(self):
        song = make_song()
        result = generate_marp(song)

        assert "Next: Chorus" in result
        assert "Next: Verse 1" in result
        assert "Next: End" in result

    def test_section_slide_shows_section_notes_when_present(self):
        song = make_song()
        result = generate_marp(song)

        assert "Keep the first pass restrained" in result

    def test_section_slide_shows_practice_notes_when_present(self):
        song = make_song()
        song.practice_notes = {"Verse 1": ["Soft dynamics"]}
        result = generate_marp(song)

        assert "Soft dynamics" in result

    def test_section_slide_hides_notes_when_practice_notes_disabled(self):
        song = make_song()
        options = MarpOptions(show_practice_notes=False)
        result = generate_marp(song, options=options)

        assert "Keep the first pass restrained" not in result

    def test_section_slide_shows_end_for_last_section(self):
        song = make_song()
        song.arrangement = ["Chorus"]
        result = generate_marp(song)

        assert "Next: End" in result
        assert "Next: Chorus" not in result

    def test_section_slide_escapes_html_in_lyrics(self):
        song = make_song()
        song.sections["Verse 1"].lines[0].text = "Line <script> test"
        result = generate_marp(song)

        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_section_slide_escapes_html_in_chords(self):
        song = make_song()
        song.sections["Verse 1"].lines[0].chords[0].chord = "C<"
        result = generate_marp(song)

        assert "C<" not in result
        assert "C&lt;" in result

    @pytest.mark.parametrize(
        "style", ["practice", "performance", "simple"]
    )
    def test_generate_marp_accepts_all_styles(self, style):
        song = make_song()
        result = generate_marp(song, style=style)

        assert "# Example Song" in result
        assert "## Verse 1" in result


class TestCssInclusion:
    """Unit tests for CSS template inclusion (Requirement 8.5)."""

    def test_css_is_included_in_output(self):
        result = generate_marp(make_song())

        assert "<style>" in result
        assert "</style>" in result

    def test_css_contains_required_classes(self):
        result = generate_marp(make_song())
        css_start = result.index("<style>")
        css_end = result.index("</style>")
        css_block = result[css_start:css_end]

        required_classes = [
            ".chord",
            ".lyric",
            ".meta",
            ".song-map",
            ".current",
            ".cue-box",
            ".line",
            ".layout",
        ]
        for cls in required_classes:
            assert cls in css_block, f"Missing CSS class: {cls}"

    def test_css_uses_default_font_size(self):
        result = generate_marp(make_song())

        assert "font-size: 24px" in result

    def test_css_uses_custom_font_size(self):
        song = make_song()
        options = MarpOptions(font_size="32px")
        result = generate_marp(song, options=options)

        assert "font-size: 32px" in result
        assert "font-size: 24px" not in result

    def test_css_uses_default_aspect_ratio(self):
        result = generate_marp(make_song())

        assert "size: 16:9" in result

    def test_css_uses_custom_aspect_ratio(self):
        song = make_song()
        options = MarpOptions(aspect_ratio="4:3")
        result = generate_marp(song, options=options)

        assert "size: 4:3" in result
        assert "size: 16:9" not in result

    def test_css_escapes_font_size_value(self):
        song = make_song()
        options = MarpOptions(font_size="24px; </style><script>")
        result = generate_marp(song, options=options)

        assert "<script>" not in result
        assert "&lt;script&gt;" in result
        assert "</style>" not in result or "&lt;/style&gt;" in result

    def test_css_overrides_body_background_to_white(self):
        """Regression: Marp's default theme sets ``body`` to ``#000``, which
        turns the in-app preview iframe black when a section SVG doesn't
        fully cover the viewport. The bundled CSS overrides this so the
        embedded preview shows on a light surface."""
        result = generate_marp(make_song())

        css_block = result[result.index("<style>"):result.index("</style>") + len("</style>")]
        assert "body" in css_block
        assert "#ffffff" in css_block.lower() or "white" in css_block.lower()
