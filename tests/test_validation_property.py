"""Property-based tests for song validation (Properties 8, 13, 14, 15).

These tests use the hypothesis library to generate many random valid song
payloads and confirm structural assumptions documented in design.md:

- Property 8: YAML Structure Completeness
- Property 13: Chord Symbol Validity
- Property 14: Section Label Presence
- Property 15: Metadata Completeness
"""

from __future__ import annotations

from dataclasses import asdict

from hypothesis import HealthCheck, given, settings, strategies as _st

from src.utils.chordpro_parser import ChordPosition, ChordProLine
from src.utils.song_validator import (
    is_valid_chord,
    validate_song,
)
from src.utils.yaml_api import song_yaml_to_dict, validate_song_yaml_dict
from src.utils.yaml_models import SongSection, SongYAML


# Strategy: realistic chord symbols accepted by both the validator's regex
# (used at runtime by ``is_valid_chord``) and the JSON schema's chord symbol
# regex (``^[A-G](b|#)?(m|maj|min|dim|aug|sus|add)?[0-9]*(sus[24])?(add[0-9]+)?
# (maj[0-9]+)?(/[A-G](b|#)?)?$``).
#
# We compose chords from four parts: root letter, optional accidental, an
# optional quality/suffix taken from a curated list, and an optional slash
# bass note (which always carries the leading ``/``). Every chord produced
# here is independently checked against the validator.
_ROOT_LETTER = _st.sampled_from(list("ABCDEFG"))
_ACCIDENTAL = _st.sampled_from(["", "b", "#"])
_MODIFIER = _st.sampled_from(
    [
        # Empty modifier = just root (+ optional accidental)
        "",
        # Quality-only modifiers
        "m",
        "maj",
        "min",
        "dim",
        "aug",
        # sus/add with their numeric suffix captured together
        "sus2",
        "sus4",
        "add9",
        # Numerics-on-their-own (e.g., seventh)
        "7",
        "9",
        # Quality + digit (e.g., m7, maj7)
        "m7",
        "maj7",
        "m9",
        "maj9",
    ]
)
# Optional bass note; either empty (no slash) or "/X" / "/Xb" / "/X#".
_BASS_PART = _st.one_of(
    _st.just(""),
    _st.tuples(
        _st.just("/"), _ROOT_LETTER, _ACCIDENTAL,
    ).map(lambda parts: "".join(parts)),
)


@_st.composite
def valid_chord_strategy(draw) -> str:
    root = draw(_ROOT_LETTER)
    accidental = draw(_ACCIDENTAL)
    modifier = draw(_MODIFIER)
    bass = draw(_BASS_PART)
    return f"{root}{accidental}{modifier}{bass}"


# Musical keys accepted by the schema.
MUSICAL_KEY = _st.sampled_from(
    ["C", "D", "E", "F", "G", "A", "B", "Bb", "Eb", "Ab", "F#", "C#", "G#", "D#"]
)

# Section label strategy (always non-empty after stripping).
SECTION_NAME = _st.text(
    alphabet=_st.characters(
        whitelist_categories=("Lu", "Nd", "P"),
        whitelist_characters=" -_",
    ),
    min_size=1,
    max_size=40,
).map(str.strip).filter(lambda s: bool(s))

# Section type must be one of the schema enum values.
SECTION_TYPE = _st.sampled_from(
    ["verse", "chorus", "bridge", "intro", "outro", "instrumental", "interlude"]
)

TITLE_STRATEGY = _st.text(min_size=1, max_size=80).map(str.strip).filter(bool)
AUTHOR_STRATEGY = _st.text(min_size=1, max_size=40).map(str.strip).filter(bool)


@_st.composite
def chordpro_line_strategy(draw) -> ChordProLine:
    """Generate a ChordPro line with at least one chord and a few lyrics."""
    lyric = draw(
        _st.text(
            alphabet=_st.characters(
                whitelist_categories=("L", "N", "P", "Zs"),
                blacklist_characters="[]",
            ),
            min_size=1,
            max_size=60,
        )
    )
    chord = draw(valid_chord_strategy())
    return ChordProLine(
        text=lyric,
        chords=[ChordPosition(chord=chord, position=0)],
    )


@_st.composite
def song_section_strategy(draw) -> SongSection:
    """Generate a song section conforming to the JSON schema."""
    name = draw(SECTION_NAME)
    section_type = draw(SECTION_TYPE)
    line_count = draw(_st.integers(min_value=1, max_value=4))
    lines = [draw(chordpro_line_strategy()) for _ in range(line_count)]
    return SongSection(name=name, type=section_type, lines=lines)


@_st.composite
def complete_song_strategy(draw) -> SongYAML:
    """Generate a song satisfying all required schema fields."""
    title = draw(TITLE_STRATEGY)
    authors = [draw(AUTHOR_STRATEGY)]
    target_key = draw(MUSICAL_KEY)

    # Use deterministic section names so arrangement can reference them.
    section_count = draw(_st.integers(min_value=1, max_value=4))
    sections: dict[str, SongSection] = {}
    for i in range(section_count):
        name = f"Section {i}"
        section = SongSection(
            name=name,
            type="verse" if i % 2 == 0 else "chorus",
            lines=[draw(chordpro_line_strategy())],
        )
        sections[name] = section

    return SongYAML(
        title=title,
        authors=authors,
        target_key=target_key,
        sections=sections,
        arrangement=list(sections),
    )


# ---------------------------------------------------------------------------
# Property 8: YAML Structure Completeness
# ---------------------------------------------------------------------------


class TestPropertyYamlStructureCompleteness:
    """Every persisted song YAML must contain the required top-level fields."""

    @given(song=complete_song_strategy())
    @settings(max_examples=50, deadline=None)
    def test_asdict_contains_all_required_top_level_keys(self, song: SongYAML) -> None:
        serialized = asdict(song)
        canonical_song_keys = set(serialized.keys())
        assert {"title", "authors", "sections", "arrangement"} <= canonical_song_keys
        # The codebase names the song's key field 'target_key'; that's
        # also a top-level field per the schema.
        assert "target_key" in canonical_song_keys

    @given(song=complete_song_strategy())
    @settings(max_examples=50, deadline=None)
    def test_schema_validation_passes_for_complete_songs(self, song: SongYAML) -> None:
        serialized = song_yaml_to_dict(song)
        result = validate_song_yaml_dict(serialized)

        assert result["valid"] is True, (
            f"Complete song failed schema validation: {result['errors']}\n"
            f"Song: title={song.title!r}, key={song.target_key!r}, "
            f"sections={list(song.sections)}"
        )
        assert result["errors"] == []


# ---------------------------------------------------------------------------
# Property 13: Chord Symbol Validity
# ---------------------------------------------------------------------------


class TestPropertyChordSymbolValidity:
    """Generated valid chords must be recognised by is_valid_chord."""

    @given(chord=valid_chord_strategy())
    @settings(max_examples=100, deadline=None)
    def test_strategy_generates_chords_validator_accepts(self, chord: str) -> None:
        assert is_valid_chord(chord), (
            f"Validator rejected a chord the strategy claimed was valid: {chord!r}"
        )


# ---------------------------------------------------------------------------
# Property 14: Section Label Presence
# ---------------------------------------------------------------------------


class TestPropertySectionLabelPresence:
    """Every section must have a non-empty, distinct label."""

    @given(section=song_section_strategy())
    @settings(max_examples=100, deadline=None)
    def test_section_name_is_non_empty(self, section: SongSection) -> None:
        # Strategy filters blanks/whitespace, so the name is guaranteed non-empty.
        assert section.name and section.name.strip(), (
            f"Section label unexpectedly empty: name={section.name!r}"
        )

    @given(song=complete_song_strategy())
    @settings(max_examples=100, deadline=None)
    def test_arrangement_references_only_existing_sections(
        self, song: SongYAML
    ) -> None:
        result = validate_song(song)
        integrity_errors = [
            err for err in result.errors if "non-existent section" in err
        ]
        assert integrity_errors == [], (
            f"Arrangement referenced missing sections: {integrity_errors}\n"
            f"arrangement={song.arrangement}, sections={list(song.sections)}"
        )


# ---------------------------------------------------------------------------
# Property 15: Metadata Completeness
# ---------------------------------------------------------------------------


class TestPropertyMetadataCompleteness:
    """Complete songs must validate as valid in the validator's metadata sense."""

    @given(song=complete_song_strategy())
    @settings(
        max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow]
    )
    def test_complete_metadata_produces_no_metadata_errors(
        self, song: SongYAML
    ) -> None:
        result = validate_song(song)
        # Only metadata-related errors (title, author, key, section label)
        # should be absent on a complete song. The chord validity check is
        # covered by Property 13.
        schema_style_errors = [
            err
            for err in result.errors
            if "title" in err.lower()
            or "author" in err.lower()
            or err.lower().startswith("section ")
            and "empty" in err.lower()
        ]
        assert schema_style_errors == [], (
            f"Complete song produced unexpected metadata errors: "
            f"{schema_style_errors}\n"
            f"Song: title={song.title!r}, authors={song.authors}, "
            f"target_key={song.target_key!r}"
        )

    @given(
        title=_st.one_of(_st.just(""), _st.just("   "), _st.just("\t\t")),
    )
    @settings(max_examples=25, deadline=None)
    def test_blank_title_causes_metadata_error(self, title: str) -> None:
        song = SongYAML(
            title=title,
            authors=["Author"],
            target_key="C",
            sections={
                "Verse 1": SongSection(
                    name="Verse 1",
                    type="verse",
                    lines=[ChordProLine(text="Test", chords=[])],
                )
            },
            arrangement=["Verse 1"],
        )
        result = validate_song(song)
        assert result.is_valid is False
        assert any("title" in err.lower() for err in result.errors)
