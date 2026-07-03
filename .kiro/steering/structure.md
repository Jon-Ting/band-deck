# Project Structure

```
band-deck/
├── src/
│   ├── main.py                       # Flask app factory, static serving
│   ├── routes/
│   │   └── api.py                    # All API endpoints as a Flask Blueprint (url_prefix=/api)
│   ├── schema/
│   │   └── song.schema.json          # JSON schema for SongYAML validation
│   ├── utils/
│   │   ├── search.py                 # Worship Together scraping
│   │   ├── chordpro_parser.py        # Parse chord-pro HTML → raw chart data
│   │   ├── yaml_models.py            # SongYAML and SongSection dataclasses
│   │   ├── yaml_converter.py         # Raw chart data → SongYAML
│   │   ├── yaml_api.py               # YAML generation API logic
│   │   ├── marp_generator.py         # SongYAML → Marp markdown
│   │   ├── html_renderer.py          # Marp markdown → HTML via Marp CLI
│   │   ├── preview.py                # Orchestrate preview pipeline (YAML → Marp → HTML)
│   │   ├── song_validator.py         # Structural errors, overflow warnings, licensing check
│   │   ├── arrangement_engine.py     # Propose/validate/update section arrangement
│   │   ├── slide_storage.py          # UUID-based save/list/get/update/delete
│   │   ├── compiler.py               # Bundle saved slides → single HTML deck with index
│   │   └── migration.py              # Backfill YAML/Marp/HTML for legacy slides
│   ├── static/
│   │   ├── index.html                # Single-page frontend
│   │   ├── js/
│   │   │   ├── app.js                # Main UI — search, save, library, compile
│   │   │   ├── slide_preview.js      # Preview panel rendering and controls
│   │   │   ├── song_editor.js        # YAML section editor with live validation
│   │   │   └── arrangement_editor.js # Drag-and-drop section arrangement
│   │   └── css/
│   │       └── style.css
├── data/
│   └── saved_slides/                 # Runtime data directory — YAML/Marp/HTML files per saved slide
│       └── compiled_*.html           # Compiled deck outputs (timestamp-based filenames)
├── tests/
│   ├── test_search.py                # Scraping and transposition
│   ├── test_chordpro_parser.py       # Chord-pro HTML parsing
│   ├── test_yaml_converter.py        # Raw chart → SongYAML conversion
│   ├── test_marp_generator.py        # SongYAML → Marp markdown
│   ├── test_html_renderer.py         # Marp → HTML rendering
│   ├── test_song_validator.py        # Validation rules (errors + warnings)
│   ├── test_arrangement_engine.py    # Arrangement proposal and updates
│   ├── test_slide_storage.py         # Save/list/get/update/delete operations
│   ├── test_compiler.py              # Multi-slide compilation
│   ├── test_migration.py             # Legacy slide migration
│   ├── test_api_*.py                 # API endpoint integration tests
│   ├── test_integration.py           # Full end-to-end flow
│   └── *.js                          # Frontend JS unit tests
├── docs/
│   ├── ARCHITECTURE.md               # System design and data flow
│   ├── API.md                        # Endpoint reference
│   ├── DATA_MODEL.md                 # SongYAML spec and section types
│   ├── MIGRATION.md                  # Legacy PPTX → YAML/Marp/HTML migration guide
│   ├── TESTING.md                    # Test strategy and coverage
│   ├── DEPLOYMENT.md                 # Production setup
│   ├── DECISIONS.md                  # ADRs and technical rationale
│   └── USER_GUIDE.md                 # End-user feature walkthrough
├── AGENTS.md                         # Agent-specific quickstart and conventions
├── pyproject.toml                    # Project metadata, dependencies, pytest + ruff config
├── uv.lock                           # Committed lockfile
└── .python-version                   # Pins Python version for uv
```

## Architectural Patterns

- **Blueprint routing** — all API routes live in `src/routes/api.py` and are registered on the app in `main.py` under `/api`
- **Utility modules** — business logic is split into focused modules under `src/utils/`; routes import from utils, never the reverse
- **UUID file storage** — each saved slide is stored as `<uuid>.yaml`, `<uuid>.marp`, `<uuid>.html` (and optional `<uuid>.pdf`) in `data/saved_slides/`; no database
- **Pipeline architecture** — search → parse → convert → validate → generate Marp → render HTML → save; each stage is a discrete module

## Key Conventions

- Song titles displayed to users come from `search_name` (user input) falling back to `title` (scraped) — preserve this priority everywhere
- `data/saved_slides/` is a runtime directory — never commit `.yaml`, `.marp`, `.html`, `.pdf` files from it (excluded in `pyproject.toml` sdist config and `.gitignore`)
