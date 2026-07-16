---
name: band-deck-slide-generator
description: Use when generating band-practice slides from a song title, song metadata, sourced lyrics/chords, ChordPro, arrangements, canonical YAML, Marp Markdown, or rendered HTML/PDF deck requests.
---

# Band Deck Slide Generator Skill

Generate rehearsal-focused band decks from a song request through a modular, source-traced pipeline.

## Core Rules

- Do not invent lyrics, chords, authors, license numbers, keys, BPM, time signatures, or copyright details.
- Do not rewrite, paraphrase, localise, correct spelling, alter punctuation, or normalise capitalisation in lyrics. Render lyric text exactly as supplied in the input.
- Do not silently transpose chords.
- Do not guess arrangements unless the user asks for a generated draft.
- Cite or record sources for metadata, lyrics/chords, and arrangement.
- Retrieve lyrics/chords from accessible internet sources when the user has not supplied them, then record the source and mark the result for copyright/licence review.
- Produce canonical YAML before Marp or rendered outputs, and reject legacy/non-canonical deck shapes.
- When filling YAML, use Unicode superscript characters for chord extensions/annotations and repetition ordinals where musically relevant, because chart text is escaped before rendering. Examples: `[G⁷]`, `[D/F♯]`, `[Cˢᵘˢ⁴]`, `1ˢᵗ time`, `2ⁿᵈ time`.
- Default to `render.mode: practice` for rehearsal use. Use `review` only when the user is checking sources, metadata, verification status, or arrangement correctness before practice.
- In practice mode, render chords above lyrics, suppress pagination, and show only current/next/after context on section slides.
- For long sections, split slides at chord/lyric line-pair boundaries before shrinking text. Keep each chord line attached to its lyric line, repeat metadata/context on continuation slides, and use `cont.` labels.
- Mark uncertainty as `unknown`, `requires review`, or `human_review_required`.

## Pipeline

1. Parse the user's input: song title plus optional artist, key, metadata, arrangement, notes, and requested outputs.
2. Identify the requested song from the input. If multiple songs match, ask or mark the match uncertain.
3. Source missing metadata: authors, license, key, BPM, time signature, capo, copyright.
4. Source lyrics and chords, plus arrangement if available. Record every source.
5. Normalise lyrics/chords into sectioned ChordPro.
6. Generate or revise the arrangement sequence.
7. Produce canonical YAML matching `schema/song-deck.schema.yaml`.
8. Generate Marp Markdown from YAML.
9. Render HTML or PDF from Marp when requested.
10. Run validation checks and report human review items.

Read `docs/workflow.md` for the full module contract.

## Modules And Resources

| Module | Use |
| --- | --- |
| Metadata Sourcing | Read `docs/source-and-copyright.md`; fill `metadata` and `sources.metadata`. |
| Lyrics and Chords Sourcing | Read `docs/source-and-copyright.md`; fill `sources.lyrics_chords`. |
| ChordPro Normalisation | Read `docs/chordpro-normalisation.md`; fill `normalised_chordpro.sections`. |
| Arrangement | Read `docs/arrangement-rules.md`; fill `arrangement.sequence`. |
| Deck Input Builder | Validate against `schema/song-deck.schema.yaml`. |
| Marp Deck Generator | Use `scripts/yaml_to_marp.py` and `templates/practice-deck.marp.md`. |
| Renderer | Use `scripts/render_marp.sh` for one-off HTML/PDF renders or `scripts/regenerate_outputs.py` to refresh Marp and HTML from YAML together. |
| QA/Validation | Use `scripts/validate_deck.py` and `docs/validation-checklist.md`. |

## Canonical YAML

Canonical YAML is the only supported deck shape and must include:

```yaml
request:
metadata:
sources:
normalised_chordpro:
arrangement:
deck:
validation:
```

Prefer these optional fields when producing practice-ready decks:

<!-- render-options:start -->
```yaml
render:
  mode: practice
  chord_layout: above_lyrics
  show_full_song_map: false
  show_pagination: false
  overflow_strategy: split
  max_line_pairs_per_slide: 6
  font_size_px: 28
  continuation_labels: true

verification:
  lyrics: unverified
  chords: unverified
  ccli: unverified
```

Supported chart font sizes: 22–38px.
<!-- render-options:end -->

Set slide-specific layout overrides on arrangement entries when one section needs
different density or text sizing. These values override top-level `render`
defaults for the slides generated from that arrangement entry:

```yaml
arrangement:
  sequence:
    - section: Verse
      label: Verse small
      render:
        max_line_pairs_per_slide: 4
        font_size_px: 26
        chord_font_px: 22
    - section: Chorus
      label: Chorus big
      render:
        max_line_pairs_per_slide: 3
        font_size_px: 34
```

Use `font_size_px` as the shared chart font size. Use `lyric_font_px`,
`chord_font_px`, or `bar_font_px` only when lyrics, chords, or instrumental
bar charts need different sizing on that slide group.

Use `schema/song-deck.schema.yaml` for validation. Keep source confidence and review notes in the YAML, not only in chat. Do not pass legacy top-level shapes like `title` / `sections` / list-form `arrangement` directly to the generator scripts.

## Script Commands

```bash
python band-deck-slide-generator/scripts/validate_deck.py song.yaml
python band-deck-slide-generator/scripts/yaml_to_marp.py song.yaml
band-deck-slide-generator/scripts/render_marp.sh song.marp.md html
band-deck-slide-generator/scripts/render_marp.sh song.marp.md pdf
```

Use `scripts/regenerate_outputs.py song.yaml` when you want the script to regenerate both `song.marp.md` and `song.html`.

## Output Contract

Unless the user asks for only one artifact, return or create:

1. canonical YAML;
2. Marp Markdown;
3. requested rendered files;
4. validation result;
5. human review notes.

For internet-sourced content, include source labels/URLs and explicitly flag copyright-sensitive material for licence review. Retrieval is expected; the review flag does not block sourcing.
