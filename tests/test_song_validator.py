"""Tests for song validator functionality.

Covers Requirements 7.1-7.8 (data validation) and 18.1, 18.2, 18.5 (licensing
warnings) handled by ``src.utils.song_validator``.
"""

import pytest

from src.utils.chordpro_parser import ChordPosition, ChordProLine
from src.utils.song_validator import (
    OverflowWarning,
    ValidationResult,
    check_for_placeholders,
    check_licensing,
    contains_placeholder,
    estimate_slide_overflow,
    is_valid_chord,
    validate_song,
)
from src.utils.yaml_models import SongSection, SongYAML


def _line(text: str, *chords: tuple[str, int]) -> ChordProLine:
    """Helper to build a ChordProLine from (chord, position) tuples."""
    return ChordProLine(
        text=text,
        chords=[ChordPosition(chord=c, position=p) for c, p in chords],
    )


def _section(
    name: str,
    section_type: str = "verse",
    lines: list[ChordProLine] | None = None,
    notes: list[str] | None = None,
) -> SongSection:
    """Helper to construct a SongSection for testing."""
    return SongSection(
        name=name,
        type=section_type,
        lines=lines or [_line("Test lyric line", ("G", 0))],
        notes=notes,
    )


def _song(
    title: str = "Example Song",
    authors: list[str] | None = None,
    target_key: str = "D",
    sections: dict[str, SongSection] | None = None,
    arrangement: list[str] | None = None,
    *,
    ccli_number: str | None = "1234567",
    copyright: str | None = "Test © 2024 Writer",
) -> SongYAML:
    """Build a baseline complete song, with optional overrides."""
    if sections is None:
        sections = {
            "Verse 1": _section("Verse 1", "verse"),
            "Chorus": _section("Chorus", "chorus"),
        }
    if arrangement is None:
        arrangement = list(sections.keys())
    # Distinguish ``authors=None`` (use default) from ``authors=[]`` (test
    # wants an empty list passed through). The ``or`` short-circuit would
    # otherwise replace an explicit empty list with the default.
    authors = ["Test Writer"] if authors is None else authors
    return SongYAML(
        title=title,
        authors=authors,
        target_key=target_key,
        sections=sections,
        arrangement=arrangement,
        ccli_number=ccli_number,
        copyright=copyright,
    )


# ---------------------------------------------------------------------------
# validate_song — Requirement 7.1, 7.2, 7.4, 7.5
# ---------------------------------------------------------------------------


class TestValidateSong:
    """Tests for the top-level validate_song entry point."""

    def test_complete_song_returns_valid(self):
        song = _song()

        result = validate_song(song)

        assert result.is_valid is True
        assert result.errors == []
        # The CCLI reminder is intentionally not emitted here; only on explicit
        # ``check_licensing`` calls (per Requirement 18.5).
        assert result.warnings == []

    def test_missing_arrangement_section_returns_error_7_1(self):
        song = _song()
        song.arrangement = ["Verse 1", "Chorus", "Phantom Section"]

        result = validate_song(song)

        assert result.is_valid is False
        assert any(
            "Phantom Section" in err and "non-existent" in err for err in result.errors
        )

    def test_invalid_chord_returns_error_7_2(self):
        song = _song()
        song.sections["Chorus"] = _section(
            "Chorus",
            "chorus",
            lines=[_line("Bogus chord here", ("Hx", 0))],
        )

        result = validate_song(song)

        assert result.is_valid is False
        assert any("Hx" in err and "Invalid chord" in err for err in result.errors)

    def test_slash_chord_is_valid_7_2(self):
        song = _song()
        song.sections["Chorus"] = _section(
            "Chorus",
            "chorus",
            lines=[_line("Slash chord line", ("C", 0), ("G", 4))],
        )
        song.sections["Chorus"].lines[0].chords.append(
            ChordPosition(chord="D/F#", position=10)
        )

        result = validate_song(song)

        assert result.is_valid is True
        assert result.errors == []

    def test_empty_section_label_returns_error_7_4(self):
        song = _song()
        # Replace the sections dict; one key is whitespace, expected to fail.
        song.sections = {
            "   ": _section("Whitespaced", "verse"),
            "Verse 1": _section("Verse 1", "verse"),
        }
        song.arrangement = ["Verse 1"]

        result = validate_song(song)

        assert result.is_valid is False
        assert any(
            "empty" in err.lower() and "section" in err.lower()
            for err in result.errors
        )

    def test_empty_section_name_property_returns_error_7_4(self):
        song = _song()
        song.sections["Verse 1"] = SongSection(
            name="",
            type="verse",
            lines=[_line("Test line", ("G", 0))],
        )

        result = validate_song(song)

        assert result.is_valid is False
        assert any("Verse 1" in err and "name" in err for err in result.errors)

    def test_missing_title_returns_error_7_5(self):
        song = _song(title="")

        result = validate_song(song)

        assert result.is_valid is False
        assert any("title" in err.lower() for err in result.errors)

    def test_whitespace_only_title_returns_error_7_5(self):
        song = _song(title="   ")

        result = validate_song(song)

        assert result.is_valid is False
        assert any("title" in err.lower() for err in result.errors)

    def test_missing_authors_emits_warning_only_7_5(self):
        song = _song(authors=[])

        result = validate_song(song)

        # Missing authors is a warning, not an error, per Requirement 7.5
        assert result.is_valid is True
        assert any("author" in warn.lower() for warn in result.warnings)

    def test_missing_target_key_emits_warning_only_7_5(self):
        song = _song(target_key="")

        result = validate_song(song)

        assert result.is_valid is True
        assert any("key" in warn.lower() for warn in result.warnings)


# ---------------------------------------------------------------------------
# Placeholder detection — Requirement 7.7, 7.8
# ---------------------------------------------------------------------------


class TestPlaceholderCheck:
    """Tests for explicit placeholder detection (Requirements 7.7, 7.8)."""

    def test_placeholder_check_disabled_by_default_7_8(self):
        song = _song(title="[placeholder Draft]")

        result = validate_song(song, check_placeholders=False)

        # Without check_placeholders, the [placeholder ...] pattern is ignored.
        assert result.errors == []
        assert result.is_valid is True

    def test_placeholder_check_enabled_finds_todo_in_title_7_7(self):
        song = _song(title="TODO Draft")

        result = validate_song(song, check_placeholders=True)

        assert result.is_valid is False
        assert any("placeholder" in err.lower() and "title" in err.lower()
                   for err in result.errors)

    def test_placeholder_check_enabled_finds_tbd_7_7(self):
        song = _song(title="Chorus TBD")

        result = validate_song(song, check_placeholders=True)

        assert result.is_valid is False
        assert any("TBD" in err or "placeholder" in err.lower()
                   for err in result.errors)

    def test_placeholder_check_enabled_finds_xxx_7_7(self):
        song = _song(title="Song name XXX")

        result = validate_song(song, check_placeholders=True)

        assert result.is_valid is False
        assert any("placeholder" in err.lower() for err in result.errors)

    def test_placeholder_check_finds_curly_braces_7_7(self):
        song = _song(title="Intro {value}")

        result = validate_song(song, check_placeholders=True)

        assert result.is_valid is False

    def test_placeholder_check_finds_in_lyric_text_7_7(self):
        song = _song()
        song.sections["Verse 1"] = _section(
            "Verse 1", lines=[_line("This line has TODO in it")]
        )

        result = validate_song(song, check_placeholders=True)

        assert result.is_valid is False
        assert any("Verse 1" in err for err in result.errors)

    def test_placeholder_check_no_placeholders_returns_clean_7_7(self):
        lines = [_line("Just a clean lyric", ("G", 0))]
        song = _song(
            title="Clean Song",
            sections={"Verse 1": _section("Verse 1", lines=lines)},
            arrangement=["Verse 1"],
        )

        result = validate_song(song, check_placeholders=True)

        assert result.is_valid is True
        assert result.errors == []


# ---------------------------------------------------------------------------
# Chord helper
# ---------------------------------------------------------------------------


class TestIsValidChord:
    """Tests for the standalone is_valid_chord helper."""

    def test_empty_chord_returns_false(self):
        assert is_valid_chord("") is False

    def test_whitespace_chord_returns_false(self):
        assert is_valid_chord("   ") is False

    @pytest.mark.parametrize(
        "chord",
        ["G", "A", "B", "C", "D", "E", "F", "Bb", "F#", "C#"],
    )
    def test_basic_chord_is_valid(self, chord):
        assert is_valid_chord(chord) is True

    @pytest.mark.parametrize(
        "chord",
        ["Bm", "Cm", "Dm", "Em", "Am", "Gm"],
    )
    def test_minor_chord_is_valid(self, chord):
        assert is_valid_chord(chord) is True

    @pytest.mark.parametrize(
        "chord",
        ["C/G", "D/F#", "G/B", "Am/E", "Bm/D"],
    )
    def test_slash_chord_is_valid(self, chord):
        assert is_valid_chord(chord) is True

    @pytest.mark.parametrize(
        "chord",
        ["Cmaj7", "Dm7", "Gsus4", "Csus2", "Cadd9", "Ddim", "Eaug"],
    )
    def test_extended_chord_is_valid(self, chord):
        assert is_valid_chord(chord) is True

    @pytest.mark.parametrize(
        "chord",
        # These must NOT match the regex r'^[A-G][b#]?(?:(?:m(?![a-z])|maj|min|dim|aug|sus[24]?|add[0-9]+|[0-9]+|b[0-9]+|#[0-9]+))*(?:/[A-G][b#]?)?$'.
        # Note: ``maj`` is itself an accepted bare modifier (so ``Cmaj`` is
        # valid — covered separately). Likewise ``add`` requires ``add[0-9]+``,
        # so ``Cadd`` is invalid; ``GG`` cannot match ([A-G] is one letter).
        ["H", "X", "123", "GG", "Cadd"],
    )
    def test_invalid_chord_returns_false(self, chord):
        assert is_valid_chord(chord) is False


# ---------------------------------------------------------------------------
# Overflow estimation — Requirement 7.3
# ---------------------------------------------------------------------------


class TestEstimateSlideOverflow:
    """Tests for estimate_slide_overflow (Requirement 7.3)."""

    def test_short_section_in_practice_style_no_warning(self):
        lines = [_line(f"Line {i}", ("G", 0)) for i in range(8)]
        song = _song(
            sections={"Verse 1": _section("Verse 1", "verse", lines=lines)},
            arrangement=["Verse 1"],
        )

        warnings = estimate_slide_overflow(song, "practice")

        # 8 < 12 (practice cap) → no warnings
        assert warnings == []

    def test_section_overflow_in_practice_style_warns_7_3(self):
        lines = [_line(f"Line {i}", ("G", 0)) for i in range(18)]
        song = _song(
            sections={"Verse 1": _section("Verse 1", "verse", lines=lines)},
            arrangement=["Verse 1"],
        )

        warnings = estimate_slide_overflow(song, "practice")

        assert len(warnings) == 1
        warning = warnings[0]
        assert warning.section_name == "Verse 1"
        assert warning.estimated_lines == 18
        assert warning.max_lines == 12
        assert isinstance(warning.suggestion, str)
        assert warning.suggestion  # non-empty

    def test_section_overflow_in_performance_style_warns_7_3(self):
        lines = [_line(f"Line {i}", ("G", 0)) for i in range(20)]
        song = _song(
            sections={"Verse 1": _section("Verse 1", "verse", lines=lines)},
            arrangement=["Verse 1"],
        )

        warnings = estimate_slide_overflow(song, "performance")

        assert len(warnings) == 1
        assert warnings[0].max_lines == 16

    def test_simple_style_has_higher_capacity(self):
        # 14 lines: practice (12) and performance (16) thresholds bracket it.
        lines = [_line(f"Line {i}", ("G", 0)) for i in range(14)]
        song = _song(
            sections={"Verse 1": _section("Verse 1", "verse", lines=lines)},
            arrangement=["Verse 1"],
        )

        # In practice there's still a warning; in simple there isn't.
        assert len(estimate_slide_overflow(song, "practice")) == 1
        assert estimate_slide_overflow(song, "simple") == []

    def test_practice_style_cap(self):
        # The "default" handler expects ``"practice"`` to be the implicit
        # baseline; pin the practice cap explicitly here so a future refactor
        # that flips the default does not silently regress this branch.
        lines = [_line(f"Line {i}", ("G", 0)) for i in range(18)]
        song = _song(
            sections={"Verse 1": _section("Verse 1", "verse", lines=lines)},
            arrangement=["Verse 1"],
        )

        warnings = estimate_slide_overflow(song, "practice")

        assert len(warnings) == 1
        assert warnings[0].max_lines == 12

    def test_invalid_arrangement_reference_skipped(self):
        # Arrangement references a section key that doesn't exist; should be
        # skipped silently (validation is the validator's job, not overflow
        # estimation's).
        lines = [_line(f"Line {i}", ("G", 0)) for i in range(20)]
        song = _song(
            sections={"Verse 1": _section("Verse 1", "verse", lines=lines)},
            arrangement=["Verse 1", "Phantom"],
        )

        # Verse 1 still overflows the practice cap, even if Phantom is skipped.
        warnings = estimate_slide_overflow(song, "performance")
        assert len(warnings) == 1
        assert warnings[0].section_name == "Verse 1"

    def test_overflow_counts_notes_in_total(self):
        # 10 lyric lines + 4 notes above practice cap (12) → overflow by 2.
        lines = [_line(f"Line {i}", ("G", 0)) for i in range(10)]
        song = _song(
            sections={
                "Verse 1": _section(
                    "Verse 1",
                    "verse",
                    lines=lines,
                    notes=["Note A", "Note B", "Note C", "Note D"],
                ),
            },
            arrangement=["Verse 1"],
        )

        warnings = estimate_slide_overflow(song, "practice")

        assert len(warnings) == 1
        assert warnings[0].estimated_lines == 14
        assert warnings[0].max_lines == 12

    @pytest.mark.parametrize(
        "excess,expected_fragment",
        [
            (2, "slightly reducing"),  # small excess
            (5, "splitting"),  # moderate excess
            (8, "strongly recommend"),  # large excess
        ],
    )
    def test_overflow_suggestion_quality(self, excess, expected_fragment):
        # Build a section with (practice cap + excess) lines.
        cap = 12
        target = cap + excess
        lines = [_line(f"Line {i}", ("G", 0)) for i in range(target)]
        song = _song(
            sections={"Verse 1": _section("Verse 1", "verse", lines=lines)},
            arrangement=["Verse 1"],
        )

        warnings = estimate_slide_overflow(song, "practice")

        assert len(warnings) == 1
        assert expected_fragment.lower() in warnings[0].suggestion.lower()

    def test_overflow_warning_dataclass_fields(self):
        lines = [_line(f"Line {i}", ("G", 0)) for i in range(20)]
        song = _song(
            sections={"Verse 1": _section("Verse 1", "verse", lines=lines)},
            arrangement=["Verse 1"],
        )

        warnings = estimate_slide_overflow(song, "performance")

        warning = warnings[0]
        assert isinstance(warning, OverflowWarning)
        assert warning.section_name == "Verse 1"
        assert warning.estimated_lines == 20
        assert warning.max_lines == 16
        assert isinstance(warning.suggestion, str)


# ---------------------------------------------------------------------------
# Licensing — Requirements 7.6, 18.1, 18.2, 18.5
# ---------------------------------------------------------------------------


class TestCheckLicensing:
    """Tests for the check_licensing helper (Requirements 7.6, 18.1, 18.2, 18.5)."""

    def test_missing_ccli_number_warns_18_1(self):
        song = _song(ccli_number=None)

        warnings = check_licensing(song)

        assert any("CCLI" in warn and "missing" in warn.lower() for warn in warnings)

    def test_missing_copyright_warns_18_2(self):
        song = _song(copyright=None)

        warnings = check_licensing(song)

        assert any(
            "copyright" in warn.lower() and "incomplete" in warn.lower()
            for warn in warnings
        )

    def test_reminder_always_emitted_18_5(self):
        song = _song(ccli_number="1234567", copyright="© 2024 Writer")

        warnings = check_licensing(song)

        # The CCLI permission reminder is unconditional, per Requirement 18.5.
        assert any("CCLI permission" in warn for warn in warnings)

    def test_reminder_emitted_even_when_warnings_present(self):
        song = _song(ccli_number=None, copyright=None)

        warnings = check_licensing(song)

        # Both incomplete fields + reminder should be present (3 warnings).
        assert len(warnings) == 3
        assert any("CCLI permission" in warn for warn in warnings)

    def test_whitespace_only_ccli_treated_as_missing(self):
        song = _song(ccli_number="   ")

        warnings = check_licensing(song)

        assert any("CCLI" in warn for warn in warnings)

    def test_whitespace_only_copyright_treated_as_missing(self):
        song = _song(copyright="   ")

        warnings = check_licensing(song)

        assert any("copyright" in warn.lower() for warn in warnings)


# ---------------------------------------------------------------------------
# Placeholder helper
# ---------------------------------------------------------------------------


class TestContainsPlaceholder:
    """Tests for the standalone contains_placeholder helper."""

    def test_empty_string_returns_false(self):
        assert contains_placeholder("") is False

    def test_none_returns_false(self):
        assert contains_placeholder(None) is False

    def test_clean_text_returns_false(self):
        assert contains_placeholder("Just a clean lyric line") is False

    @pytest.mark.parametrize(
        "text",
        ["TODO", "todo", "todo note", "Please TODO this later"],
    )
    def test_todo_pattern_matches(self, text):
        assert contains_placeholder(text) is True

    @pytest.mark.parametrize(
        "text",
        ["TBD", "tbd lyric", "Bridge: TBD"],
    )
    def test_tbd_pattern_matches(self, text):
        assert contains_placeholder(text) is True

    @pytest.mark.parametrize(
        "text",
        ["XXX", "Chorus (xxx)", "intro xxx marker"],
    )
    def test_xxx_pattern_matches(self, text):
        assert contains_placeholder(text) is True

    @pytest.mark.parametrize(
        "text",
        ["{placeholder}", "lyric with {value} in middle"],
    )
    def test_curly_brace_pattern_matches(self, text):
        assert contains_placeholder(text) is True

    def test_square_bracket_placeholder_matches(self):
        assert contains_placeholder("[placeholder text]") is True


# ---------------------------------------------------------------------------
# Helpers exposed by the module
# ---------------------------------------------------------------------------


class TestModuleExports:
    """Smoke tests on the module's public surface."""

    def test_validation_result_is_dataclass(self):
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []

    def test_overflow_warning_is_dataclass(self):
        warning = OverflowWarning(
            section_name="Verse 1",
            estimated_lines=20,
            max_lines=16,
            suggestion="split it",
        )
        assert warning.section_name == "Verse 1"
        assert warning.estimated_lines == 20

    def test_check_for_placeholders_helper_publicly_callable(self):
        # Direct call to the helper, not via validate_song, is part of the
        # supported API surface.
        song = _song(title="TODO Song")

        issues = check_for_placeholders(song)

        assert any("title" in msg.lower() for msg in issues)
