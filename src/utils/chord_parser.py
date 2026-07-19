"""Unified chord grammar, parser, and transposer.

Single source of truth for the chord DSL used across the app and the
slide-generator pipeline. Replaces three previously-divergent regexes
in:

* ``src/utils/song_validator.py`` (``CHORD_PATTERN``)
* ``src/utils/yaml_converter.py`` (``CHORD_TOKEN_RE``)
* ``band-deck-slide-generator/scripts/yaml_to_marp.py`` (``_transpose_chord``)
* ``band-deck-slide-generator/scripts/band_deck_helpers.py`` (``CHORD_TOKEN_RE``)

Grammar (case-sensitive, ASCII; legacy Unicode is normalised first):

    [A-G]                          Root letter (A through G).
    [b#]?                          Optional flat/sharp accidental on the root.
    (m|maj|min|                    Quality (optional; default = major).
     dim|aug|
     sus[24]?|add[0-9]+)?
    ([b#]?[0-9]+)*                Extensions and alterations (e.g. 7, b9, #11).
    (/[A-G][b#]?)?                 Optional bass (slash chord).

Examples: ``G``, ``Bm``, ``D/F#``, ``Cmaj7``, ``Asus4``, ``Cadd9``, ``G7``,
``Bm7b5``, ``G7b9``, ``G7b9#11``, ``G7b9#11b13``.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from typing import Optional, Tuple


__all__ = [
    "CHORD_GRAMMAR_RE",
    "CHORD_TOKEN_RE",
    "CHORD_BRACKET_RE",
    "CHROMATIC_SCALE_SHARPS",
    "CHROMATIC_SCALE_FLATS",
    "ChordNode",
    "ExtensionToken",
    "parse_chord",
    "serialize_chord",
    "is_valid_chord",
    "normalize_chord_superscripts",
    "format_chord_inner",
    "format_chord_html",
    "transpose_chord_string",
    "transpose_chord_line_string",
    "get_semitone_shift",
]	


# ---------------------------------------------------------------------------
# Unicode → ASCII normalisation (legacy-data bridge)
# ---------------------------------------------------------------------------

_UNICODE_NORMALISATIONS = str.maketrans(
    {
        # Superscript / subscript digits.
        "\u2070": "0",
        "\u00b9": "1",
        "\u00b2": "2",
        "\u00b3": "3",
        "\u2074": "4",
        "\u2075": "5",
        "\u2076": "6",
        "\u2077": "7",
        "\u2078": "8",
        "\u2079": "9",
        "\u2080": "0",
        "\u2081": "1",
        "\u2082": "2",
        "\u2083": "3",
        "\u2084": "4",
        "\u2085": "5",
        "\u2086": "6",
        "\u2087": "7",
        "\u2088": "8",
        "\u2089": "9",
        # Latin modifier letters (small caps) used for chord annotations
        # such as ``Cᵐᵃʲ⁷`` (which is the legacy Unicode spelling of
        # ``Cmaj7``). Keep this list exhaustive so any future music-typography
        # variant that appears in scraped or pasted chart text degrades to
        # ASCII rather than silently failing to parse.
        "\u1d43": "a",   # ᵃ -> a
        "\u1d47": "b",   # ᵇ -> b
        "\u1d9c": "c",   # ᶜ -> c
        "\u1d48": "d",   # ᵈ -> d
        "\u1d49": "e",   # ᵉ -> e
        "\u1da0": "f",   # ᶠ -> f
        "\u1d4d": "g",   # ᵍ -> g
        "\u02b0": "h",   # ʰ -> h
        "\u2071": "i",   # ⁱ -> i
        "\u02b2": "j",   # ʲ -> j
        "\u1d4f": "k",   # ᵏ -> k
        "\u02e1": "l",   # ˡ -> l
        "\u1d50": "m",   # ᵐ -> m
        "\u207f": "n",   # ⁿ -> n
        "\u1d52": "o",   # ᵒ -> o
        "\u1d56": "p",   # ᵖ -> p
        "\u02b3": "r",   # ʳ -> r
        "\u02e2": "s",   # ˢ -> s
        "\u1d57": "t",   # ᵗ -> t
        "\u1d58": "u",   # ᵘ -> u
        "\u1d5b": "v",   # ᵛ -> v
        "\u02b7": "w",   # ʷ -> w
        "\u02e3": "x",   # ˣ -> x
        "\u02b8": "y",   # ʸ -> y
        "\u1dbb": "z",   # ᶻ -> z
        # A few capital-style modifier strokes seen in some chord sites.
        "\u1d39": "M",   # ᴹ -> M
        # Music typography: flat / sharp.
        "\u266f": "#",
        "\u266d": "b",
    }
)


def normalize_chord_superscripts(chord: str) -> str:
    """Map common Unicode chord-typographic characters to ASCII.

    Legacy YAML or pasted chord text sometimes uses superscripts or
    music-typographic characters (``G\u2077``, ``D/F\u266f``, ``F\u266fm\u2077``).
    This best-effort bridge keeps such data loading while the project
    standardises on plain ASCII syntax.
    """
    return chord.translate(_UNICODE_NORMALISATIONS)


# ---------------------------------------------------------------------------
# Master regex (one body reused for anchored, unanchored, and bracket matches)
# ---------------------------------------------------------------------------

_CHORD_GRAMMAR_BODY = (
    r"[A-G]"                                          # root
    r"[b#]?"                                          # accidental
    r"(?:madd[0-9]+|m(?:aj|in)?|dim|aug|sus[24]?|add[0-9]+)?"  # quality (optional)
    r"(?:[b#]?[0-9]+)*"                               # extensions + alterations
    r"(?:/[A-G][b#]?)?"                               # optional bass
)

CHORD_GRAMMAR_RE = re.compile(r"^" + _CHORD_GRAMMAR_BODY + r"$")
CHORD_TOKEN_RE = re.compile(_CHORD_GRAMMAR_BODY)
CHORD_BRACKET_RE = re.compile(r"\[(" + _CHORD_GRAMMAR_BODY + r")\]")


# ---------------------------------------------------------------------------
# Data model (the simpler shape used throughout this codebase)
# ---------------------------------------------------------------------------

CHROMATIC_SCALE_SHARPS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
CHROMATIC_SCALE_FLATS = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]
_ENHARMONIC = {
    "Db": "C#", "Eb": "D#", "Gb": "F#", "Ab": "G#", "Bb": "A#",
    "C#": "Db", "D#": "Eb", "F#": "Gb", "G#": "Ab", "A#": "Bb",
}


@dataclass(frozen=True)
class ExtensionToken:
    """One third-stacked extension or alteration (e.g. ``7``, ``b9``, ``#11``).

    ``sign`` is ``""`` (diatonic) / ``"b"`` (flat) / ``"#"`` (sharp).
    ``degree`` is the integer scale degree above the root (7, 9, 11, 13).
    """

    sign: str
    degree: int


@dataclass(frozen=True)
class ChordNode:
    """Parsed representation of one chord symbol.

    Captures the simpler shape used throughout this codebase:
    ``root + accidental + quality + extensions + bass``.
    """

    root: str
    accidental: str
    quality: str = ""
    extensions: Tuple[ExtensionToken, ...] = field(default_factory=tuple)
    bass: Optional[Tuple[str, str]] = None  # (root_letter, accidental)

    @property
    def root_with_accidental(self) -> str:
        return f"{self.root}{self.accidental}"


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def parse_chord(chord: str) -> Optional[ChordNode]:
    """Parse a chord string into a :class:`ChordNode`. Return ``None`` if invalid.

    Empty or whitespace-only input returns ``None``. Strings written with
    Unicode superscripts (``G\u2077``) or music typography (``D/F\u266f``) are
    normalised to ASCII before parsing.
    """
    if chord is None or not isinstance(chord, str) or not chord.strip():
        return None
    normalised = normalize_chord_superscripts(chord.strip())
    if not CHORD_GRAMMAR_RE.fullmatch(normalised):
        return None

    idx = 0
    length = len(normalised)
    root = normalised[idx]
    idx += 1

    accidental = ""
    if idx < length and normalised[idx] in "b#":
        accidental = normalised[idx]
        idx += 1

    quality = ""
    if idx < length:
        ch = normalised[idx]
        # Quality dispatch (longest match first so ``madd<N>`` beats
        # ``m`` and ``add<N>`` beats ``a``).
        if normalised.startswith("madd", idx):
            j = idx + 4
            end = j
            while end < length and normalised[end: end + 1].isdigit():
                end += 1
            quality = f"madd{normalised[j:end]}" if end > j else "madd"
            idx = end
        elif normalised.startswith("add", idx):
            j = idx + 3
            end = j
            while end < length and normalised[end: end + 1].isdigit():
                end += 1
            quality = f"add{normalised[j:end]}" if end > j else "add"
            idx = end
        elif ch == "m":
            if normalised.startswith("maj", idx):
                quality = "maj"
                idx += 3
            elif normalised.startswith("min", idx):
                quality = "min"
                idx += 3
            else:
                quality = "m"
                idx += 1
        elif normalised.startswith("dim", idx):
            quality = "dim"
            idx += 3
        elif normalised.startswith("aug", idx):
            quality = "aug"
            idx += 3
        elif normalised.startswith("sus", idx):
            if (
                idx + 3 < length
                and normalised[idx + 3] in "24"
                and (idx + 4 == length or not normalised[idx + 4].isdigit())
            ):
                quality = f"sus{normalised[idx + 3]}"
                idx += 4
            elif idx + 3 == length:
                quality = "sus"
                idx += 3
            else:
                return None

    extensions: list[ExtensionToken] = []
    while idx < length and normalised[idx] != "/":
        sign = ""
        if normalised[idx] in "b#":
            sign = normalised[idx]
            idx += 1
        if idx >= length or not normalised[idx: idx + 1].isdigit():
            return None
        start = idx
        while idx < length and normalised[idx: idx + 1].isdigit():
            idx += 1
        extensions.append(ExtensionToken(sign=sign, degree=int(normalised[start:idx])))

    bass: Optional[Tuple[str, str]] = None
    if idx < length and normalised[idx] == "/":
        idx += 1
        if idx >= length or normalised[idx] not in "ABCDEFG":
            return None
        bass_letter = normalised[idx]
        idx += 1
        bass_acc = ""
        if idx < length and normalised[idx] in "b#":
            bass_acc = normalised[idx]
            idx += 1
        bass = (bass_letter, bass_acc)

    if idx != length:
        return None

    return ChordNode(
        root=root,
        accidental=accidental,
        quality=quality,
        extensions=tuple(extensions),
        bass=bass,
    )


def serialize_chord(node: ChordNode) -> str:
    """Render a :class:`ChordNode` into the canonical ASCII string form.

    Round-trip guarantee: ``serialize_chord(parse_chord(s))`` returns ``s``
    for any input that already conforms to the grammar.
    """
    parts: list[str] = [node.root, node.accidental, node.quality]
    for ext in node.extensions:
        parts.append(f"{ext.sign}{ext.degree}")
    if node.bass is not None:
        parts.append(f"/{node.bass[0]}{node.bass[1]}")
    return "".join(parts)


def is_valid_chord(chord: str) -> bool:
    """Return whether ``chord`` is a recognised chord symbol.

    Empty, whitespace, and unparseable strings all return ``False``.
    """
    if chord is None or not isinstance(chord, str) or not chord.strip():
        return False
    return parse_chord(chord) is not None


# ---------------------------------------------------------------------------
# Pretty HTML rendering for slide decks
# ---------------------------------------------------------------------------

_ACCIDENTAL_GLYPHS = {
    "#": "\u266f",   # ♯
    "b": "\u266d",   # ♭
    "\u266f": "\u266f",
    "\u266d": "\u266d",
}


def _accidental_glyph(accidental: str) -> str:
    """Map an ASCII accidental character to its music-typography glyph.

    ``#`` becomes ``♯`` and ``b`` becomes ``♭`` so slide output reads like
    a printed chart. Already-Unicode accidentals pass through unchanged
    so legacy inputs render without surprise.
    """
    if not accidental:
        return accidental
    return _ACCIDENTAL_GLYPHS.get(accidental, accidental)


def format_chord_inner(chord: str) -> str:
    """Return prettified HTML content (no outer wrapper) for one chord symbol.

    Builds markup from the parsed :class:`ChordNode` so each chord component
    receives the right representation:

    * Root letter ``G`` -> ``G``
    * Accidental -> ``\u266f`` / ``\u266d`` music typography
    * Quality -> plain (``m``, ``sus4``, ``add9``, ``maj``, ``dim``)
    * Each extension wrapped in ``<sup>... </sup>`` so CSS can shrink +
      raise it; ``b9`` becomes ``<sup>\u266d9</sup>``.
    * Slash bass wrapped in ``<span class="bass">...</span>`` so it can be
      styled distinctly (smaller, dimmed) without leaving the row's
      monospace alignment.

    Invalid input is rendered as escaped plain text inside the caller's
    outer wrapper rather than rejected, so upstream renderers can hand
    through unexpected symbols safely.
    """
    if chord is None:
        return ""
    if not isinstance(chord, str):
        chord = str(chord)
    stripped = chord.strip()
    if not stripped:
        return html.escape(chord)

    normalised = normalize_chord_superscripts(stripped)
    node = parse_chord(normalised)
    if node is None:
        return html.escape(chord)

    parts: list[str] = [html.escape(node.root)]
    if node.accidental:
        parts.append(html.escape(_accidental_glyph(node.accidental)))
    if node.quality:
        parts.append(html.escape(node.quality))
    for ext in node.extensions:
        sign = _accidental_glyph(ext.sign)
        parts.append(f"<sup>{html.escape(sign)}{ext.degree}</sup>")
    if node.bass is not None:
        bass_letter, bass_acc = node.bass
        parts.append(
            f'<span class="bass">/'
            f"{html.escape(bass_letter)}"
            f"{html.escape(_accidental_glyph(bass_acc))}"
            "</span>"
        )
    return "".join(parts)


def format_chord_html(chord: str) -> str:
    """Render a chord symbol as a standalone ``<span class="chord">`` HTML chunk.

    Use this in inline-with-lyrics renderers (each chord gets its own span).
    For aligned monospace chord rows prefer :func:`format_chord_inner`
    wrapped in a single outer span by the caller.
    """
    return f'<span class="chord">{format_chord_inner(chord)}</span>'


# ---------------------------------------------------------------------------
# Transposition
# ---------------------------------------------------------------------------

def _note_index(note: str, use_flats: bool) -> int:
    """Return the 0-11 chromatic index of a note (e.g. ``"F#"``)."""
    scale = CHROMATIC_SCALE_FLATS if use_flats else CHROMATIC_SCALE_SHARPS
    if note in scale:
        return scale.index(note)
    alternate = _ENHARMONIC.get(note)
    if alternate is not None and alternate in scale:
        return scale.index(alternate)
    return -1


def _note_name(index: int, use_flats: bool) -> str:
    """Return the chromatic note name at ``index`` (mod 12)."""
    scale = CHROMATIC_SCALE_FLATS if use_flats else CHROMATIC_SCALE_SHARPS
    return scale[index % 12]


def _shift_root(
    root: str, accidental: str, semitones: int, use_flats: bool
) -> Tuple[str, str]:
    """Shift a ``(root, accidental)`` pair by ``semitones`` semitones."""
    full_note = f"{root}{accidental}"
    idx = _note_index(full_note, use_flats)
    if idx == -1:
        return root, accidental
    new_name = _note_name(idx + semitones, use_flats)
    if len(new_name) == 2 and new_name[1] in "b#":
        return new_name[0], new_name[1]
    return new_name, ""


def transpose_chord_string(
    chord: str, semitones: int, use_flats: bool = False
) -> str:
    """Transpose a chord symbol by ``semitones``.

    Quality, extensions, alterations, and bass are preserved verbatim.
    The accidental style of the result follows ``use_flats``: pass
    ``True`` for flat keys (``"Bb"``, ``"Eb"``, ``"Ab"``), ``False`` for
    sharp keys. Unparseable input is returned unchanged so the caller
    never crashes on unexpected data.

    Multi-slash chords (e.g. ``C/G/B``) are split on every ``/`` and each
    component is transposed independently so poly-bass voicings survive
    transposition. This matches the legacy behaviour of the regex-based
    implementation that pre-dated the parser.
    """
    if "/" in chord:
        return "/".join(
            transpose_chord_string(part, semitones, use_flats)
            for part in chord.split("/")
        )
    node = parse_chord(chord)
    if node is None:
        return chord
    new_root, new_acc = _shift_root(node.root, node.accidental, semitones, use_flats)
    new_bass: Optional[Tuple[str, str]] = None
    if node.bass is not None:
        new_bass = _shift_root(node.bass[0], node.bass[1], semitones, use_flats)
    return serialize_chord(
        ChordNode(
            root=new_root,
            accidental=new_acc,
            quality=node.quality,
            extensions=node.extensions,
            bass=new_bass,
        )
    )


def transpose_chord_line_string(
    line: str, semitones: int, use_flats: bool = False
) -> str:
    """Apply :func:`transpose_chord_string` to every chord token in ``line``.

    Designed for space-padded / monospace chord-only rows (instrumental
    sections) and inline chord annotations above a lyric line. Tokens
    that do not match the chord grammar (whitespace, bare digits, etc.)
    are left untouched.
    """
    if not line:
        return line
    return CHORD_TOKEN_RE.sub(
        lambda m: transpose_chord_string(m.group(0), semitones, use_flats),
        line,
    )


def get_semitone_shift(original_key: str, target_key: str) -> int:
    """Return the chromatic semitone offset from ``original_key`` to ``target_key``.

    Returns ``0`` when either key is unknown / missing, so callers can use
    this unconditionally without pre-checks.
    """
    if not original_key or not target_key:
        return 0
    try:
        idx_orig = _note_index(original_key, use_flats=False)
        idx_target = _note_index(target_key, use_flats=False)
        if idx_orig == -1 or idx_target == -1:
            return 0
        return (idx_target - idx_orig) % 12
    except (TypeError, AttributeError):
        return 0
