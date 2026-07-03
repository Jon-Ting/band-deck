# Band-Deck Agent Guide

Flask app — scrapes internet, transposes chords, generates HTML/Marp/YAML slide decks. See `docs/` for architecture, API reference, and data model.

**Start server:** `uv run python src/main.py` (port 5000)

## Data Flow

```
Search → chordpro_parser → SongYAML → marp_generator → html_renderer → slide_storage
```

## Key Modules (`src/utils/`)

| Module | Purpose |
|---|---|
| `search.py` | Internet scraping, chord extraction, transposition |
| `yaml_models.py` | `SongYAML` / `SongSection` dataclasses — core data model |
| `marp_generator.py` | `SongYAML` → Marp markdown |
| `html_renderer.py` | Marp markdown → HTML via Marp CLI |
| `song_validator.py` | Structural errors, overflow warnings, licensing check |
| `arrangement_engine.py` | Propose/validate/update section arrangement |
| `compiler.py` | Bundle saved slides → single HTML deck with index |
| `slide_storage.py` | UUID-based save/list/get/update/delete |
| `migration.py` | Backfill YAML/Marp/HTML for legacy slides (idempotent) |

## API (`/api/*`)

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/search` | Scrape; params: `song`, `artist`, `key` |
| `GET` | `/health` | Marp CLI status + storage stats |
| `POST` | `/generate_yaml` | Raw chart data → SongYAML |
| `POST` | `/preview` | SongYAML → rendered HTML |
| `POST` | `/regenerate` | Edited SongYAML → re-rendered HTML |
| `POST` | `/validate` | SongYAML → errors + warnings |
| `POST` | `/save_slide` | Persist as yaml + marp + html (pdf optional) |
| `GET` | `/saved_slides` | List saved slides |
| `GET` | `/saved_slide/<id>/download/<format>` | Download yaml / marp / html / pdf |
| `DELETE/PUT` | `/saved_slide/<id>` | Delete or update a slide |
| `POST` | `/compile` | Combine slides → single HTML deck |

## Conventions

- Song title: prefer `search_name` (user input) over `title` (scraped).
- Business logic in `src/utils/` only; route handlers are thin wrappers.
- Save formats: `{yaml, marp, html}` always; `pdf` optional. `pptx` is retired.
- `src/saved_slides/` is runtime data — never commit its contents.
