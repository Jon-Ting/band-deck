# Marp Style Guide

Band practice decks should be dense enough for musicians and plain enough to read quickly.

## Slide Types

- Review overview: title, authors, key, BPM, time signature, capo, full song map, source warnings, verification notes.
- Practice overview: title, key, BPM, time signature, capo, full song map, unresolved warnings only.
- Section: current section, chord-over-lyric lines, now/next/after context, section cues.
- Cue: intro, instrumental, spoken cue, a cappella, stop, modulation, or ending.
- Final review: unresolved metadata, source, copyright, fit, or render issues.

## Layout

- Use 16:9.
- Put chorded lyrics in the main column, with chords above the lyric line.
- Put only now, next, after, and urgent cue information in the right column.
- Keep metadata visible on every section slide.
- Use red/orange for chords and blue for the current section marker.
- Avoid decorative backgrounds and imagery unless requested.
- Disable pagination in practice mode; section labels are the useful navigation.
- Keep the full arrangement map on the overview or review slide only.

## Practice Mode Defaults

```yaml
render:
  mode: practice
  chord_layout: above_lyrics
  show_full_song_map: false
  show_pagination: false
  overflow_strategy: split
  max_line_pairs_per_slide: 6
  font_size_px: 30
  min_lyric_font_px: 28
  min_chord_font_px: 22
  continuation_labels: true
  theme: band_deck_light
```

Use 30-36px lyric text, 24-30px chord text, and 34-40px section titles for projection readability.

Use arrangement-entry `render` blocks for slide-specific density or font sizing:

```yaml
arrangement:
  sequence:
    - section: Verse
      render:
        max_line_pairs_per_slide: 4
        font_size_px: 26
    - section: Chorus
      render:
        max_line_pairs_per_slide: 3
        font_size_px: 34
        chord_font_px: 30
```

Prefer `font_size_px` for shared chord/lyric sizing. Use `lyric_font_px`,
`chord_font_px`, and `bar_font_px` only when a slide needs separate sizing.

## Overflow Policy

- Split long lyric/chord sections before shrinking text.
- Split only at complete chord/lyric line-pair boundaries.
- Label continuation slides as `Verse 1 cont.`, `Verse 1 cont. 2`, etc.
- Repeat metadata and now/next/after context on every continuation slide.
- Put long cues on the first slide or a separate cue slide; do not let cue text crowd lyrics.
- Only shrink text after splitting, and do not go below 28px lyrics or 22px chords for practice projection.

## Rendering

Generate Marp first, then render:

```bash
python band-deck-slide-generator/scripts/yaml_to_marp.py song.yaml --output song.marp.md
band-deck-slide-generator/scripts/render_marp.sh song.marp.md html
band-deck-slide-generator/scripts/render_marp.sh song.marp.md pdf
```

After rendering, inspect each output for clipped lines, unreadable chords, missing slides, and unsupported HTML.
