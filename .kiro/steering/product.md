# Band-Deck — Product Overview

Band-deck is a Flask web application for musicians. It fetches song lyrics and chords from the internet, optionally transposes the chords to a target key, and generates a ready-to-present slide deck.

## Core User Flows

1. **Search** — enter a song name, optional artist, and optional target key → scrapes internet, transposes chords, generates structured YAML, and renders an HTML preview in the browser
2. **Edit** — adjust the arrangement order, edit section content in the song editor, and re-render the preview live via `/api/regenerate`
3. **Validate** — structural errors, overflow warnings, and licensing reminders surface automatically via `/api/validate` after each preview render
4. **Download** — download the current song in one of four formats: HTML slide deck, Marp markdown, YAML source, or PDF
5. **Save** — persist a slide to the server library (stored as `{yaml, marp, html}` by default; PDF optional); saved slides are listed in the library panel
6. **Compile** — select saved slides and bundle them into a single HTML deck with a clickable index via `POST /api/compile`

## Key Constraints

- Current data source is Worship Together only (scraping `chord-pro-line` HTML)
- Chord transposition must preserve sharp/flat conventions and handle slash chords (e.g. `C/G`)
- HTML rendering depends on Marp CLI being available on the server; `/api/health` reports its availability
- Saved-slide format set is `{yaml, marp, html}`; PDF is optional. `pptx` is not a valid format — the PowerPoint pipeline has been retired
