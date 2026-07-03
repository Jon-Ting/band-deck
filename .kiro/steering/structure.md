# Project Structure

## Pipeline
```
Search → chordpro_parser → yaml_converter → SongYAML → marp_generator → html_renderer → slide_storage
```

## Key Modules (`src/utils/`)
| Module | Purpose |
|---|---|
| `search.py` | Worship Together scraping + transposition |
| `chordpro_parser.py` | chord-pro HTML → raw chart data |
| `yaml_models.py` | `SongYAML` / `SongSection` dataclasses |
| `yaml_converter.py` | Raw chart data → SongYAML |
| `yaml_api.py` | YAML generation API logic |
| `marp_generator.py` | SongYAML → Marp markdown |
| `html_renderer.py` | Marp markdown → HTML via Marp CLI |
| `preview.py` | Orchestrates YAML → Marp → HTML |
| `song_validator.py` | Structural errors, overflow warnings, licensing |
| `arrangement_engine.py` | Propose/validate/update section arrangement |
| `slide_storage.py` | UUID-based save/list/get/update/delete |
| `compiler.py` | Bundle saved slides → single HTML deck with index |
| `migration.py` | Backfill YAML/Marp/HTML for legacy slides |

## Architectural Patterns
- **Blueprint routing** — all routes in `src/routes/api.py`, registered on app under `/api`
- **Utility modules** — business logic in `src/utils/` only; routes are thin wrappers
- **UUID file storage** — each slide stored as `<uuid>.{yaml,marp,html}` in `data/saved_slides/`; no database
- Routes import from utils, never the reverse

## Key Conventions
- Song title: prefer `search_name` (user input) over `title` (scraped) — preserve everywhere
- `data/saved_slides/` is runtime data — never commit its contents
- Save formats: `{yaml, marp, html}` always; `pdf` optional; `pptx` is retired
