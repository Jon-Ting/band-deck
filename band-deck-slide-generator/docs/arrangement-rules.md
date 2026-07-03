# Arrangement Rules

The arrangement module turns sourced or user-supplied song order into a clear sequence for rehearsal slides.

## Inputs

- user-provided arrangement;
- chart-provided arrangement;
- section names found in the ChordPro content;
- practice cues such as intro, tag, stop, repeat, or ending.

## Rules

- Preserve the user's arrangement when supplied.
- Do not guess an arrangement unless the user asks for a generated draft.
- When generating a draft, mark `arrangement.source: generated`.
- Expand compact repeats only when they are unambiguous.
- Keep cue-only items in the sequence only when they affect rehearsal navigation.
- Flag any section named in the arrangement that has no lyrics/chords or cue.
- Make repeated sections occurrence-aware when cues differ by occurrence.
- Use `display_title` on sections when the internal ID is machine-style, such as `IntroTurn`.

## Canonical Examples

Compact request:

```text
Intro, Verse x2, Chorus, Bridge x2, Chorus, Ending
```

Canonical YAML:

```yaml
arrangement:
  source: user-supplied
  sequence:
    - section: Intro
      cue: Instrumental intro
    - section: Verse
    - section: Verse
    - section: Chorus
    - section: Bridge
    - section: Bridge
    - section: Chorus
    - section: Ending
      cue: Final stop
```

## Labelling

- Use exact section names in YAML.
- Use `label` on arrangement entries for occurrence labels such as `Chorus 1 of 2`.
- Use `cue` on the occurrence where the cue applies, not on the shared section definition.
- Use compact labels in slide song maps: `V`, `C`, `B`, `Tag`, `End`.
- Label repeats as `Verse 1 of 2` or `Bridge x2` when useful.
- Prefer clear names over clever abbreviations when the section is unusual.

Occurrence-aware repeat:

```yaml
arrangement:
  source: user-supplied
  sequence:
    - section: Verse 3
    - section: Chorus
      label: Chorus 1 of 2
      cue: Repeat chorus; do not go to Verse 4 yet.
    - section: Chorus
      label: Chorus 2 of 2
      cue: Build; next is Verse 4.
```
