"""Tests for ChordPro parser module."""

import string

from hypothesis import given, settings, strategies as st

from src.utils.chordpro_parser import (
    ChordPosition,
    ChordProLine,
    Token,
    TokenType,
    calculate_positions,
    parse_chordpro,
    reconstruct_brackets,
    tokenize_chordpro,
)


class TestTokenizeChordpro:
    """Tests for tokenize_chordpro function."""

    def test_simple_chord_and_text(self):
        """Parse basic chord with text."""
        result = tokenize_chordpro("Who [Bm]else")

        assert len(result) == 3
        assert result[0] == Token(TokenType.TEXT, "Who ")
        assert result[1] == Token(TokenType.CHORD, "Bm")
        assert result[2] == Token(TokenType.TEXT, "else")

    def test_multiple_chords(self):
        """Parse line with multiple chords."""
        result = tokenize_chordpro("Who [Bm]else commands the [G]time")

        assert len(result) == 5
        assert result[0] == Token(TokenType.TEXT, "Who ")
        assert result[1] == Token(TokenType.CHORD, "Bm")
        assert result[2] == Token(TokenType.TEXT, "else commands the ")
        assert result[3] == Token(TokenType.CHORD, "G")
        assert result[4] == Token(TokenType.TEXT, "time")

    def test_chord_at_start(self):
        """Parse line starting with a chord."""
        result = tokenize_chordpro("[G]Amazing grace")

        assert len(result) == 2
        assert result[0] == Token(TokenType.CHORD, "G")
        assert result[1] == Token(TokenType.TEXT, "Amazing grace")

    def test_chord_at_end(self):
        """Parse line ending with a chord."""
        result = tokenize_chordpro("Amazing grace [G]")

        assert len(result) == 2
        assert result[0] == Token(TokenType.TEXT, "Amazing grace ")
        assert result[1] == Token(TokenType.CHORD, "G")

    def test_only_chords(self):
        """Parse line with only chords (instrumental)."""
        result = tokenize_chordpro("[Bm]      [G]      [D]")

        assert len(result) == 5
        assert result[0] == Token(TokenType.CHORD, "Bm")
        assert result[1] == Token(TokenType.TEXT, "      ")
        assert result[2] == Token(TokenType.CHORD, "G")
        assert result[3] == Token(TokenType.TEXT, "      ")
        assert result[4] == Token(TokenType.CHORD, "D")

    def test_no_chords(self):
        """Parse line with no chords."""
        result = tokenize_chordpro("Just plain text")

        assert len(result) == 1
        assert result[0] == Token(TokenType.TEXT, "Just plain text")

    def test_empty_line(self):
        """Parse empty line."""
        result = tokenize_chordpro("")

        assert len(result) == 0

    def test_slash_chord(self):
        """Parse slash chord notation."""
        result = tokenize_chordpro("[D/F#]grace")

        assert len(result) == 2
        assert result[0] == Token(TokenType.CHORD, "D/F#")
        assert result[1] == Token(TokenType.TEXT, "grace")

    def test_complex_chord_symbols(self):
        """Parse various chord suffix notations."""
        result = tokenize_chordpro("[Cmaj7]test [Am7b5]here [Dsus4]now")

        assert result[0] == Token(TokenType.CHORD, "Cmaj7")
        assert result[2] == Token(TokenType.CHORD, "Am7b5")
        assert result[4] == Token(TokenType.CHORD, "Dsus4")


class TestCalculatePositions:
    """Tests for calculate_positions function."""

    def test_single_chord_mid_text(self):
        """Calculate position for one chord in middle of text."""
        tokens = [
            Token(TokenType.TEXT, "Who "),
            Token(TokenType.CHORD, "Bm"),
            Token(TokenType.TEXT, "else"),
        ]

        result = calculate_positions(tokens)

        assert result.text == "Who else"
        assert len(result.chords) == 1
        assert result.chords[0] == ChordPosition(chord="Bm", position=4)

    def test_multiple_chords(self):
        """Calculate positions for multiple chords."""
        tokens = [
            Token(TokenType.TEXT, "Who "),
            Token(TokenType.CHORD, "Bm"),
            Token(TokenType.TEXT, "else commands the "),
            Token(TokenType.CHORD, "G"),
            Token(TokenType.TEXT, "time"),
        ]

        result = calculate_positions(tokens)

        assert result.text == "Who else commands the time"
        assert len(result.chords) == 2
        assert result.chords[0] == ChordPosition(chord="Bm", position=4)
        assert result.chords[1] == ChordPosition(chord="G", position=22)

    def test_chord_at_position_zero(self):
        """Calculate position for chord at start."""
        tokens = [Token(TokenType.CHORD, "G"), Token(TokenType.TEXT, "Amazing")]

        result = calculate_positions(tokens)

        assert result.text == "Amazing"
        assert result.chords[0] == ChordPosition(chord="G", position=0)

    def test_chord_at_end(self):
        """Calculate position for chord at end of text."""
        tokens = [Token(TokenType.TEXT, "Amazing grace "), Token(TokenType.CHORD, "G")]

        result = calculate_positions(tokens)

        assert result.text == "Amazing grace "
        assert result.chords[0] == ChordPosition(chord="G", position=14)

    def test_no_chords(self):
        """Handle text-only line."""
        tokens = [Token(TokenType.TEXT, "Just text")]

        result = calculate_positions(tokens)

        assert result.text == "Just text"
        assert len(result.chords) == 0

    def test_only_chords(self):
        """Handle chord-only line (instrumental)."""
        tokens = [
            Token(TokenType.CHORD, "Bm"),
            Token(TokenType.TEXT, "      "),
            Token(TokenType.CHORD, "G"),
        ]

        result = calculate_positions(tokens)

        assert result.text == "      "
        assert len(result.chords) == 2
        assert result.chords[0] == ChordPosition(chord="Bm", position=0)
        assert result.chords[1] == ChordPosition(chord="G", position=6)

    def test_empty_tokens(self):
        """Handle empty token list."""
        result = calculate_positions([])

        assert result.text == ""
        assert len(result.chords) == 0


class TestParseChordpro:
    """Tests for parse_chordpro main entry point."""

    def test_complete_parsing_simple(self):
        """End-to-end parse of simple line."""
        result = parse_chordpro("Who [Bm]else")

        assert result.text == "Who else"
        assert len(result.chords) == 1
        assert result.chords[0].chord == "Bm"
        assert result.chords[0].position == 4

    def test_complete_parsing_complex(self):
        """End-to-end parse of complex line with multiple chords."""
        result = parse_chordpro("Who [Bm]else commands the [G]time with His [D]hand?")

        assert result.text == "Who else commands the time with His hand?"
        assert len(result.chords) == 3
        assert result.chords[0] == ChordPosition(chord="Bm", position=4)
        assert result.chords[1] == ChordPosition(chord="G", position=22)
        assert result.chords[2] == ChordPosition(chord="D", position=36)

    def test_complete_parsing_slash_chords(self):
        """End-to-end parse with slash chord notation."""
        result = parse_chordpro("[G]Amazing [D/F#]grace how [Em]sweet")

        assert result.text == "Amazing grace how sweet"
        assert len(result.chords) == 3
        assert result.chords[0].chord == "G"
        assert result.chords[1].chord == "D/F#"
        assert result.chords[2].chord == "Em"

    def test_complete_parsing_instrumental(self):
        """End-to-end parse of instrumental line."""
        result = parse_chordpro("[Bm]      [G]      [D]      [A]")

        assert result.text == "                  "
        assert len(result.chords) == 4
        assert result.chords[0] == ChordPosition(chord="Bm", position=0)
        assert result.chords[1] == ChordPosition(chord="G", position=6)
        assert result.chords[2] == ChordPosition(chord="D", position=12)
        assert result.chords[3] == ChordPosition(chord="A", position=18)

    def test_complete_parsing_no_chords(self):
        """End-to-end parse of text-only line."""
        result = parse_chordpro("Just plain lyrics")

        assert result.text == "Just plain lyrics"
        assert len(result.chords) == 0

    def test_complete_parsing_empty(self):
        """End-to-end parse of empty line."""
        result = parse_chordpro("")

        assert result.text == ""
        assert len(result.chords) == 0

    def test_real_world_example_verse(self):
        """Parse actual verse line from Only A Holy God."""
        result = parse_chordpro("Who [Bm]else but [G]O - [A]nly our [D]God?")

        assert result.text == "Who else but O - nly our God?"
        assert len(result.chords) == 4
        assert result.chords[0] == ChordPosition(chord="Bm", position=4)
        assert result.chords[1] == ChordPosition(chord="G", position=13)
        assert result.chords[2] == ChordPosition(chord="A", position=17)
        assert result.chords[3] == ChordPosition(chord="D", position=25)

    def test_real_world_example_chorus(self):
        """Parse actual chorus line from Only A Holy God."""
        result = parse_chordpro("Come and [Bm]behold [G]Him")

        assert result.text == "Come and behold Him"
        assert len(result.chords) == 2
        assert result.chords[0] == ChordPosition(chord="Bm", position=9)
        assert result.chords[1] == ChordPosition(chord="G", position=16)



class TestReconstructBrackets:
    """Tests for reconstruct_brackets function."""

    def test_simple_reconstruction(self):
        """Reconstruct simple ChordPro line."""
        from src.utils.chordpro_parser import ChordProLine, reconstruct_brackets

        line = ChordProLine(text="Who else", chords=[ChordPosition("Bm", 4)])
        result = reconstruct_brackets(line)

        assert result == "Who [Bm]else"

    def test_multiple_chords_reconstruction(self):
        """Reconstruct line with multiple chords."""
        from src.utils.chordpro_parser import ChordProLine, reconstruct_brackets

        line = ChordProLine(
            text="Who else commands the time",
            chords=[ChordPosition("Bm", 4), ChordPosition("G", 22)],
        )
        result = reconstruct_brackets(line)

        assert result == "Who [Bm]else commands the [G]time"

    def test_chord_at_start_reconstruction(self):
        """Reconstruct line with chord at position 0."""
        from src.utils.chordpro_parser import ChordProLine, reconstruct_brackets

        line = ChordProLine(text="Amazing grace", chords=[ChordPosition("G", 0)])
        result = reconstruct_brackets(line)

        assert result == "[G]Amazing grace"

    def test_chord_at_end_reconstruction(self):
        """Reconstruct line with chord at end."""
        from src.utils.chordpro_parser import ChordProLine, reconstruct_brackets

        line = ChordProLine(text="Amazing grace ", chords=[ChordPosition("G", 14)])
        result = reconstruct_brackets(line)

        assert result == "Amazing grace [G]"

    def test_no_chords_reconstruction(self):
        """Reconstruct line with no chords."""
        from src.utils.chordpro_parser import ChordProLine, reconstruct_brackets

        line = ChordProLine(text="Just text", chords=[])
        result = reconstruct_brackets(line)

        assert result == "Just text"

    def test_slash_chord_reconstruction(self):
        """Reconstruct slash chord notation."""
        from src.utils.chordpro_parser import ChordProLine, reconstruct_brackets

        line = ChordProLine(text="grace", chords=[ChordPosition("D/F#", 0)])
        result = reconstruct_brackets(line)

        assert result == "[D/F#]grace"

    def test_round_trip_preservation(self):
        """Verify parse → reconstruct → parse produces equivalent data."""
        from src.utils.chordpro_parser import parse_chordpro, reconstruct_brackets

        original = "Who [Bm]else commands the [G]time with His [D]hand?"
        parsed = parse_chordpro(original)
        reconstructed = reconstruct_brackets(parsed)
        reparsed = parse_chordpro(reconstructed)

        # Text should match
        assert parsed.text == reparsed.text

        # Chords should match
        assert len(parsed.chords) == len(reparsed.chords)
        for orig_chord, new_chord in zip(parsed.chords, reparsed.chords):
            assert orig_chord.chord == new_chord.chord
            assert orig_chord.position == new_chord.position


class TestFormatTwoLineDisplay:
    """Tests for format_two_line_display function."""

    def test_simple_two_line(self):
        """Format simple line with one chord."""
        from src.utils.chordpro_parser import ChordProLine, format_two_line_display

        line = ChordProLine(text="Who else", chords=[ChordPosition("Bm", 4)])
        result = format_two_line_display(line)

        assert result == "    Bm\nWho else"

    def test_multiple_chords_two_line(self):
        """Format line with multiple chords."""
        from src.utils.chordpro_parser import ChordProLine, format_two_line_display

        line = ChordProLine(
            text="Who else commands the time",
            chords=[ChordPosition("Bm", 4), ChordPosition("G", 22)],
        )
        result = format_two_line_display(line)

        # "Bm" at position 4, then "G" at position 22
        # After "Bm" (2 chars), need to reach position 22
        # Position after "Bm" = 4 + 2 = 6, need 22 - 6 = 16 spaces
        expected = "    Bm                G\nWho else commands the time"
        assert result == expected

    def test_chord_at_start_two_line(self):
        """Format line with chord at position 0."""
        from src.utils.chordpro_parser import ChordProLine, format_two_line_display

        line = ChordProLine(text="Amazing grace", chords=[ChordPosition("G", 0)])
        result = format_two_line_display(line)

        assert result == "G\nAmazing grace"

    def test_no_chords_two_line(self):
        """Format line with no chords."""
        from src.utils.chordpro_parser import ChordProLine, format_two_line_display

        line = ChordProLine(text="Just text", chords=[])
        result = format_two_line_display(line)

        assert result == "Just text"


class TestRoundTripProperty:
    """Property-based tests for ChordPro round-trip preservation."""

    # Strategy: valid chord symbols (alphanumeric, #, b, /, m, M, s, u, a, j, 7, 9, etc.)
    chord_symbol = st.text(
        alphabet=st.sampled_from(
            list(string.ascii_uppercase + string.digits + "#b/msuaj79+-()")
        ),
        min_size=1,
        max_size=8,
    ).filter(lambda s: s[0] in string.ascii_uppercase)

    # Strategy: lyric text without brackets
    lyric_text = st.text(
        alphabet=st.characters(
            blacklist_categories=("Cs",),  # no surrogates
            blacklist_characters="[]",
        ),
        min_size=0,
        max_size=200,
    )

    @given(
        text=lyric_text,
        chords=st.lists(
            st.tuples(
                chord_symbol,
                st.integers(min_value=0, max_value=200),
            ),
            min_size=0,
            max_size=10,
        ),
    )
    @settings(deadline=None)
    def test_parse_reconstruct_parse_equivalence(self, text, chords):
        """Parse → reconstruct → parse produces equivalent ChordProLine.

        Validates Requirement 5.5: round-trip property for all valid data.
        """
        # Build chord positions, capping at text length
        chord_positions = [
            ChordPosition(chord=chord_sym, position=min(pos, len(text)))
            for chord_sym, pos in chords
        ]

        # Sort by position so forward comparison matches parsed order
        # (reconstruct_brackets sorts internally; stable sort preserves
        # original ordering of chords at duplicate positions)
        chord_positions.sort(key=lambda c: c.position)

        original_line = ChordProLine(text=text, chords=chord_positions)

        # Forward: generate valid ChordPro string and parse it
        chordpro_str = reconstruct_brackets(original_line)
        parsed_once = parse_chordpro(chordpro_str)

        # Round-trip: reconstruct and parse again
        reconstructed = reconstruct_brackets(parsed_once)
        parsed_twice = parse_chordpro(reconstructed)

        # Forward direction: original line should match first parse
        assert original_line.text == parsed_once.text, (
            f"Forward text mismatch: '{original_line.text}' vs '{parsed_once.text}'\n"
            f"ChordPro: {chordpro_str!r}"
        )
        assert len(original_line.chords) == len(parsed_once.chords), (
            f"Forward chord count mismatch: {len(original_line.chords)} vs {len(parsed_once.chords)}\n"
            f"ChordPro: {chordpro_str!r}"
        )
        for i, (orig, parsed) in enumerate(zip(original_line.chords, parsed_once.chords)):
            assert orig.chord == parsed.chord, (
                f"Forward chord symbol mismatch at index {i}: '{orig.chord}' vs '{parsed.chord}'\n"
                f"ChordPro: {chordpro_str!r}"
            )
            assert orig.position == parsed.position, (
                f"Forward chord position mismatch at index {i}: {orig.position} vs {parsed.position}\n"
                f"ChordPro: {chordpro_str!r}"
            )

        # Round-trip: parsed_once must equal parsed_twice
        assert parsed_once.text == parsed_twice.text, (
            f"Round-trip text mismatch: '{parsed_once.text}' vs '{parsed_twice.text}'\n"
            f"ChordPro: {chordpro_str!r}\nReconstructed: {reconstructed!r}"
        )
        assert len(parsed_once.chords) == len(parsed_twice.chords), (
            f"Round-trip chord count mismatch: {len(parsed_once.chords)} vs {len(parsed_twice.chords)}\n"
            f"ChordPro: {chordpro_str!r}\nReconstructed: {reconstructed!r}"
        )
        for i, (c1, c2) in enumerate(zip(parsed_once.chords, parsed_twice.chords)):
            assert c1.chord == c2.chord, (
                f"Round-trip chord symbol mismatch at index {i}: '{c1.chord}' vs '{c2.chord}'\n"
                f"ChordPro: {chordpro_str!r}\nReconstructed: {reconstructed!r}"
            )
            assert c1.position == c2.position, (
                f"Round-trip chord position mismatch at index {i}: {c1.position} vs {c2.position}\n"
                f"ChordPro: {chordpro_str!r}\nReconstructed: {reconstructed!r}"
            )


class TestPrettyPrintChordpro:
    """Tests for pretty_print_chordpro main function."""

    def test_html_format_simple(self):
        """Generate HTML format with span tags."""
        from src.utils.chordpro_parser import ChordProLine, pretty_print_chordpro

        line = ChordProLine(text="Who else", chords=[ChordPosition("Bm", 4)])
        result = pretty_print_chordpro(line, "html")

        assert result == 'Who <span class="chord">Bm</span>else'

    def test_html_format_multiple_chords(self):
        """Generate HTML format with multiple chords."""
        from src.utils.chordpro_parser import ChordProLine, pretty_print_chordpro

        line = ChordProLine(
            text="Who else commands the time",
            chords=[ChordPosition("Bm", 4), ChordPosition("G", 22)],
        )
        result = pretty_print_chordpro(line, "html")

        assert (
            result
            == 'Who <span class="chord">Bm</span>else commands the <span class="chord">G</span>time'
        )

    def test_html_format_chord_at_start(self):
        """Generate HTML format with chord at position 0."""
        from src.utils.chordpro_parser import ChordProLine, pretty_print_chordpro

        line = ChordProLine(text="Amazing grace", chords=[ChordPosition("G", 0)])
        result = pretty_print_chordpro(line, "html")

        assert result == '<span class="chord">G</span>Amazing grace'

    def test_html_format_no_chords(self):
        """Generate HTML format with no chords."""
        from src.utils.chordpro_parser import ChordProLine, pretty_print_chordpro

        line = ChordProLine(text="Just text", chords=[])
        result = pretty_print_chordpro(line, "html")

        assert result == "Just text"

    def test_html_format_escaping(self):
        """Verify HTML escaping for safety."""
        from src.utils.chordpro_parser import ChordProLine, pretty_print_chordpro

        line = ChordProLine(
            text="Test <script> & stuff", chords=[ChordPosition("C#", 5)]
        )
        result = pretty_print_chordpro(line, "html")

        assert (
            result
            == 'Test <span class="chord">C#</span>&lt;script&gt; &amp; stuff'
        )

    def test_html_format_chord_escaping(self):
        """Verify HTML escaping in chord symbols."""
        from src.utils.chordpro_parser import ChordProLine, pretty_print_chordpro

        # Edge case: chord with HTML-like content (unlikely but possible)
        line = ChordProLine(text="Test", chords=[ChordPosition("C<D", 0)])
        result = pretty_print_chordpro(line, "html")

        assert result == '<span class="chord">C&lt;D</span>Test'

    def test_chordpro_format(self):
        """Generate ChordPro bracket notation."""
        from src.utils.chordpro_parser import ChordProLine, pretty_print_chordpro

        line = ChordProLine(text="Who else", chords=[ChordPosition("Bm", 4)])
        result = pretty_print_chordpro(line, "chordpro")

        assert result == "Who [Bm]else"

    def test_plain_format(self):
        """Generate plain two-line format."""
        from src.utils.chordpro_parser import ChordProLine, pretty_print_chordpro

        line = ChordProLine(text="Who else", chords=[ChordPosition("Bm", 4)])
        result = pretty_print_chordpro(line, "plain")

        assert result == "    Bm\nWho else"

    def test_invalid_format_raises_error(self):
        """Raise ValueError for unsupported format."""
        import pytest

        from src.utils.chordpro_parser import ChordProLine, pretty_print_chordpro

        line = ChordProLine(text="Test", chords=[])

        with pytest.raises(ValueError) as exc_info:
            pretty_print_chordpro(line, "invalid")

        assert "Unsupported format 'invalid'" in str(exc_info.value)
        assert "Must be 'html', 'plain', or 'chordpro'" in str(exc_info.value)

    def test_real_world_html_output(self):
        """Test HTML output for actual verse line."""
        from src.utils.chordpro_parser import parse_chordpro, pretty_print_chordpro

        parsed = parse_chordpro("Who [Bm]else but [G]O - [A]nly our [D]God?")
        result = pretty_print_chordpro(parsed, "html")

        expected = (
            'Who <span class="chord">Bm</span>else but '
            '<span class="chord">G</span>O - '
            '<span class="chord">A</span>nly our '
            '<span class="chord">D</span>God?'
        )
        assert result == expected
