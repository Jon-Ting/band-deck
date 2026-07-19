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
- **Use plain ASCII chord grammar (described below), not Unicode superscripts.** The shared grammar in `src/utils/chord_parser.py` recognises everything from `G` and `Bm` through `Bm7b5`, `G7b9`, `G7b9#11`, and `G7b9#11b13`. Unicode-typed chord text from older sources is normalised transparently on load.
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

### Sustained Beats with `-`

Use `-` inside a bar cell to indicate the previous chord rings through that beat. Cell contents are rendered inline between bars `| ... |`, separated by spaces, so `-[Em, -, E, -]` renders as `| Em - E - |`.

```yaml
IntroTurn:
  type: instrumental
  repeat: 1
  bars:
    - [Em, -, E, -]   # Em sustains for beats 1–2, E sustains for beats 3–4
    - [G, D, C, -]    # G, D, C, then rest
```

List-based bars are always rendered with cells separated by spaces inside `| ... |` (e.g. `[G, D, C, G]` → `| G D C G |`). Single-string bars pass through unchanged, so use them when you need custom formatting.

### Grouping Bars with `bars_per_line`

To keep several bars on the same rendered line (so the bar boundary `|` stays visible for counting), set `bars_per_line` inside the section's `render` block. The default is `1`, which preserves the existing one-bar-per-line behaviour.

```yaml
Intro:
  type: instrumental
  repeat: 1
  render:
    bars_per_line: 2
  bars:
    - [Em, -, E, -]
    - [A, D, G, D]
    - [B, E]
    - [C, F]
```

With `bars_per_line: 2`, the rendered output becomes:

```
| Em - E - | A D G D |
| B E | C F |
```

Adjacent bars share a single `|` between them. The schema clamps `bars_per_line` to `>= 1`; values of `0`, negative numbers, and non-integers fall back to `1`.

## Chord Handling

Use the unified ASCII chord grammar owned by `src/utils/chord_parser.py`. The application auto-detects alterations, so author what the chart actually says without Unicode tricks.

### Accepted chord grammar

```
[A-G]                            Root letter.
[b#]?                            Optional flat or sharp on the root.
(m | maj | min |                 Quality (optional; default = major).
 dim | aug |
 sus[24]? | add[0-9]+)?
([b#]?[0-9]+)*                  Extensions and alterations
                                  (one or more ``[b#]?``+digits tokens).
(/[A-G][b#]?)?                   Optional slash bass.
```

Examples (all valid under the grammar):

```text
G        Bm       D/F#     Cmaj7    Asus4
Cadd9    Bm7b5    G7b9     G7#9b13  G7b9#11
F#m7b5   Ebsus4   Gadd9    C7/Bb    G7b9#11b13
```

### How alterations parse

`G7b9` means "G dominant seventh with a flat ninth" — the parser
splits it as `root=G, quality=major (default), extensions=[(7), (b,9)]`.
Stacks read left-to-right, so `G7b9#11b13` is a fully altered
dominant that marches through every alteration.

Avoid authoring chords as bare `b5` / `#9` (without an extension
prefix) — write them as `7b5`, `7#9`, `7b9#11` etc. to keep the
intent unambiguous.

### Slash-bass and double-slur

`D/F#` means "D with F# in the bass". `G7/B` means "G dominant with
B in the bass". Both root and bass shift cleanly under transposition.

### Legacy Unicode

Incoming data that still carries Unicode typography (`G\u2077`,
`D/F\u266f`, `F\u266fm\u2077`) loads correctly via
`normalize_chord_superscripts`, but always author new material in
ASCII to keep YAML diffs readable.

### Repetition ordinals

Cues and practice notes should use plain ASCII ordinals
(`1st time soft, 2nd time full`) \u2014 the older `1\u02e2\u1d57 time` superscript form
is no longer recommended because it complicates search and grep.

If a chord is unusual but plausible, keep it and flag it for review. If transposition is requested, record source key, target key, and method in `normalised_chordpro.transposition`.
