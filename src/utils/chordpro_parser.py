"""ChordPro parser for band-deck slide generation.

Parses ChordPro notation (e.g., "[G]Amazing [D/F#]grace") into structured data
with chord symbols and their positions relative to lyric text.
"""

import html
import logging
import re
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class TokenType(Enum):
    """Token types for ChordPro parsing."""

    TEXT = "text"
    CHORD = "chord"


@dataclass
class Token:
    """A single token from ChordPro parsing."""

    type: TokenType
    value: str


@dataclass
class ChordPosition:
    """A chord symbol and its character position in the lyric text."""

    chord: str
    position: int


@dataclass
class ChordProLine:
    """Parsed ChordPro line with lyrics and positioned chords."""

    text: str
    chords: list[ChordPosition]


def tokenize_chordpro(raw_line: str) -> list[Token]:
    """Split ChordPro line into chord and text tokens.

    Parses notation like "[G]Amazing [D/F#]grace" into a sequence of
    Text and Chord tokens.

    Args:
        raw_line: ChordPro-formatted string with chords in brackets

    Returns:
        List of Token objects (Text or Chord)

    Example:
        >>> tokenize_chordpro("Who [Bm]else commands")
        [Token(TEXT, "Who "), Token(CHORD, "Bm"), Token(TEXT, "else commands")]
    """
    tokens: list[Token] = []
    pattern = r"\[([^\]]+)\]"
    last_pos = 0

    for match in re.finditer(pattern, raw_line):
        # Add text before chord
        if match.start() > last_pos:
            tokens.append(Token(TokenType.TEXT, raw_line[last_pos : match.start()]))

        # Add chord (contents of brackets)
        tokens.append(Token(TokenType.CHORD, match.group(1)))
        last_pos = match.end()

    # Add remaining text
    if last_pos < len(raw_line):
        tokens.append(Token(TokenType.TEXT, raw_line[last_pos:]))

    return tokens


def calculate_positions(tokens: list[Token]) -> ChordProLine:
    """Calculate character positions for each chord in the token stream.

    Converts tokens into a ChordProLine with plain text and chord positions.

    Args:
        tokens: List of Token objects from tokenize_chordpro()

    Returns:
        ChordProLine with text string and positioned chords

    Example:
        >>> tokens = [Token(TEXT, "Who "), Token(CHORD, "Bm"), Token(TEXT, "else")]
        >>> calculate_positions(tokens)
        ChordProLine(text="Who else", chords=[ChordPosition(chord="Bm", position=4)])
    """
    text_parts: list[str] = []
    chords: list[ChordPosition] = []
    current_pos = 0

    for token in tokens:
        if token.type == TokenType.TEXT:
            text_parts.append(token.value)
            current_pos += len(token.value)
        elif token.type == TokenType.CHORD:
            chords.append(ChordPosition(chord=token.value, position=current_pos))

    return ChordProLine(text="".join(text_parts), chords=chords)


def parse_chordpro(raw_line: str) -> ChordProLine:
    """Parse ChordPro notation into structured data (main entry point).

    Converts ChordPro notation like "[G]Amazing [D/F#]grace" into a
    ChordProLine with plain text and positioned chord symbols.

    Args:
        raw_line: ChordPro-formatted string with chords in brackets

    Returns:
        ChordProLine with text and positioned chords

    Example:
        >>> parse_chordpro("Who [Bm]else commands the [G]time")
        ChordProLine(
            text="Who else commands the time",
            chords=[
                ChordPosition(chord="Bm", position=4),
                ChordPosition(chord="G", position=22)
            ]
        )
    """
    logger.debug(f"Parsing ChordPro line: {raw_line}")

    tokens = tokenize_chordpro(raw_line)
    result = calculate_positions(tokens)

    logger.debug(f"Parsed text: '{result.text}', chords: {result.chords}")

    return result



def reconstruct_brackets(line: ChordProLine) -> str:
    """Reconstruct original ChordPro bracket notation from parsed data.

    Converts a ChordProLine back into ChordPro format with [Chord] brackets.
    This enables round-trip conversion: parse → reconstruct → parse.

    Args:
        line: ChordProLine with text and positioned chords

    Returns:
        ChordPro-formatted string with chords in brackets

    Example:
        >>> line = ChordProLine(text="Who else", chords=[ChordPosition("Bm", 4)])
        >>> reconstruct_brackets(line)
        "Who [Bm]else"
    """
    result: list[str] = []
    last_pos = 0

    # Sort chords by position to ensure correct ordering
    sorted_chords = sorted(line.chords, key=lambda c: c.position)

    for chord_pos in sorted_chords:
        # Add text before chord
        result.append(line.text[last_pos : chord_pos.position])
        # Add bracketed chord
        result.append(f"[{chord_pos.chord}]")
        last_pos = chord_pos.position

    # Add remaining text
    result.append(line.text[last_pos:])

    return "".join(result)


def format_two_line_display(line: ChordProLine) -> str:
    """Format ChordPro line as two-line display for terminal output.

    Creates a chord line above the lyric line with proper alignment.

    Args:
        line: ChordProLine with text and positioned chords

    Returns:
        Two-line string with chords above lyrics

    Example:
        >>> line = ChordProLine(text="Who else", chords=[ChordPosition("Bm", 4)])
        >>> print(format_two_line_display(line))
            Bm
        Who else
    """
    if not line.chords:
        # No chords, just return the text
        return line.text

    # Build chord line with proper spacing
    chord_line_parts: list[str] = []
    last_pos = 0

    sorted_chords = sorted(line.chords, key=lambda c: c.position)

    for chord_pos in sorted_chords:
        # Add spacing to reach chord position
        spacing = chord_pos.position - last_pos
        chord_line_parts.append(" " * spacing)
        chord_line_parts.append(chord_pos.chord)
        last_pos = chord_pos.position + len(chord_pos.chord)

    chord_line = "".join(chord_line_parts)

    return f"{chord_line}\n{line.text}"


def pretty_print_chordpro(line: ChordProLine, format: str = "html") -> str:
    """Generate styled output with chords inline with lyrics.

    Converts a ChordProLine into various display formats suitable for
    different output targets (HTML slides, terminal, round-trip conversion).

    Args:
        line: ChordProLine with text and positioned chords
        format: Output format - "html", "plain", or "chordpro"

    Returns:
        Formatted string in the requested format

    Raises:
        ValueError: If format is not one of the supported options

    Examples:
        >>> line = ChordProLine(text="Amazing grace", chords=[ChordPosition("G", 0)])
        >>> pretty_print_chordpro(line, "html")
        '<span class="chord">G</span>Amazing grace'
        >>> pretty_print_chordpro(line, "chordpro")
        '[G]Amazing grace'
        >>> print(pretty_print_chordpro(line, "plain"))
        G
        Amazing grace
    """
    if format == "chordpro":
        # Reconstruct bracket notation for round-trip
        return reconstruct_brackets(line)

    elif format == "html":
        # Generate HTML with <span class="chord"> tags
        result: list[str] = []
        last_pos = 0

        sorted_chords = sorted(line.chords, key=lambda c: c.position)

        for chord_pos in sorted_chords:
            # Add text before chord (HTML-escaped)
            if chord_pos.position > last_pos:
                result.append(html.escape(line.text[last_pos : chord_pos.position]))
            # Add chord with span tag (HTML-escaped)
            result.append(f'<span class="chord">{html.escape(chord_pos.chord)}</span>')
            last_pos = chord_pos.position

        # Add remaining text (HTML-escaped)
        if last_pos < len(line.text):
            result.append(html.escape(line.text[last_pos:]))

        return "".join(result)

    elif format == "plain":
        # Terminal-friendly: chord line above lyric line
        return format_two_line_display(line)

    else:
        raise ValueError(
            f"Unsupported format '{format}'. Must be 'html', 'plain', or 'chordpro'."
        )
