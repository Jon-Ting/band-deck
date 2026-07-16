# Validation Checklist

Run this checklist before finalising a generated deck.

## Identity And Metadata

- [ ] Title matches the user's request or chosen canonical title.
- [ ] Authors are present or marked `unknown`.
- [ ] License number is present or marked `unknown`.
- [ ] Copyright text is present or marked `requires review`.
- [ ] Target key appears in YAML and on every section slide.
- [ ] BPM and time signature are present or marked `unknown`.
- [ ] Capo is present or marked `none` or `unknown`.
- [ ] Optional: `metadata.search_name` mirrors the user-input title from `request`.
- [ ] Optional: `metadata.artist` mirrors the user-input artist from `request`.
- [ ] Optional: `metadata.highest_note` / `metadata.lowest_note` are in scientific pitch notation (`C5`, `A3`, `F#4`) or `unknown`/`none`.
- [ ] Optional: `metadata.source_urls` aggregates the URLs referenced from `sources.metadata[]`.
- [ ] Optional: top-level `practice_notes` keys match arrangement section names (plus `general`).

## Sources

- [ ] Metadata sources are recorded.
- [ ] Lyrics/chords sources are recorded.
- [ ] Arrangement source is recorded or marked `generated`.
- [ ] Source confidence is recorded for uncertain fields.
- [ ] External content has a human copyright/licence review note.

## ChordPro And Arrangement

- [ ] Every arrangement item maps to a section or cue.
- [ ] Repeated sections are expanded or labelled clearly.
- [ ] Chords remain attached to the intended lyric line.
- [ ] No lyrics were invented.
- [ ] No chords were invented.
- [ ] Transposition, if any, is disclosed with source and target keys.
- [ ] Unusual chords are flagged, not deleted.

## Deck And Render

- [ ] Overview slide shows title, authors, key, BPM, time signature, capo, and song map.
- [ ] Section slides show current section and next section.
- [ ] Cues are visible without crowding lyric/chord lines.
- [ ] Long sections are split at chord/lyric pair boundaries before text is shrunk.
- [ ] Continuation slides repeat metadata and now/next/after context.
- [ ] Lyrics are not rendered below 28px and chords are not rendered below 22px in practice mode.
- [ ] Rendered HTML/PDF has no clipped lyrics or overlapping text.
- [ ] Final review notes list every uncertainty.

## Commands

```bash
python band-deck-slide-generator/scripts/validate_deck.py song.yaml
python band-deck-slide-generator/scripts/yaml_to_marp.py song.yaml
band-deck-slide-generator/scripts/render_marp.sh song.marp.md html
```
