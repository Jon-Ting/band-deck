# Band Deck Slide Generator

Reusable skill package for generating band-practice decks from song requests, sourced metadata, lyrics/chords, ChordPro, canonical YAML, Marp Markdown, and rendered outputs.

The workflow is source-traced and conservative: do not invent lyrics, chords, authors, arrangements, or copyright details.

Practice decks are the default output: chords render above lyrics, section slides show now/next/after context instead of the full song map, and pagination is disabled. Use review mode when checking metadata, sources, licence state, or arrangement correctness before rehearsal.

Long lyric sections split across continuation slides by default. The generator keeps chord/lyric pairs together, repeats the section context on each continuation slide, and avoids shrinking below practice-readable font floors. YAML can set global render defaults, and each arrangement entry can override `max_line_pairs_per_slide` and chart font sizes for the slides generated from that entry.

## Target Architecture

```text
Band Deck Slide Generator Skill
  Metadata Sourcing Module
  Lyrics and Chords Sourcing Module
  ChordPro Normalisation Module
  Arrangement Module
  Deck Input Builder
  Marp Deck Generator
  Renderer
  QA/Validation
```

## Files

```text
schema/song-deck.schema.yaml
docs/source-and-copyright.md
docs/workflow.md
docs/validation-checklist.md
docs/arrangement-rules.md
docs/chordpro-normalisation.md
docs/marp-style-guide.md
scripts/band_deck_generator/
scripts/band_deck_helpers.py
scripts/update_render_docs.py
scripts/yaml_to_marp.py
scripts/validate_deck.py
scripts/render_marp.sh
templates/practice-deck.marp.md
```

## Standard Commands

Validate canonical YAML:

```bash
python band-deck-slide-generator/scripts/validate_deck.py song.yaml
```

Generate Marp:

```bash
python band-deck-slide-generator/scripts/yaml_to_marp.py song.yaml --output song.marp.md
```

Render outputs:

```bash
band-deck-slide-generator/scripts/render_marp.sh song.marp.md html
band-deck-slide-generator/scripts/render_marp.sh song.marp.md pdf
```

## Canonical YAML

The canonical deck input uses these top-level fields:

```yaml
request:
metadata:
sources:
normalised_chordpro:
arrangement:
render:
deck:
validation:
verification:
```

Use `schema/song-deck.schema.yaml` as the contract between modules. Non-canonical top-level shapes are rejected instead of being adapted.

Global practice defaults live under top-level `render`:

<!-- render-options:start -->
```yaml
render:
  max_line_pairs_per_slide: 6
  font_size_px: 28
```

Supported chart font sizes: 22–38px.
<!-- render-options:end -->

Per-slide-group overrides live on arrangement entries:

```yaml
arrangement:
  sequence:
    - section: Verse
      render:
        max_line_pairs_per_slide: 4
        font_size_px: 26
        chord_font_px: 22
```

## Copyright Caution

Store full lyrics/chords only when supplied by the user or covered by the user's licence/workflow. Otherwise use placeholders and record human review requirements.
