# ChordPro Normalisation

The ChordPro normalisation module converts sourced charts into consistent sectioned lines.

## Section Shape

```yaml
normalised_chordpro:
  source_format: chordpro
  sections:
    Verse 1:
      type: verse
      lyric_status: user-supplied
      lines:
        - chordpro: "[G]<licensed lyric line>"
```

## Rules

- Preserve user-supplied lyric text exactly. Do not rewrite, paraphrase, localise, correct spelling, alter punctuation, or normalise capitalisation in lyrics.
- Preserve all user-supplied chords exactly unless asked to transpose.
- Do not add missing lyrics or chords.
- Convert inline chords to `[Chord]lyric` format.
- Use Unicode superscript characters for chord extensions/annotations and repetition ordinals when filling YAML, rather than HTML tags. For example, write `[G⁷]`, `[Cˢᵘˢ⁴]`, `1ˢᵗ time`, and `2ⁿᵈ time` instead of `[G7]`, `[Csus4]`, `1st time`, and `2nd time` when the superscripted form improves readability.
- Store instrumental progressions as bars when possible.
- Split sections by musical function: intro, verse, pre-chorus, chorus, bridge, tag, ending.
- Store uncertainty in `validation.human_review_required`.

## Instrumentals

For instrumental sections, prefer bar structure over spacing-only chord lines:

```yaml
IntroTurn:
  type: instrumental
  display_title: Intro / Turnaround
  repeat: 2
  bars:
    - [Bm, G, D, A]
```

## Chord Handling

Accept common symbols such as:

```text
G D/F# Am Cadd9 Bb F#m7 Asus4
```

Use superscript for compact chord details where helpful:

```text
G⁷ D/F♯ Am Cᵃᵈᵈ⁹ B♭ F♯ᵐ⁷ Aˢᵘˢ⁴
```

Use superscript ordinals for repetition notes in cues or practice notes:

```yaml
cue: 1ˢᵗ time soft, 2ⁿᵈ time full
```

If a chord is unusual but plausible, keep it and flag it for review. If transposition is requested, record source key, target key, and method in `normalised_chordpro.transposition`.
