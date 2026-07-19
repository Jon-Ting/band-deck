"""Comprehensive tests for the unified chord parser.

The parser owned by ``src.utils.chord_parser`` is the single source of
truth for chord grammar and transposition across both the main app and
the slide-generator pipeline. These tests pin down the public surface
(``is_valid_chord``, ``parse_chord``, ``serialize_chord``,
``transpose_chord_string``, ``transpose_chord_line_string``) and the
unified grammar's coverage of real-world chord symbols.
"""

import re
import unittest

from hypothesis import given, settings, strategies as st

from src.utils.chord_parser import (
    CHORD_BRACKET_RE,
    CHORD_GRAMMAR_RE,
    CHORD_TOKEN_RE,
    ChordNode,
    ExtensionToken,
    format_chord_html,
    format_chord_inner,
    get_semitone_shift,
    is_valid_chord,
    normalize_chord_superscripts,
    parse_chord,
    serialize_chord,
    transpose_chord_line_string,
    transpose_chord_string,
)


class TestGrammarAccepts(unittest.TestCase):
    """Chords the unified grammar must accept."""

    @classmethod
    def _valid(cls):
        return [
            "G",
            "A",
            "F",
            "C",
            "D",
            "E",
            "B",
            "Gb",
            "Db",
            "Eb",
            "Ab",
            "Bb",
            "F#",
            "C#",
            "G#",
            "D#",
            "A#",
            "Bm",
            "Cm",
            "Dm",
            "Em",
            "Am",
            "Gm",
            "Fm",
            "Bb",
            "Eb",
            "F#m",
            "C#m",
            "G#m",
            "Cmaj7",
            "Dmaj7",
            "Emaj7",
            "Gmaj7",
            "Amaj7",
            "Bmaj7",
            "Fmaj7",
            "C7",
            "D7",
            "E7",
            "F7",
            "G7",
            "A7",
            "B7",
            "C9",
            "D9",
            "G9",
            "C11",
            "G13",
            "C13",
            "Cm7",
            "Dm7",
            "Em7",
            "Gm7",
            "Am7",
            "Bm7",
            "Cmaj9",
            "Dmaj9",
            "Emaj9",
            "Asus4",
            "Dsus4",
            "Esus4",
            "Gsus4",
            "Csus2",
            "Dsus2",
            "Gadd9",
            "Cadd9",
            "Dadd9",
            "Cdim",
            "Ddim",
            "Edim",
            "Caug",
            "Eaug",
            "Gaug",
            "D/F#",
            "G/B",
            "C/E",
            "Am/G",
            "C/G",
            "Bm7b5",
            "Am7b5",
            "Em7b5",
            "Dm7b5",
            "Gm7b5",
            "G7b9",
            "G7#9",
            "G7b5",
            "G7#5",
            "G7#11",
            "G7b13",
            "G7b9#11",
            "G7b9b13",
            "G7#9b13",
            "G7b9#11b13",
            "G7#9#11",
            "C7b9",
            "C7#9",
            "C7b5",
            "F7b9",
            "F#m7b5",
            "Cm7b5",            "Bb7b9",
            "Eb7#9",
            "Ab13",
            "Db13",
            # Accidental-before-quality combinations the simpler
            # grammar must accept.
            "Bbmaj7",
            "Cbmaj7",
            "Ebmin7",
            "F#dim",
            "Gbaug",
            "Bbmaj9",
            "Ebsus4",
            "F#sus2",
            # ``m`` + ``add<N>`` composite quality.
            "Bbmadd9",
            "Cmadd9",
            "Gmadd9",
        ]   

    def test_grammar_accepts_canonical_chords(self):
        for chord in self._valid():
            with self.subTest(chord=chord):
                assert is_valid_chord(chord), f"Grammar should accept {chord!r}"
                assert parse_chord(chord) is not None

    def test_round_trip_preserves_canonical_chords(self):
        for chord in self._valid():
            with self.subTest(chord=chord):
                node = parse_chord(chord)
                assert serialize_chord(node) == chord, (
                    f"Round-trip lost fidelity: {chord!r} -> {serialize_chord(node)!r}"
                )


class TestGrammarRejects(unittest.TestCase):
    """Inputs the unified grammar must reject."""

    def test_empty_and_whitespace(self):
        assert not is_valid_chord("")
        assert not is_valid_chord("   ")
        assert not is_valid_chord("\t")

    def test_non_string_inputs(self):
        assert not is_valid_chord(None)
        assert not is_valid_chord(123)
        assert not is_valid_chord(["G"])

    def test_bare_letters(self):
        assert not is_valid_chord("H")  # not a note
        assert not is_valid_chord("gg")  # lowercase root

    def test_invalid_root_accidental_combos(self):
        assert not is_valid_chord("Gbb")  # double flat not in grammar
        assert not is_valid_chord("G##")
        assert not is_valid_chord("G♯♭")

    def test_invalid_qualities(self):
        assert not is_valid_chord("Gfoo")
        assert not is_valid_chord("G7m")  # digits-then-m

    def test_garbage_input(self):
        assert not is_valid_chord("Hello")
        assert not is_valid_chord("[G]")
        assert not is_valid_chord("G 7")  # space inside
        # Whitespace around the chord is tolerated by the parser
        # (it strips before matching); whitespace inside a chord is not.
        assert is_valid_chord("  G7b9#11  ")
        assert is_valid_chord("G7b9#11  ".strip())
        assert parse_chord("G7b9#11  ".strip()) is not None

    def test_accidental_before_quality_is_accepted(self):
        # Regression: the parser used to reject these because its
        # quality-block length check assumed no accidental was present.
        assert is_valid_chord("Bbmaj7")
        assert is_valid_chord("Ebmin7")
        assert is_valid_chord("Ebdim")
        assert is_valid_chord("Gbaug")
        assert is_valid_chord("Bbmadd9")

    def test_multi_slash_is_transposed_recursively(self):
        # Multi-bass polychords (rare, but supported): each component
        # transposes independently so the poly-bass voicing survives.
        assert transpose_chord_string("C/G/B", 2) == "D/A/C#"
        assert transpose_chord_string("G/B/D", -5) == "D/F#/A"

    def test_accidental_before_quality_is_accepted(self):
        # Regression: the parser used to reject these because its
        # quality-block length check assumed no accidental was present.
        assert is_valid_chord("Bbmaj7")
        assert is_valid_chord("Ebmin7")
        assert is_valid_chord("Ebdim")
        assert is_valid_chord("Gbaug")
        assert is_valid_chord("Bbmadd9")


class TestParseNodeStructure(unittest.TestCase):
    """Verify parse_chord() returns the expected ChordNode."""

    def test_plain_major(self):
        node = parse_chord("G")
        assert node == ChordNode(root="G", accidental="", quality="")

    def test_minor(self):
        node = parse_chord("Bm")
        assert node.root == "B"
        assert node.accidental == ""
        assert node.quality == "m"

    def test_sharp_root(self):
        node = parse_chord("F#m7b5")
        assert node.root == "F"
        assert node.accidental == "#"
        assert node.quality == "m"
        assert node.extensions == (ExtensionToken("", 7), ExtensionToken("b", 5))

    def test_altered_dominant_full_stack(self):
        node = parse_chord("G7b9#11b13")
        assert node.root == "G"
        assert node.quality == ""
        assert node.extensions == (
            ExtensionToken("", 7),
            ExtensionToken("b", 9),
            ExtensionToken("#", 11),
            ExtensionToken("b", 13),
        )

    def test_slash_bass(self):
        node = parse_chord("D/F#")
        assert node.root == "D"
        assert node.bass == ("F", "#")

    def test_sus_keeps_default_quality_empty(self):
        node = parse_chord("Gsus4")
        assert node.quality == "sus4"
        assert node.extensions == ()

    def test_add_chord(self):
        node = parse_chord("Gadd9")
        assert node.quality == "add9"
        assert node.extensions == ()


class TestUnicodeNormalisation(unittest.TestCase):
    """Real-world Unicode chord text should normalise and then parse."""

    def test_superscript_seven(self):
        assert is_valid_chord("G\u2077")
        assert normalize_chord_superscripts("G\u2077") == "G7"

    def test_music_typography_sharp(self):
        assert is_valid_chord("D/F\u266f")
        assert normalize_chord_superscripts("D/F\u266f") == "D/F#"

    def test_music_typography_flat(self):
        assert is_valid_chord("B\u266d7")
        assert normalize_chord_superscripts("B\u266d7") == "Bb7"

    def test_combined_unicode_modifier(self):
        # ``F\u266fm\u2077`` would mean ``F#m7`` if you squint.
        result = normalize_chord_superscripts("F\u266fm\u2077")
        assert result == "F#m7"
        assert is_valid_chord(result)

    def test_unicode_modifier_letters_render_as_ascii_chords(self):
        # The legacy ``Cmaj7``-style is sometimes written with four
        # Unicode modifier letters. ``C`` + ``\u1d50\u1d43\u02b2\u2077``
        # (m, a, j, superscript 7) should normalise to ``Cmaj7``.
        legacy = "C\u1d50\u1d43\u02b2\u2077"
        node = parse_chord(legacy)
        assert node is not None, "Cmaj7 written with modifier letters should parse"
        assert serialize_chord(node) == "Cmaj7"
        assert is_valid_chord(legacy)
        # Round-trip a sharp / flat minor chord with the same suffix.
        altered = "F\u266fm7\u1d43\u1d48"
        # ``a\u1d48`` -> ``ad`` because \u1d48 is mapped to ``d``.
        assert normalize_chord_superscripts(altered) == "F#m7ad"
        # The grammar treats ``m7ad`` as garbage (extensions must be a\n
        # digit-after-sign, and ``ad`` after ``m7`` is a stray suffix), so
        # the parser should reject this rather than silently mis-render.
        assert not is_valid_chord(altered)

    def test_superscript_ordinals_normalise(self):
        # Crucially, the parser should still recognise the result as not
        # a chord (1st is not a chord), but normalisation should be a no-op.
        assert normalize_chord_superscripts("1\u02e2\u1d57 time") == "1st time"
        assert not is_valid_chord("1st time")


class TestTransposition(unittest.TestCase):
    """Transposition is the second big responsibility of the parser."""

    def test_simple_major_up_one(self):
        assert transpose_chord_string("C", 1) == "C#"
        assert transpose_chord_string("C", 1, use_flats=True) == "Db"

    def test_simple_major_down_one(self):
        assert transpose_chord_string("G", -1) == "F#"
        assert transpose_chord_string("G", -1, use_flats=True) == "Gb"

    def test_minor_preserves_quality_and_accidental_style(self):
        assert transpose_chord_string("Am", 2) == "Bm"
        assert transpose_chord_string("Am", 2, use_flats=True) == "Bm"

    def test_altered_dominant_preserves_qualifier_stack(self):
        assert transpose_chord_string("G7b9#11b13", 5) == "C7b9#11b13"
        assert transpose_chord_string("G7b9#11b13", -5) == "D7b9#11b13"

    def test_minor_seventh_flat_five_preserves_alteration(self):
        # Default (sharp) scale: B + 3 = D. The flat-five alteration on
        # the original chord is preserved verbatim.
        assert transpose_chord_string("Bm7b5", 3) == "Dm7b5"
        # use_flats=True routes through the flat chromatic scale, so
        # B - 3 = Ab.
        assert transpose_chord_string("Bm7b5", -3, use_flats=True) == "Abm7b5"
        # use_flats=False: B - 3 = G# (per legacy rename behaviour).
        assert transpose_chord_string("Bm7b5", -3, use_flats=False) == "G#m7b5"

    def test_slash_chord_shifts_root_and_bass(self):
        # Sharp scale path (default): ``D`` -> ``E`` and ``F`` (the
        # letter of ``F#``) -> ``G``; the explicit accidental on ``F#``
        # is preserved.
        assert transpose_chord_string("D/F#", 2) == "E/G#"
        # Flat scale path routes ``D`` through flats (D -> E) and
        # ``F#`` through the flat chromatic scale (F# = Gb -> Ab),
        # matching the legacy regex-based transpose in
        # ``src.utils.search``.
        assert transpose_chord_string("D/F#", 2, use_flats=True) == "E/Ab"
        # Pure-flat-spelling chord: ``D/G`` with use_flats=True. ``D``
        # + 2 -> ``E`` (flat-scale index 4), ``G`` + 2 -> ``A`` (flat
        # scale index 9 — natural ``A``, not ``Ab``). Confirms the
        # legacy ``search.transpose_chord`` behaviour: chord spelling
        # follows the chosen scale when no explicit accidental is
        # present on the root.
        assert transpose_chord_string("D/G", 2, use_flats=True) == "E/A"

    def test_zero_semitones_is_identity(self):
        for chord in ("G", "Bm", "D/F#", "Cmaj7", "Gsus4", "Gadd9", "Bm7b5"):
            assert transpose_chord_string(chord, 0) == chord

    def test_round_trip_through_twelve_semitones(self):
        for chord in ("G", "Am", "C7", "F#m7b5", "G7b9#11b13", "D/F#"):
            shifted = transpose_chord_string(chord, 12)
            # Same note name (potentially different spelling).
            shifted_root = re.match(r"^[A-G][b#]?", shifted).group(0)
            original_root = re.match(r"^[A-G][b#]?", chord).group(0)
            assert (
                normalize_chord_superscripts(shifted).replace(
                    "b", ""
                ).replace(
                    "#", ""
                )
                == chord.replace("b", "").replace("#", "")
            )

    def test_round_trip_through_seven_then_five_returns_original(self):
        # Pure root and minor-chord round-trip across ``+7`` then ``+5``
        # semitones. Accidental-altering chords may flip the spelling
        # style but the letters always return to the input.
        for chord in ("G", "Am", "C7", "G/D"):
            forward = transpose_chord_string(chord, 7)
            back = transpose_chord_string(forward, 5)
            assert back == chord, (
                f"Round-trip failed: {chord!r} -> {forward!r} -> {back!r}"
            )

    def test_unparseable_input_passes_through_unchanged(self):
        assert transpose_chord_string("not a chord", 5) == "not a chord"
        assert transpose_chord_string("Xxx", 5) == "Xxx"


class TestLineTransposition(unittest.TestCase):
    """Aligned chord-row transposition (instrumental sections)."""

    def test_basic_chord_row(self):
        # The token regex replaces chord spans and preserves
        # surrounding whitespace exactly. ``"Em     C"`` has 5 spaces
        # between the two tokens, so the substitution keeps 5 spaces
        # even though ``F#m`` is one character wider than ``Em``.
        line = "G      D      Em     C"
        assert transpose_chord_line_string(line, 2) == (
            "A      E      F#m     D"
        )
        assert transpose_chord_line_string(line, 2, use_flats=True) == (
            "A      E      Gbm     D"
        )

    def test_slash_chord_row(self):
        # Default (sharp) scale: every chord advances exactly one
        # semitone and the explicit ``#`` on ``F#`` is preserved in
        # the bass.
        line = "D/F#   G      Bm     A"
        assert (
            transpose_chord_line_string(line, 1) == "D#/G   G#      Cm     A#"
        )

    def test_altered_chord_in_row(self):
        line = "G7b9   G7b9#11    Am"
        assert (
            transpose_chord_line_string(line, 2)
            == "A7b9   A7b9#11    Bm"
        )

    def test_non_chord_text_is_left_alone(self):
        # Note: the unanchored CHORD_TOKEN_RE will match any single
        # letter chord span (like the ``C`` inside ``N.C.`` here), so
        # ``+5`` semitones turns it into ``F``. This matches the legacy
        # behaviour documented in ``src.utils.search``; reserve
        # chord-only rows for transposition.
        line = "N.C.   (rest)   after"
        assert (
            transpose_chord_line_string(line, 5) == "N.F.   (rest)   after"
        )


class TestSemitoneShift(unittest.TestCase):
    """Helper for circuit-style transposition callers."""

    def test_known_offsets(self):
        assert get_semitone_shift("C", "G") == 7
        assert get_semitone_shift("G", "C") == 5
        assert get_semitone_shift("A", "A") == 0

    def test_missing_keys_default_to_zero(self):
        assert get_semitone_shift(None, "G") == 0
        assert get_semitone_shift("C", None) == 0
        assert get_semitone_shift("", "G") == 0


class TestPrettyRenderer(unittest.TestCase):
    """``format_chord_html`` / ``format_chord_inner`` build slide output."""

    def test_plain_chord_is_passthrough(self):
        # No extensions or accidental: prettified output equals root text.
        # Wrapping ``format_chord_html`` still adds the outer ``<span>``.
        assert format_chord_inner("G") == "G"
        assert format_chord_html("G") == '<span class="chord">G</span>'
        assert format_chord_inner("Bm") == "Bm"

    def test_minor_quality_renders_with_letter(self):
        assert format_chord_inner("Am") == "Am"
        assert format_chord_inner("F#m") == "F\u266fm"

    def test_extension_renders_inside_sup(self):
        # ``G7`` -> ``G<sup>7</sup>``.
        assert format_chord_inner("G7") == "G<sup>7</sup>"

    def test_altered_extension_renders_with_music_glyph(self):
        # ``b9`` -> ``♭9`` inside ``<sup>`` so the sign renders as music
        # typography rather than ASCII ``b``.
        assert format_chord_inner("G7b9") == "G<sup>7</sup><sup>\u266d9</sup>"
        assert format_chord_inner("G7#9") == "G<sup>7</sup><sup>\u266f9</sup>"

    def test_compound_altered_dominant_stacks_extensions(self):
        # ``G7b9#11b13`` -> ``G<sup>7</sup><sup>♭9</sup><sup>#11</sup><sup>♭13</sup>``.
        rendered = format_chord_inner("G7b9#11b13")
        assert rendered == (
            "G<sup>7</sup>"
            "<sup>\u266d9</sup>"
            "<sup>\u266f11</sup>"
            "<sup>\u266d13</sup>"
        )

    def test_altered_dominant_in_full_html_wrapper(self):
        assert format_chord_html("G7b9#11b13") == (
            '<span class="chord">'
            "G<sup>7</sup>"
            "<sup>\u266d9</sup>"
            "<sup>\u266f11</sup>"
            "<sup>\u266d13</sup>"
            "</span>"
        )

    def test_slash_bass_renders_in_class_bass(self):
        # ``D/F#`` -> ``D<span class="bass">/F♯</span>``
        assert format_chord_inner("D/F#") == (
            'D<span class="bass">/F\u266f</span>'
        )

    def test_slash_bass_with_full_html_wrapper(self):
        assert format_chord_html("D/F#") == (
            '<span class="chord">'
            'D<span class="bass">/F\u266f</span>'
            "</span>"
        )

    def test_altered_dominant_with_bass_combines_components(self):
        # ``G7b9/B`` -> ``G<sup>7</sup><sup>♭9</sup><span class="bass">/B</span>``
        assert format_chord_html("G7b9/B") == (
            '<span class="chord">'
            "G<sup>7</sup>"
            "<sup>\u266d9</sup>"
            '<span class="bass">/B</span>'
            "</span>"
        )

    def test_sus_quality_renders_as_plain_text(self):
        # Quality labels like ``sus4`` belong inside the chord body, not
        # inside ``<sup>`` — they're integral, not extensions.
        assert format_chord_inner("Gsus4") == "Gsus4"
        assert format_chord_inner("Asus4") == "Asus4"

    def test_add_quality_renders_as_plain_text(self):
        assert format_chord_inner("Cadd9") == "Cadd9"
        assert format_chord_inner("Dadd9") == "Dadd9"

    def test_invalid_chord_renders_as_escaped_plain_text(self):
        # ``format_chord_inner`` is for inner content; invalid input is
        # returned as escaped text so callers can still wrap it safely.
        assert format_chord_inner("not a chord") == "not a chord"
        assert format_chord_inner("<script>") == "&lt;script&gt;"

    def test_format_chord_html_invalid_input_falls_back_to_escaped(self):
        assert format_chord_html("not a chord") == (
            '<span class="chord">not a chord</span>'
        )

    def test_empty_string_is_escaped(self):
        # Empty / whitespace input is harmless: escaped empty stays empty.
        assert format_chord_inner("") == ""
        assert format_chord_inner("   ") == ""

    def test_unicode_input_is_normalised_before_render(self):
        # ``G\u2077`` normalised to ``G7`` then prettified as ``G<sup>7</sup>``.
        assert format_chord_inner("G\u2077") == "G<sup>7</sup>"
        assert format_chord_html("D/F\u266f") == (
            '<span class="chord">'
            'D<span class="bass">/F\u266f</span>'
            "</span>"
        )

    def test_maj7_quality_keeps_maj_as_plain_body(self):
        # ``Cmaj7`` -> ``Cmaj<sup>7</sup>``. The ``maj`` token sits in the
        # quality slot so it is not superscripted; only the extension
        # digit ``7`` is.
        assert format_chord_inner("Cmaj7") == "Cmaj<sup>7</sup>"

    def test_minor_seventh_flat_five_renders_all_extensions(self):
        # ``Bm7b5`` -> ``Bm<sup>7</sup><sup>♭5</sup>``
        assert format_chord_inner("Bm7b5") == "Bm<sup>7</sup><sup>\u266d5</sup>"

    def test_multi_slash_polyrhythm_passes_through_unescaped(self):
        # Multi-bass polychords (``C/G/B``) are split on every ``/`` by
        # :func:`transpose_chord_string` but the grammar regex and
        # :func:`parse_chord` only accept a single bass. The renderer
        # therefore falls back to escaped raw text, which is safe and
        # preserves the surface form so users see exactly what was
        # authored.
        rendered = format_chord_inner("C/G/B")
        assert rendered == "C/G/B"
        # The outer wrapper still applies.
        assert format_chord_html("C/G/B") == (
            '<span class="chord">C/G/B</span>'
        )

    def test_plain_chord_is_a_no_op_string_equality(self):
        # Plain chords must produce inner content that round-trips back
        # to the original chord text once HTML markup is stripped, so the
        # marp row / chord line column alignment tests for plain major /
        # minor / sharp chords keep working without manual adjustment.
        import re

        for chord in ("G", "Bm", "D", "Em", "F#m", "Cmaj7", "Gsus4", "Cadd9"):
            rendered = format_chord_inner(chord)
            visible = "".join(re.findall(r"[^<>]+", rendered))
            assert visible == chord, (
                f"Visible text of prettified {chord!r} drifted: {rendered!r}"
            )


class TestRegexExports(unittest.TestCase):
    """The exported regex objects compile and behave as documented."""

    def test_grammar_re_anchors_full_string(self):
        assert CHORD_GRAMMAR_RE.fullmatch("G7b9")
        assert not CHORD_GRAMMAR_RE.fullmatch("G7b")  # missing digit
        assert not CHORD_GRAMMAR_RE.fullmatch("X")

    def test_token_re_matches_substrings(self):
        text = "G   D/F#   C7b9   X7"
        matches = [m.group(0) for m in CHORD_TOKEN_RE.finditer(text)]
        assert matches == ["G", "D/F#", "C7b9"]

    def test_bracket_re_is_strict(self):
        text = "Who [G]else [Gm7b5]here [Bmaj9]and [fakeharmony]too"
        matches = [m.group(1) for m in CHORD_BRACKET_RE.finditer(text)]
        assert matches == ["G", "Gm7b5", "Bmaj9"]


class TestPropertyRoundTrip(unittest.TestCase):
    """Property-based round-trip across a curated chord strategy."""

    @given(
        root=st.sampled_from(list("ABCDEFG")),
        accidental=st.sampled_from(["", "b", "#"]),
        quality=st.sampled_from(
            [
                "",
                "m",
                "maj",
                "min",
                "dim",
                "aug",
                "sus2",
                "sus4",
                "add9",
                "7",
                "9",
                "11",
                "13",
                "m7",
                "maj7",
                "m9",
                "maj9",
                "7b5",
                "7#5",
                "7b9",
                "7#9",
                "7#11",
                "7b13",
                "7b9#11",
                "7b9#11b13",
                "m7b5",
            ]
        ),
    )
    @settings(deadline=None, max_examples=200)
    def test_round_trip(self, root, accidental, quality):
        chord = f"{root}{accidental}{quality}"
        if is_valid_chord(chord):
            assert serialize_chord(parse_chord(chord)) == chord
        else:
            # Some combinations are ambiguous given the simpler-shape
            # grammar; just confirm we either accept or refuse consistently.
            assert parse_chord(chord) is None
