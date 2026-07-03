# Band Deck Workflow

Use this workflow when turning a song request into a rehearsal deck.

## Pipeline

1. Parse the request: capture title, artist, target key, output formats, and any metadata the user supplied.
2. Identify the song: resolve likely canonical title and artist before sourcing content.
3. Source metadata: find or verify authors, license number, key, BPM, time signature, capo, and copyright fields when not supplied.
4. Source lyrics and chords: gather user-supplied, licensed, official, or otherwise accessible public lyrics/chords, and record every source.
5. Normalise to ChordPro: convert each section into `[Chord]lyric` lines without adding missing content.
6. Generate or revise arrangement: expand repeats, decide cue slides, and flag uncertain order.
7. Build canonical YAML: write `request`, `metadata`, `sources`, `normalised_chordpro`, `arrangement`, `render`, `deck`, `validation`, and `verification`. Do not rely on legacy top-level fallback fields.
8. Generate Marp: run `scripts/yaml_to_marp.py` or follow `templates/practice-deck.marp.md`; split long sections according to `render.overflow_strategy`.
9. Render deliverables: use `scripts/render_marp.sh` for HTML or PDF when Marp CLI is installed.
10. Validate: run `scripts/validate_deck.py` and complete `docs/validation-checklist.md`.

## Module Contracts

| Module | Input | Output |
| --- | --- | --- |
| Metadata Sourcing | title, artist, supplied fields | verified metadata with sources |
| Lyrics and Chords Sourcing | identified song | sourced lyrics/chords with provenance |
| ChordPro Normalisation | raw chart text | sectioned ChordPro lines |
| Arrangement | source chart and user notes | ordered section sequence |
| Deck Input Builder | all prior outputs | canonical YAML |
| Marp Deck Generator | canonical YAML | `.marp.md` |
| Renderer | `.marp.md` | HTML, PDF |
| QA/Validation | YAML and rendered files | errors, warnings, human review notes |

## Stop Conditions

Ask for clarification or use placeholders when:

- the title match is ambiguous;
- lyrics, chords, authors, key, BPM, or time signature cannot be sourced confidently from accessible sources;
- the requested arrangement conflicts with the sourced chart;
- a source cannot be cited or appears to be unauthorised;
- transposition is requested but source and target keys are unclear.
