# 🏗️ Band-Deck Architecture

## Overview

Band-Deck is a single-server Flask web application with a vanilla JS frontend. There is no build step, no database, and no external message queue. All song slides are persisted as files on local disk.

```
Browser (Vanilla JS)
       │  HTTP (JSON / file download)
       ▼
Flask App
       │
       ├── routes/api.py               ← HTTP boundary; thin handlers only
       │
       ├── utils/search.py             ← Pluggable chord/lyric scrapers + chord transposition
       ├── utils/yaml_converter.py     ← Raw chart data → typed SongYAML
       ├── utils/yaml_api.py           ← /generate_yaml response builder
       ├── utils/marp_generator.py     ← SongYAML → Marp markdown
       ├── utils/html_renderer.py      ← Marp markdown → HTML via Marp CLI
       ├── utils/preview.py            ← /preview & /regenerate orchestration
       ├── utils/song_validator.py     ← Validation + overflow estimation
       ├── utils/arrangement_engine.py ← Section arrangement proposal/validation
       ├── utils/compiler.py           ← Multi-slide HTML deck assembly
       └── utils/slide_storage.py      ← File-based persistence
                 │
                 └── data/saved_slides/   ← .yaml / .marp.md / .html / .json artefacts
```

---

## Module Responsibilities

### `src/routes/api.py`
- Defines the Flask Blueprint `api_bp` mounted at `/api/`.
- Each route handler is a thin wrapper: validate input → call a utility → return JSON or stream a file.
- **Does not** contain business logic.

### `src/utils/search.py`
- Fetches song HTML from any registered chord/lyric scraper, using a spoofed `User-Agent` per request. New sources register their own fetch + parse helpers; source selection lives in `search_song()`.
- Parses `<div class="chord-pro-line">` / `<div class="chord-pro-segment">` elements (the granularity used by the current bootstrap source) to extract interleaved chord + lyric pairs, grouped into named sections.
- Transposes chords: reads the original key from source metadata (the current bootstrap reads `<meta property="cludo:originalKey">`), calculates semitone shift, and rewrites each chord symbol.
- Returns a plain dict; knows nothing about PowerPoint or HTTP.

### `src/utils/yaml_converter.py`
- Converts the raw scraped output from `search.py` (plain-text sections with chord/lyric lines) into a typed `SongYAML` dataclass tree (`src/utils/yaml_models.py`).
- Infers section types (`verse`, `chorus`, `bridge`, `intro`, …) from section names via `infer_section_type()`.

### `src/utils/marp_generator.py`
- `generate_marp(song, style, options)` — emits a Marp markdown deck for either the `practice` (chord-over-lyric) or `performance` (lyric only) preset.
- Anchors chord columns above the syllable they apply to so the chord stays aligned with its lyric in the rendered HTML.
- Emits an embedded `<style>` block with the band's typography preferences (see `_css_template` for the exact rule set).

### `src/utils/html_renderer.py`
- `render_html(marp_markdown, output_path, timeout)` — shells out to the `marp` CLI to convert Marp markdown into a self-contained HTML file.
- `verify_marp_cli()` — used by `/api/health` to report whether the CLI is on the `PATH`; the API returns `status: degraded` if it is missing.
- Enforces an upper bound (`MAX_MARKDOWN_BYTES`) and a per-call timeout (`DEFAULT_RENDER_TIMEOUT_SECONDS`) so a malicious or pathological input cannot run unbounded.

### `src/utils/preview.py`
- `generate_preview(payload)` / `generate_regeneration(payload)` — orchestrate the `SongYAML → Marp → HTML` pipeline for the `/api/preview` and `/api/regenerate` endpoints.

### `src/utils/compiler.py`
- `compile_slides_html(slide_ids)` — merges saved slides into a single HTML deck with a clickable index page. The output is an HTML file (not a binary presentation): slides load via anchors pointing at the per-deck `<section id="…">` blocks.

### `src/utils/slide_storage.py`
- Each saved slide is a **UUID-named artefact set**: `<uuid>.yaml`, `<uuid>.marp.md`, `<uuid>.html`, plus the `<uuid>.json` metadata sidecar (optional `<uuid>.pdf` if the renderer can produce one).
- The JSON sidecar stores `{id, title, artist, key, filenames, created_at, updated_at, …}` — it is the source of truth for listing, downloading, and updating.
- Each storage function (`save_slide`, `list_slides`, `get_slide`, `delete_slide`, `update_slide`, `get_slide_file`, `clear_temp_files`) reads/writes under `SLIDES_DIR` (defined as `<project_root>/data/saved_slides/`).

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
All my life    You have been faithful
```

---

## Chord Transposition Algorithm

1. Extract `original_key` from the scraped page (the active scraper exposes it however its source page provides it).
2. Compute `semitones = (target_index - original_index) % 12` using the chromatic scale.
3. For each chord token (regex `[A-G][b#]?...`):
   - Split on `/` to handle bass notes (e.g. `C/G → E/B`).
   - Look up root note index, add semitones mod 12, look up new root.
   - Preserve suffix (e.g. `m7`, `sus4`, `dim`).
4. Use flats if the target key contains `b` (e.g. `Bb`, `Eb`).
5. Handle enharmonic equivalents (e.g. `C#` ↔ `Db`) via fallback mapping in `get_note_index()`.

---

## Slide Overflow Estimation

Overflow warnings come from `src/utils/song_validator.py:estimate_slide_overflow(song, style)` rather than from a Python-side PowerPoint layout picker. The estimator counts chord + lyric lines per section in the chosen style (`practice`, `performance`, `simple`) and flags any section whose line count exceeds the configured per-slide cap.

- Each section is treated as a contiguous block (not interleaved) so narrative flow is preserved across slides.
- The estimator surfaces a `suggestion` string per overflow (e.g. split verse, reduce repeats, switch style) that the editor UI displays next to the offending section.

---

## Rate Limiting

- Rate limiting is currently disabled.
- For public or multi-user deployments, add a limiter at the Flask or reverse-proxy layer with shared external state, such as `Flask-Limiter` backed by Redis.

---

## File Storage Layout

```
data/saved_slides/
├── <uuid>.yaml       ← Structured SongYAML source
├── <uuid>.marp.md    ← Marp markdown deck
├── <uuid>.html       ← Rendered HTML deck (Marp CLI output)
├── <uuid>.json       ← Metadata sidecar
├── ...
└── (compiled.html    ← Compiled deck filename emitted by /api/compile)
```

`clear_temp_files()` deletes everything in `data/saved_slides/` whose extension is not in `{.yaml, .marp.md, .html, .json}` (PDF artefacts are also kept if present).

---

## Frontend (Vanilla JS)

- Single-page app in `src/static/index.html` + `src/static/js/{app,slide_preview,song_editor,arrangement_editor}.js`.
- No framework, no build step.
- Communicates with the Flask API via `fetch()`.
- Live preview is rendered by loading the `html_content` field returned by `POST /api/preview` (and `/api/regenerate` after edits) into an `<iframe srcdoc="…">` in the editor pane.

---

## Known Limitations & Future Considerations

| Area | Current | Future Option |
|------|---------|--------------|
| Song source | Pluggable chord/lyric scrapers, one wired in by default | Add more public chord/lyric sources (e.g. Ultimate Guitar, OpenSong, Chordie) |
| Storage | Local disk | Swap `slide_storage.py` for a DB-backed implementation |
| Rate limiting | Disabled | Flask-Limiter + Redis |
| Multi-user | Not supported | Session-scoped slide libraries |
| Auth | None | Add auth if multi-user is needed |
