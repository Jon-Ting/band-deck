# 🏗️ Band-Deck Architecture

## Overview

Band-Deck is a single-server Flask web application with a vanilla JS frontend. There is no build step, no database, and no external message queue. All song slides are persisted as files on local disk.

```
Browser (Vanilla JS)
       │  HTTP (JSON / file download)
       ▼
Flask App  ──  Rate Limiter (per-IP, in-memory)
       │
       ├── routes/api.py        ← HTTP boundary; thin handlers only
       │
       ├── utils/search.py      ← Scraping + chord transposition
       ├── utils/pptx_generator.py  ← Slide generation
       └── utils/slide_storage.py   ← File-based persistence
                 │
                 └── src/saved_slides/   ← .pptx + .json pairs on disk
```

---

## Module Responsibilities

### `src/routes/api.py`
- Defines the Flask Blueprint `api_bp` mounted at `/api/`.
- Each route handler is a thin wrapper: validate input → call a utility → return JSON or stream a file.
- Rate limiting is enforced here via a simple per-IP timestamp dict (`request_timestamps`).
- **Does not** contain business logic.

### `src/utils/search.py`
- Fetches song HTML from Worship Together using a spoofed `User-Agent`.
- Parses `<div class="chord-pro-line">` / `<div class="chord-pro-segment">` elements to extract interleaved chord + lyric pairs, grouped into named sections.
- Transposes chords: reads the original key from `<meta property="cludo:originalKey">`, calculates semitone shift, and rewrites each chord symbol.
- Returns a plain dict; knows nothing about PowerPoint or HTTP.

### `src/utils/pptx_generator.py`
- `PowerPointGenerator.create_slide(song_data)` — builds a 10×5.625 inch slide.
  - Determines column count (2–4) and font size (4–10pt) adaptively based on total line count.
  - Distributes sections as contiguous blocks across columns left-to-right.
  - Uses Consolas (monospace) font so chord alignment above lyrics is preserved.
- `LyricsFormatter.parse_lyrics_and_chords()` — secondary parser for raw text content.
- `format_worship_together_url()` — URL slug builder (also used by `search.py`).

### `src/utils/slide_storage.py`
- Each saved slide is a **UUID-named pair**: `<uuid>.pptx` + `<uuid>.json`.
- The JSON sidecar stores `{id, title, artist, key, filename}` — it is the source of truth for listing and metadata.
- `compile_slides_with_index()` — merges all individual `.pptx` files into one presentation with a clickable index slide. Clickable areas are transparent rectangles with `click_action.target_slide` set.

---

## Key Data Structures

### Song Data Dict (passed between modules)
```python
{
    'title': str,           # Title from the scraped page <h1>
    'search_name': str,     # User's original search input (used on slides)
    'artist': str,
    'content': str,         # Plain-text sections separated by \n\n
                            # Each section: header line, then alternating chord/lyric lines
    'source_url': str,
    'original_key': str | None,
    'key': str | None,      # Target key (added by API layer)
}
```

### `content` String Format
```
Verse 1
G          Em
I love You Lord
C          D
For Your mercy never fails me

Chorus
G    D    Em   C
All my life You have been faithful
```

---

## Chord Transposition Algorithm

1. Extract `original_key` from the Worship Together page meta tag.
2. Compute `semitones = (target_index - original_index) % 12` using the chromatic scale.
3. For each chord token (regex `[A-G][b#]?...`):
   - Split on `/` to handle bass notes (e.g. `C/G → E/B`).
   - Look up root note index, add semitones mod 12, look up new root.
   - Preserve suffix (e.g. `m7`, `sus4`, `dim`).
4. Use flats if the target key contains `b` (e.g. `Bb`, `Eb`).
5. Handle enharmonic equivalents (e.g. `C#` ↔ `Db`) via fallback mapping in `get_note_index()`.

---

## Adaptive Slide Layout Algorithm

```
for num_cols in [2, 3, 4]:
    for font_size in [10, 9, ..., 4]:
        if total_lines ≤ num_cols × (available_height / line_height):
            use this combination
            break
```

- Sections are distributed as contiguous blocks (not interleaved) to preserve narrative flow.
- A 1.25× line-height multiplier compensates for PowerPoint's internal spacing.

---

## Rate Limiting

- Implemented as an in-memory dict: `{ip: [timestamps]}`.
- Limit: ~10 requests/minute per IP (one request per 5 seconds via `RATE_LIMIT_SECONDS = 5`).
- **Caveat**: State is lost on server restart and does not scale across multiple processes. Suitable for personal/small-team use. For production, replace with `Flask-Limiter` backed by Redis.

---

## File Storage Layout

```
src/saved_slides/
├── <uuid>.pptx       ← Individual song slide
├── <uuid>.json       ← Metadata sidecar
├── ...
└── all_songs.pptx    ← Compiled deck (overwritten on each compile)
```

`clear_temp_files()` deletes everything that is **not** `.pptx` or `.json`.

---

## Frontend (Vanilla JS)

- Single-page app in `src/static/index.html` + `src/static/js/app.js`.
- No framework, no build step.
- Communicates with the Flask API via `fetch()`.
- Preview is rendered by parsing the `pptx_preview.sections` JSON returned by `/api/search`.

---

## Known Limitations & Future Considerations

| Area | Current | Future Option |
|------|---------|--------------|
| Song source | Worship Together only | Add more sources (e.g. Ultimate Guitar, OpenSong) |
| Storage | Local disk | Swap `slide_storage.py` for a DB-backed implementation |
| Rate limiting | In-memory per-IP | Flask-Limiter + Redis |
| Multi-user | Not supported | Session-scoped slide libraries |
| Auth | None | Add auth if multi-user is needed |
