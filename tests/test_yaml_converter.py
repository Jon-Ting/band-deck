"""Tests for converting current search results into structured YAML models."""

import re

from hypothesis import given, settings, strategies as st

from src.utils.chordpro_parser import ChordPosition, ChordProLine
from src.utils.search import (
    CHROMATIC_SCALE_FLATS,
    CHROMATIC_SCALE_SHARPS,
    transpose_chord,
)
from src.utils.yaml_converter import (
    combine_chord_and_lyric_lines,
    convert_to_yaml,
    infer_section_type,
    parse_sections_from_content,
    transpose_chordpro_lines,
)

# Suffixes chosen to avoid ambiguity with root accidentals when combined
# with a natural root (e.g. "C" + "b5" → "Cb5" parses as root "Cb").
_CHORD_SUFFIXES = ["", "m", "7", "maj7", "sus4", "m7", "dim", "add9"]


def test_convert_to_yaml_preserves_metadata_and_prefers_search_name():
    song_data = {
        "title": "Scraped Source Title",
        "search_name": "Congregation Title",
        "artist": "Example Artist",
        "content": "Verse 1\n    G      D\nHow great is God",
        "source_url": "https://example.com/songs/example/",
        "original_key": "G",
        "key": "D",
    }

    result = convert_to_yaml(song_data, target_key="D")

    assert result.title == "Congregation Title"
    assert result.authors == ["Example Artist"]
    assert result.original_key == "G"
    assert result.target_key == "D"
    assert result.source_urls == ["https://example.com/songs/example/"]
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


class TestTranspositionProperties:
    """Property-based tests for chord transposition correctness."""

    # -------------------------------------------------------------------
    # Property 27: Transposition Correctness
    # -------------------------------------------------------------------
    @given(
        use_flats=st.booleans(),
        root_idx=st.integers(min_value=0, max_value=11),
        suffix=st.sampled_from(_CHORD_SUFFIXES),
        semitones=st.integers(min_value=1, max_value=11),
    )
    @settings(deadline=None)
    def test_transpose_by_n_then_back_returns_original(
        self, use_flats, root_idx, suffix, semitones
    ):
        """Transposing by N semitones then by 12-N with the same accidental
        style returns the original chord.

        Validates Requirement 13.1.
        """
        scale = CHROMATIC_SCALE_FLATS if use_flats else CHROMATIC_SCALE_SHARPS
        chord = scale[root_idx] + suffix

        transposed = transpose_chord(chord, semitones, use_flats)
        back = transpose_chord(transposed, 12 - semitones, use_flats)

        assert back == chord, (
            f"Round-trip failed: {chord} → {transposed} → {back}\n"
            f"semitones={semitones}, use_flats={use_flats}"
        )

    # -------------------------------------------------------------------
    # Property 28: Chord Suffix Preservation
    # -------------------------------------------------------------------
    @given(
        use_flats=st.booleans(),
        root_idx=st.integers(min_value=0, max_value=11),
        suffix=st.sampled_from(_CHORD_SUFFIXES),
        semitones=st.integers(min_value=1, max_value=11),
    )
    @settings(deadline=None)
    def test_suffix_preserved_during_transposition(
        self, use_flats, root_idx, suffix, semitones
    ):
        """Chord suffixes (m, 7, maj7, etc.) are preserved when transposing.

        Validates Requirement 13.2.
        """
        scale = CHROMATIC_SCALE_FLATS if use_flats else CHROMATIC_SCALE_SHARPS
        chord = scale[root_idx] + suffix

        transposed = transpose_chord(chord, semitones, use_flats)

        match = re.match(r"^([A-G][b#]?)(.*)$", transposed)
        assert match is not None, f"Could not parse transposed chord: {transposed}"
        _, transposed_suffix = match.groups()

        assert transposed_suffix == suffix, (
            f"Suffix not preserved: {chord} → {transposed}\n"
            f"expected suffix '{suffix}', got '{transposed_suffix}'"
        )

    # -------------------------------------------------------------------
    # Property 29: Slash Chord Transposition
    # -------------------------------------------------------------------
    @given(
        use_flats=st.booleans(),
        root_idx=st.integers(min_value=0, max_value=11),
        suffix=st.sampled_from(_CHORD_SUFFIXES),
        bass_idx=st.integers(min_value=0, max_value=11),
        semitones=st.integers(min_value=1, max_value=11),
    )
    @settings(deadline=None)
    def test_slash_chord_both_parts_transposed(
        self, use_flats, root_idx, suffix, bass_idx, semitones
    ):
        """Slash chords transpose both root and bass note.

        Validates Requirement 13.3.
        """
        scale = CHROMATIC_SCALE_FLATS if use_flats else CHROMATIC_SCALE_SHARPS
        root = scale[root_idx]
        bass = scale[bass_idx]
        chord = f"{root}{suffix}/{bass}"

        transposed = transpose_chord(chord, semitones, use_flats)

        assert "/" in transposed, (
            f"Slash removed during transposition: {chord} → {transposed}"
        )

        root_part, bass_part = transposed.rsplit("/", 1)

        expected_root = transpose_chord(root + suffix, semitones, use_flats)
        assert root_part == expected_root, (
            f"Root part mismatch: expected {expected_root}, got {root_part}\n"
            f"from {chord} with semitones={semitones}"
        )

        expected_bass = transpose_chord(bass, semitones, use_flats)
        assert bass_part == expected_bass, (
            f"Bass mismatch: expected {expected_bass}, got {bass_part}\n"
            f"from {chord} with semitones={semitones}"
        )

    # -------------------------------------------------------------------
    # Property 30: Accidental Consistency
    # -------------------------------------------------------------------
    @given(
        use_flats=st.booleans(),
        root_idx=st.integers(min_value=0, max_value=11),
        suffix=st.sampled_from(_CHORD_SUFFIXES),
        semitones=st.integers(min_value=1, max_value=11),
    )
    @settings(deadline=None)
    def test_accidental_style_is_consistent(
        self, use_flats, root_idx, suffix, semitones
    ):
        """When use_flats=True, results use flat notation; when False, sharp notation.

        Validates Requirement 13.4.
        """
        scale = CHROMATIC_SCALE_FLATS if use_flats else CHROMATIC_SCALE_SHARPS
        chord = scale[root_idx] + suffix

        transposed = transpose_chord(chord, semitones, use_flats)

        match = re.match(r"^([A-G][b#]?)(.*)$", transposed)
        assert match is not None
        transposed_root, _ = match.groups()

        assert transposed_root in scale, (
            f"Accidental style mismatch: {chord} → {transposed}\n"
            f"root '{transposed_root}' not in {'flats' if use_flats else 'sharps'} scale"
        )

    # -------------------------------------------------------------------
    # transpose_chordpro_lines preserves text and positions
    # -------------------------------------------------------------------
    @given(
        text=st.text(
            alphabet=st.characters(blacklist_characters="[]"),
            min_size=0,
            max_size=100,
        ),
        chords=st.lists(
            st.tuples(
                st.sampled_from(CHROMATIC_SCALE_SHARPS + CHROMATIC_SCALE_FLATS),
                st.integers(min_value=0, max_value=100),
            ),
            min_size=0,
            max_size=8,
        ),
        from_key=st.sampled_from(["C", "G", "D", "A", "E", "B", "F", "Bb", "Eb", "Ab"]),
        to_key=st.sampled_from(["C", "G", "D", "A", "E", "B", "F", "Bb", "Eb", "Ab"]),
    )
    @settings(deadline=None)
    def test_transpose_chordpro_lines_preserves_text_and_positions(
        self, text, chords, from_key, to_key
    ):
        """transpose_chordpro_lines preserves lyric text and chord positions.

        Validates Requirements 13.1-13.4 collectively for the ChordProLine level.
        """
        from src.utils.search import get_semitone_shift

        chord_positions = [
            ChordPosition(chord=chord_sym, position=min(pos, len(text)))
            for chord_sym, pos in chords
        ]
        chord_positions.sort(key=lambda c: c.position)

        original_line = ChordProLine(text=text, chords=chord_positions)
        result_lines = transpose_chordpro_lines(
            [original_line], from_key=from_key, to_key=to_key
        )

        assert len(result_lines) == 1
        result = result_lines[0]

        assert result.text == original_line.text, (
            f"Text changed during transposition: '{original_line.text}' → '{result.text}'"
        )

        assert len(result.chords) == len(original_line.chords), (
            f"Chord count changed: {len(original_line.chords)} → {len(result.chords)}"
        )
        for orig, transposed in zip(original_line.chords, result.chords):
            assert orig.position == transposed.position, (
                f"Position changed for chord '{orig.chord}': "
                f"{orig.position} → {transposed.position}"
            )

        if from_key != to_key:
            try:
                semitones = get_semitone_shift(from_key, to_key)
            except Exception:
                semitones = 0

            if semitones != 0:
                for orig, transposed in zip(original_line.chords, result.chords):
                    assert transposed.chord != orig.chord or not any(
                        c in orig.chord for c in "#b"
                    ), (
                        f"Chord not transposed: '{orig.chord}' stayed '{transposed.chord}' "
                        f"for {from_key} → {to_key} ({semitones} semitones)"
                    )
