# Source And Copyright

This skill can help organise sourced song data. It should retrieve lyrics/chords from accessible internet sources when needed, then record provenance and flag copyright review.

## Source Records

Record sources in canonical YAML under `sources.metadata`, `sources.lyrics_chords`, and `sources.arrangement`.

Each source record should include:

- `label`: human-readable source name;
- `provider`: site, publisher, user, or chart provider;
- `url`: source URL when available;
- `accessed_on`: date checked;
- `confidence`: `confirmed`, `likely`, `uncertain`, or `unknown`;
- `copyright_sensitive`: `true` for lyric/chord sources;
- `notes`: what was verified or what still needs review.

## Sourcing Rules

- Prefer user-supplied, licensed, official, or otherwise accessible public chart sources.
- If the user has not supplied lyrics/chords, search the internet and retrieve the best accessible source you can find.
- Do not bypass logins, paywalls, robots protections, or site terms.
- Do not invent lyrics, chords, authors, license numbers, BPM, time signature, or copyright details.
- If a source disagrees with user input, preserve the user input and add a validation note.
- If the source is uncertain, set confidence to `uncertain` and add a human review item.

## Lyrics And Chords

Store retrieved lyrics/chords in the working deck when they come from accessible internet sources and are needed for transformation. If you only have a partial or uncertain source, use placeholders for the missing parts and record what still needs review.

Render lyric text exactly as supplied in the input. Do not rewrite, paraphrase, localise, correct spelling, alter punctuation, or normalise capitalisation in lyrics.

For examples and templates, use placeholders rather than reproducing full copyrighted songs.

When the source is public but copyright-sensitive, keep the content in the internal working deck and flag it for human review rather than refusing to source it.

## License

Include license number (CCLI, ISRC, BMI/ASCAP work ID, etc.) and copyright fields when available. Treat licence compliance as a human review item unless the user provides explicit confirmation.
