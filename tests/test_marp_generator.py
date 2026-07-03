"""Tests for generating Marp markdown from structured song YAML."""

from src.utils.chordpro_parser import ChordPosition, ChordProLine
from src.utils.marp_generator import generate_marp
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
