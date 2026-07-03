"""Tests for converting current search results into structured YAML models."""

from src.utils.chordpro_parser import ChordPosition
from src.utils.yaml_converter import (
    combine_chord_and_lyric_lines,
    convert_to_yaml,
    infer_section_type,
    parse_sections_from_content,
    transpose_chordpro_lines,
)


def test_convert_to_yaml_preserves_metadata_and_prefers_search_name():
    song_data = {
        "title": "Scraped Worship Together Title",
        "search_name": "Congregation Title",
        "artist": "Example Artist",
        "content": "Verse 1\n    G      D\nHow great is God",
        "source_url": "https://www.worshiptogether.com/songs/example/",
        "original_key": "G",
        "key": "D",
    }

    result = convert_to_yaml(song_data, target_key="D")

    assert result.title == "Congregation Title"
    assert result.authors == ["Example Artist"]
    assert result.original_key == "G"
    assert result.target_key == "D"
    assert result.source_urls == ["https://www.worshiptogether.com/songs/example/"]
    assert result.ccli_number is None
    assert result.copyright is None
    assert result.bpm is None
    assert result.time_signature is None
    assert result.capo is None


def test_parse_sections_preserves_names_types_and_arrangement_order():
    content = "\n\n".join(
        [
            "Verse 1\nG\nLine one",
            "Chorus\nD\nLine two",
            "Bridge\nEm\nLine three",
        ]
    )

    sections = parse_sections_from_content(content)

    assert list(sections) == ["Verse 1", "Chorus", "Bridge"]
    assert sections["Verse 1"].name == "Verse 1"
    assert sections["Verse 1"].type == "verse"
    assert sections["Chorus"].type == "chorus"
    assert sections["Bridge"].type == "bridge"


def test_convert_to_yaml_uses_section_order_as_arrangement():
    song_data = {
        "title": "Example",
        "artist": "",
        "content": "Verse 1\nG\nLine one\n\nChorus\nD\nLine two",
        "original_key": "G",
    }

    result = convert_to_yaml(song_data)

    assert result.authors == ["Unknown"]
    assert result.arrangement == ["Verse 1", "Chorus"]


def test_infer_section_type_maps_supported_section_names():
    assert infer_section_type("Verse 2") == "verse"
    assert infer_section_type("Pre-Chorus") == "chorus"
    assert infer_section_type("Intro") == "intro"
    assert infer_section_type("Interlude") == "interlude"
    assert infer_section_type("Outro") == "outro"
    assert infer_section_type("Tag") == "instrumental"
    assert infer_section_type("Instrumental.") == "instrumental"
    assert infer_section_type("Something Else") == "verse"


def test_combine_chord_and_lyric_lines_preserves_chord_positions():
    result = combine_chord_and_lyric_lines("    G      D", "How great is God")

    assert result.text == "How great is God"
    assert result.chords == [
        ChordPosition(chord="G", position=4),
        ChordPosition(chord="D", position=11),
    ]


def test_parse_sections_preserves_instrumental_chord_positions():
    sections = parse_sections_from_content("Intro\nBm      G      D")

    line = sections["Intro"].lines[0]

    assert line.text == "                "
    assert line.chords == [
        ChordPosition(chord="Bm", position=0),
        ChordPosition(chord="G", position=8),
        ChordPosition(chord="D", position=15),
    ]


def test_transpose_chordpro_lines_changes_chords_but_preserves_text_and_positions():
    original = combine_chord_and_lyric_lines("    G      D/F#", "How great is God")

    result = transpose_chordpro_lines([original], from_key="G", to_key="A")

    assert result[0].text == original.text
    assert [chord.position for chord in result[0].chords] == [4, 11]
    assert [chord.chord for chord in result[0].chords] == ["A", "E/G#"]


def test_convert_to_yaml_avoids_double_transposition_when_content_already_in_target_key():
    song_data = {
        "title": "Already Transposed",
        "artist": "Example Artist",
        "content": "Verse 1\n    A      E\nHow great is God",
        "original_key": "G",
        "key": "A",
    }

    result = convert_to_yaml(song_data, target_key="A")

    chords = result.sections["Verse 1"].lines[0].chords
    assert [chord.chord for chord in chords] == ["A", "E"]
