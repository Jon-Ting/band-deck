"""Tests for arrangement engine functionality."""

import string

import pytest
from hypothesis import given, settings, strategies as st

from src.utils.arrangement_engine import (
    ArrangementEdit,
    propose_arrangement,
    update_arrangement,
    validate_arrangement,
)
from src.utils.chordpro_parser import ChordProLine, ChordPosition
from src.utils.yaml_models import SongSection


def create_test_section(name: str, section_type: str) -> SongSection:
    """Helper to create a test section."""
    return SongSection(
        name=name,
        type=section_type,
        lines=[
            ChordProLine(
                text="Test lyric line",
                chords=[ChordPosition(chord="G", position=0)],
            )
        ],
    )


class TestProposeArrangement:
    """Tests for propose_arrangement function."""

    def test_propose_simple_verse_chorus(self):
        """Test arrangement proposal with verses and chorus."""
        sections = {
            "Verse 1": create_test_section("Verse 1", "verse"),
            "Verse 2": create_test_section("Verse 2", "verse"),
            "Chorus": create_test_section("Chorus", "chorus"),
        }

        result = propose_arrangement(sections)

        # Should alternate verses with chorus
        assert result == ["Verse 1", "Chorus", "Verse 2", "Chorus", "Chorus"]

    def test_propose_with_intro_and_outro(self):
        """Test arrangement proposal with intro and outro sections."""
        sections = {
            "Intro": create_test_section("Intro", "intro"),
            "Verse 1": create_test_section("Verse 1", "verse"),
            "Chorus": create_test_section("Chorus", "chorus"),
            "Outro": create_test_section("Outro", "outro"),
        }

        result = propose_arrangement(sections)

        # Intro first, outro last
        assert result[0] == "Intro"
        assert result[-1] == "Outro"
        assert "Verse 1" in result
        assert "Chorus" in result

    def test_propose_with_bridge(self):
        """Test arrangement proposal including bridge section."""
        sections = {
            "Verse 1": create_test_section("Verse 1", "verse"),
            "Chorus": create_test_section("Chorus", "chorus"),
            "Bridge": create_test_section("Bridge", "bridge"),
        }

        result = propose_arrangement(sections)

        # Bridge should come after verses, followed by chorus
        bridge_idx = result.index("Bridge")
        verse_idx = result.index("Verse 1")
        assert bridge_idx > verse_idx
        # Chorus should appear after bridge
        chorus_after_bridge = result[bridge_idx + 1]
        assert chorus_after_bridge == "Chorus"

    def test_propose_verses_numerical_order(self):
        """Test that verses are ordered numerically."""
        sections = {
            "Verse 3": create_test_section("Verse 3", "verse"),
            "Verse 1": create_test_section("Verse 1", "verse"),
            "Verse 2": create_test_section("Verse 2", "verse"),
        }

        result = propose_arrangement(sections)

        # Find verse positions
        v1_idx = result.index("Verse 1")
        v2_idx = result.index("Verse 2")
        v3_idx = result.index("Verse 3")

        assert v1_idx < v2_idx < v3_idx

    def test_propose_no_chorus(self):
        """Test arrangement proposal without chorus."""
        sections = {
            "Verse 1": create_test_section("Verse 1", "verse"),
            "Verse 2": create_test_section("Verse 2", "verse"),
        }

        result = propose_arrangement(sections)

        # Should just list verses in order
        assert result == ["Verse 1", "Verse 2"]

    def test_propose_empty_sections(self):
        """Test arrangement proposal with no sections."""
        sections = {}

        result = propose_arrangement(sections)

        assert result == []

    def test_propose_instrumental_intro(self):
        """Test that instrumental intro sections are recognized."""
        sections = {
            "IntroTurn": create_test_section("IntroTurn", "instrumental"),
            "Verse 1": create_test_section("Verse 1", "verse"),
        }

        result = propose_arrangement(sections)

        # Instrumental intro should come first
        assert result[0] == "IntroTurn"

    def test_propose_intro_without_intro_substring_in_name(self):
        """Regression: a section with type='intro' but a non-'intro' name is still an intro.

        Locks in the fix for the dual-condition heuristic that previously required
        both type='intro' AND 'intro' in name.lower(), which dropped sections like
        'Opening' (type='intro') into the 'other' bucket.
        """
        sections = {
            "Opening": create_test_section("Opening", "intro"),
            "Verse 1": create_test_section("Verse 1", "verse"),
        }

        result = propose_arrangement(sections)

        # Opening must be classified as an intro (first position), not in 'other'
        assert result[0] == "Opening"

    def test_propose_interlude(self):
        """Test that interlude sections are included."""
        sections = {
            "Verse 1": create_test_section("Verse 1", "verse"),
            "Interlude": create_test_section("Interlude", "interlude"),
        }

        result = propose_arrangement(sections)

        assert "Interlude" in result


class TestValidateArrangement:
    """Tests for validate_arrangement function."""

    def test_validate_valid_arrangement(self):
        """Test validation passes for valid arrangement."""
        sections = {
            "Verse 1": create_test_section("Verse 1", "verse"),
            "Chorus": create_test_section("Chorus", "chorus"),
        }
        arrangement = ["Verse 1", "Chorus", "Chorus"]

        is_valid, errors = validate_arrangement(arrangement, sections)

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_missing_section(self):
        """Test validation fails for non-existent section reference."""
        sections = {
            "Verse 1": create_test_section("Verse 1", "verse"),
        }
        arrangement = ["Verse 1", "Chorus"]

        is_valid, errors = validate_arrangement(arrangement, sections)

        assert is_valid is False
        assert len(errors) == 1
        assert "Chorus" in errors[0]
        assert "non-existent" in errors[0]

    def test_validate_multiple_missing_sections(self):
        """Test validation reports all missing sections."""
        sections = {
            "Verse 1": create_test_section("Verse 1", "verse"),
        }
        arrangement = ["Verse 1", "Chorus", "Bridge", "Verse 1"]

        is_valid, errors = validate_arrangement(arrangement, sections)

        assert is_valid is False
        assert len(errors) == 2
        assert any("Chorus" in err for err in errors)
        assert any("Bridge" in err for err in errors)

    def test_validate_empty_arrangement(self):
        """Test validation passes for empty arrangement."""
        sections = {
            "Verse 1": create_test_section("Verse 1", "verse"),
        }
        arrangement = []

        is_valid, errors = validate_arrangement(arrangement, sections)

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_repeated_sections_valid(self):
        """Test validation passes when section is repeated."""
        sections = {
            "Chorus": create_test_section("Chorus", "chorus"),
        }
        arrangement = ["Chorus", "Chorus", "Chorus"]

        is_valid, errors = validate_arrangement(arrangement, sections)

        assert is_valid is True
        assert len(errors) == 0


class TestUpdateArrangement:
    """Tests for update_arrangement function."""

    def test_reorder_move_section(self):
        """Test reorder operation moves section to target position."""
        current = ["Verse 1", "Verse 2", "Chorus"]
        modification = ArrangementEdit(
            operation="reorder", section_name="Chorus", target_position=1
        )

        result = update_arrangement(current, modification)

        assert result == ["Verse 1", "Chorus", "Verse 2"]

    def test_reorder_missing_target_position(self):
        """Test reorder fails without target_position."""
        current = ["Verse 1", "Chorus"]
        modification = ArrangementEdit(operation="reorder", section_name="Chorus")

        with pytest.raises(ValueError, match="requires target_position"):
            update_arrangement(current, modification)

    def test_reorder_nonexistent_section(self):
        """Test reorder fails for section not in arrangement."""
        current = ["Verse 1", "Chorus"]
        modification = ArrangementEdit(
            operation="reorder", section_name="Bridge", target_position=0
        )

        with pytest.raises(ValueError, match="not found"):
            update_arrangement(current, modification)

    def test_repeat_default_position(self):
        """Test repeat operation with default position (after current)."""
        current = ["Verse 1", "Chorus", "Verse 2"]
        modification = ArrangementEdit(operation="repeat", section_name="Chorus")

        result = update_arrangement(current, modification)

        # Should insert after current position (index 1 -> insert at 2)
        assert result == ["Verse 1", "Chorus", "Chorus", "Verse 2"]

    def test_repeat_with_target_position(self):
        """Test repeat operation with explicit target position."""
        current = ["Verse 1", "Chorus", "Verse 2"]
        modification = ArrangementEdit(
            operation="repeat", section_name="Chorus", target_position=3
        )

        result = update_arrangement(current, modification)

        assert result == ["Verse 1", "Chorus", "Verse 2", "Chorus"]

    def test_repeat_multiple_times(self):
        """Test repeat operation with repeat_count."""
        current = ["Verse 1", "Chorus"]
        modification = ArrangementEdit(
            operation="repeat",
            section_name="Chorus",
            target_position=2,
            repeat_count=2,
        )

        result = update_arrangement(current, modification)

        assert result == ["Verse 1", "Chorus", "Chorus", "Chorus"]

    def test_repeat_nonexistent_section(self):
        """Test repeat fails for section not in arrangement."""
        current = ["Verse 1", "Chorus"]
        modification = ArrangementEdit(operation="repeat", section_name="Bridge")

        with pytest.raises(ValueError, match="not found"):
            update_arrangement(current, modification)

    def test_insert_section(self):
        """Test insert operation adds section at position."""
        current = ["Verse 1", "Verse 2"]
        modification = ArrangementEdit(
            operation="insert", section_name="Chorus", target_position=1
        )

        result = update_arrangement(current, modification)

        assert result == ["Verse 1", "Chorus", "Verse 2"]

    def test_insert_missing_target_position(self):
        """Test insert fails without target_position."""
        current = ["Verse 1"]
        modification = ArrangementEdit(operation="insert", section_name="Chorus")

        with pytest.raises(ValueError, match="requires target_position"):
            update_arrangement(current, modification)

    def test_insert_at_end(self):
        """Test insert at end of arrangement."""
        current = ["Verse 1"]
        modification = ArrangementEdit(
            operation="insert", section_name="Chorus", target_position=10
        )

        result = update_arrangement(current, modification)

        # Should clamp to valid position
        assert result == ["Verse 1", "Chorus"]

    def test_delete_section(self):
        """Test delete operation removes first occurrence."""
        current = ["Verse 1", "Chorus", "Verse 2", "Chorus"]
        modification = ArrangementEdit(operation="delete", section_name="Chorus")

        result = update_arrangement(current, modification)

        # Should remove first Chorus only
        assert result == ["Verse 1", "Verse 2", "Chorus"]

    def test_delete_nonexistent_section(self):
        """Test delete fails for section not in arrangement."""
        current = ["Verse 1", "Chorus"]
        modification = ArrangementEdit(operation="delete", section_name="Bridge")

        with pytest.raises(ValueError, match="not found"):
            update_arrangement(current, modification)

    def test_repeat_with_zero_count_raises_value_error(self):
        """repeat_count of 0 should raise (not silently insert nothing)."""
        current = ["Verse 1", "Chorus"]
        modification = ArrangementEdit(
            operation="repeat", section_name="Chorus", repeat_count=0
        )
        with pytest.raises(ValueError, match="repeat_count must be a positive integer"):
            update_arrangement(current, modification)

    def test_repeat_with_negative_count_raises_value_error(self):
        """Negative repeat_count should raise ValueError."""
        current = ["Verse 1", "Chorus"]
        modification = ArrangementEdit(
            operation="repeat", section_name="Chorus", repeat_count=-2
        )
        with pytest.raises(ValueError, match="repeat_count must be a positive integer"):
            update_arrangement(current, modification)

    def test_invalid_operation(self):
        """Test invalid operation raises error."""
        current = ["Verse 1"]
        modification = ArrangementEdit(operation="invalid_op", section_name="Verse 1")

        with pytest.raises(ValueError, match="Unknown operation"):
            update_arrangement(current, modification)

    def test_update_does_not_mutate_input(self):
        """Test that update_arrangement doesn't modify the input list."""
        original = ["Verse 1", "Chorus"]
        current = original.copy()
        modification = ArrangementEdit(
            operation="insert", section_name="Bridge", target_position=1
        )

        result = update_arrangement(current, modification)

        # Original should be unchanged
        assert current == original
        assert result != current


# ---------------------------------------------------------------------------
# Property 12: Arrangement Referential Integrity
# ---------------------------------------------------------------------------

# Section names are non-empty strings; avoid whitespace-only edge cases by
# filtering on ``strip()`` after the draw.
_SECTION_NAME_CHARS = string.ascii_letters + string.digits + " _-"
section_name_strategy = st.text(
    alphabet=_SECTION_NAME_CHARS, min_size=1, max_size=20
).filter(lambda s: s.strip())


@st.composite
def sections_dict_strategy(draw) -> dict[str, SongSection]:
    """Build a sections dict whose keys are a unique set of drawn names.

    ``validate_arrangement`` only inspects the keys of this dict; the
    ``SongSection`` values are placeholders, intentionally using a fixed
    ``type="verse"`` because the function never reads the type/lines fields.
    """
    keys = draw(st.sets(section_name_strategy, min_size=0, max_size=12))
    return {
        name: SongSection(name=name, type="verse", lines=[])
        for name in keys
    }


class TestArrangementReferentialIntegrity:
    """Property 12: Arrangement Referential Integrity.

    For any sections dict + arrangement, ``validate_arrangement`` returns
    ``is_valid=True`` (with an empty error list) iff every arrangement entry
    is a key in the sections dict. Conversely, when any arrangement entry
    does not reference an existing section, the function reports an error for
    each such occurrence and returns ``is_valid=False``.

    The first test is a hypothesis property test that exercises 100 random
    examples; the remaining three are written as readable documentation of
    specific edge-case behavior, not for additional coverage (which the
    property test already provides).
    """

    @given(
        sections=sections_dict_strategy(),
        arrangement=st.lists(section_name_strategy, min_size=0, max_size=20),
    )
    @settings(deadline=None, max_examples=100)
    def test_validate_arrangement_reports_integrity_correctly(
        self, sections: dict[str, SongSection], arrangement: list[str]
    ) -> None:
        """``is_valid`` matches referential integrity; errors list mirrors
        each missing arrangement entry, in arrival order, with the position
        index embedded in the message.
        """
        is_valid, errors = validate_arrangement(arrangement, sections)

        section_names = set(sections.keys())
        # Track each missing reference with its *arrangement* position. Note:
        # ``errors`` is sequentially indexed (errors[k] is the kth emitted
        # error), NOT indexed by arrangement position, so we cannot assume
        # ``errors[arrangement_pos]`` corresponds to that position. The
        # embedded ``position {N}`` field in each message is the contract.
        missing_entries = [
            (idx, name)
            for idx, name in enumerate(arrangement)
            if name not in section_names
        ]

        if not missing_entries:
            assert is_valid is True
            assert errors == []
            return

        assert is_valid is False
        assert len(errors) == len(missing_entries)
        for arrangement_idx, missing_name in missing_entries:
            # Strict prefix match binds the assertion to the documented
            # message format (``Arrangement item at position {N} references
            # non-existent section '{name}'``). Substring match would falsely
            # pass if a section name accidentally contains "position N" or
            # the failure phrase, so we anchor on the leading prefix instead.
            prefix = f"Arrangement item at position {arrangement_idx}"
            matching = [
                err for err in errors
                if err.startswith(prefix) and missing_name in err
            ]
            assert matching, (
                f"Expected an error starting with {prefix!r} and mentioning "
                f"{missing_name!r} in {errors!r}"
            )

    def test_validate_arrangement_reports_each_missing_occurrence(self) -> None:
        """Documentation: duplicate references to a missing section produce
        duplicate errors (one per occurrence); the implementation iterates by
        position rather than by unique name.
        """
        missing = "PhantomSection"
        arrangement = [missing, missing]
        sections = {
            "RealSection": SongSection(
                name="RealSection", type="verse", lines=[]
            )
        }

        is_valid, errors = validate_arrangement(arrangement, sections)

        assert is_valid is False
        assert len(errors) == 2
        assert all(missing in err for err in errors)
        # Errors preserve arrival order so the position index increases.
        assert "0" in errors[0]
        assert "1" in errors[1]

    def test_validate_empty_arrangement_with_empty_sections_is_valid(self):
        """Documentation: both inputs empty still passes (vacuous truth)."""
        is_valid, errors = validate_arrangement([], {})
        assert is_valid is True
        assert errors == []

    def test_validate_arrangement_all_missing_when_sections_empty(self):
        """Documentation: non-empty arrangement against empty sections flags
        every entry, with errors emitted in arrival order.
        """
        arrangement = ["A", "B", "C"]
        is_valid, errors = validate_arrangement(arrangement, {})

        assert is_valid is False
        assert len(errors) == len(arrangement)
        # When every arrangement entry is missing, the errors list aligns 1:1
        # with arrangement positions, so we can use direct positional checks.
        for position, name in enumerate(arrangement):
            assert name in errors[position]
            assert f"Arrangement item at position {position}" in errors[position]
