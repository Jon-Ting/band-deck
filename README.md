# 🎶 Band-Deck

## What is Band-Deck?

Band-Deck turns a song name (and an optional artist and key) into a ready-to-project HTML / Marp slide deck with lyrics and chords. It pulls chords and lyrics from public sources, transposes to the key you ask for, and lays out clean, click-throughable slides — so you can focus on the music instead of the formatting. Save slides to a personal library as YAML / Marp markdown / HTML, batch them into a single clickable deck, and keep the music moving.

A Python Flask web application that creates musician-friendly slides with lyrics and chords for songs of any genre in one click. Search a song by name and (optionally) artist, transpose to any key, preview the rendered deck in the browser, edit live, and download YAML, Marp markdown, or rendered HTML — all optimised for projection during services, concerts, rehearsals, or lessons.

![Status](https://img.shields.io/badge/status-active-success.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![Scope](https://img.shields.io/badge/scope-personal%20%26%20educational-blue.svg)

---

## ✨ Features

- 🔍 **Smart search** — Looks up songs by name and (optional) artist across supported public chord/lyric sources, with plans to broaden coverage across more genres
- 🎼 **Automatic chord transposition** — Request any key; chords are rewritten on the fly
- 📊 **Adaptive slide layout** — Content is auto-distributed across 2–4 columns with font size that fits the slide
- 👁️ **Live preview** — See how the slide will look before downloading
- 🌐 **HTML/Marp workflow** — Generates standalone Marp-driven HTML decks; preview in-browser, edit live, regenerate on blur
- 🎬 **Multiple slide styles** — Choose `practice`, `performance`, or `simple` style for each song
- 📝 **YAML editor** — Modify metadata, chords, lyrics, arrangement, and practice notes; the preview auto-updates after a 500 ms debounce
- 🔔 **Validation warnings** — Live errors, slide overflow, and licensing reminders surface in the editor
- 💾 **Slide library** — Save slides as YAML, Marp, HTML, or PDF; re-download or delete any time
- 📦 **Batch compilation** — Combine saved slides into a single HTML deck with a clickable index
- 🧹 **Cleanup** — One-click removal of temporary files
- ⚖️ **Unrestricted (for now)** — `/api/` endpoints have no per-client throttling; add `Flask-Limiter` or a reverse-proxy limiter before any public deployment

### Keyboard shortcuts (live preview)

| Key | Action |
| :-- | :----- |
| `→`, `Space`, `PageDown` | Next slide |
| `←`, `PageUp` | Previous slide |
| `F` | Toggle fullscreen |
| `P` | Toggle presenter mode (high-contrast sidebar, larger queue) |

---

## 🧰 Tech Stack

- **Backend:** [Flask](https://flask.palletsprojects.com/) (Python 3.10+)
- **HTML rendering:** [Marp CLI](https://github.com/marp-team/marp-cli) (Node.js)
- **HTML parsing:** [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/)
- **HTTP:** [requests](https://requests.readthedocs.io/)
- **Data validation:** [jsonschema](https://python-jsonschema.readthedocs.io/) + custom completeness checks
- **Frontend:** Vanilla HTML / CSS / JavaScript (no build step)

> The Marp CLI handles the final HTML render step. Install it once with `npm install -g @marp-team/marp-cli`. The `/api/health` endpoint reports whether the CLI is available.

---

## 📋 Prerequisites

- **[uv](https://docs.astral.sh/uv/)** (manages Python, virtual environments, and dependencies — replaces `pip` + `venv` + `pyenv`)
  > Install uv once: `curl -LsSf https://astral.sh/uv/install.sh | sh` (or `pip install uv`, or `brew install uv`).
- **Node.js 16+** for the Marp CLI (used by the HTML rendering pipeline)
- A modern web browser

> The repository ships with sample song files in `data/saved_slides/` — these are templates you can use or replace. The `.python-version` file pins Python 3.10 so `uv` picks the right interpreter automatically.

---

## 🚀 Installation

### 1. Clone the repository

```bash
git clone <your-repo-url> Band-Deck
cd Band-Deck
```

### 2. Install dependencies with uv

From the project root, `uv sync` creates a `.venv` virtual environment, installs every runtime dependency, and (by default) the PEP 735 `dev` group (pytest, ruff, etc.). The resolved versions are pinned in `uv.lock`, which is committed for reproducibility.

```bash
uv sync
```

For a production-like install without dev tooling, use:

```bash
uv sync --no-dev
```

**Contributors**: when you change dependencies in `pyproject.toml`, regenerate the lockfile first, then apply:

```bash
uv lock
uv sync
```

### 3. Install the Marp CLI (required for HTML rendering)

```bash
npm install -g @marp-team/marp-cli
```

`/api/health` will report `degraded` if the CLI is not on the PATH; users can still save YAML / Marp markdown even when HTML rendering is unavailable.

---

## ▶️ Running the App

> All commands below assume you ran `uv sync` first. If you'd rather activate the venv manually, use `source .venv/bin/activate` (macOS/Linux) or `.venv\Scripts\activate` (Windows) and drop the `uv run` prefix.

### Start the Flask server

From the project root:

```bash
uv run python src/main.py
```

The server starts on **http://localhost:5000**. Open that URL in your browser to access the web UI.

### Run the tests

```bash
uv run pytest
```

This discovers and executes all `test_*.py` files under the `tests/` directory.

### Lint with ruff

```bash
uv run ruff check .
```

---

## 🖥️ Using the Web UI

1. **Search** — Enter the song name (and optionally the artist and a target key like `C`, `G`, `F#`).
2. **Preview** — A live preview shows the slide layout and content.
3. **Edit** — Tweak metadata, lyrics, chords, arrangement, or practice notes; the preview auto-regenerates after 500 ms.
4. **Download** — Pick a format (HTML deck, Marp markdown, or YAML source) and download the rendered slide.
5. **Save Slide** — Persist the slide locally for later use or batch compilation.
6. **Saved Slides** — Browse, re-download, or delete saved slides.
7. **Batch Compile** — Combine saved slides into a single HTML deck with a clickable index page.
8. **Cleanup Temporary Files** — Remove temp artifacts.

---

## 🔌 API Reference

All endpoints live under `/api/`. **No rate limiting is enforced** at the application layer; see Development Notes for production guidance.

| Method | Endpoint                              | Description                                                      |
| :----- | :------------------------------------ | :--------------------------------------------------------------- |
| GET    | `/api/search`                         | Search a song. Params: `song`, optional `artist`, optional `key` |
| GET    | `/api/health`                         | Reports Marp CLI availability + storage usage                    |
| POST   | `/api/generate_yaml`                  | Build a typed SongYAML from raw search/scrape output             |
| POST   | `/api/preview`                        | Render an HTML preview deck from a SongYAML payload             |
| POST   | `/api/regenerate`                     | Re-render after edits to the SongYAML                            |
| POST   | `/api/validate`                       | Return validation errors, warnings, overflow, licensing notices  |
| POST   | `/api/save_slide`                     | Save one or more formats (yaml / marp / html / pdf)             |
| GET    | `/api/saved_slides`                   | List metadata for every saved slide                              |
| POST   | `/api/saved_slide/<id>` (PUT)         | Update a saved slide with new edited SongYAML data               |
| DELETE | `/api/saved_slide/<id>`               | Delete a saved slide                                             |
| GET    | `/api/saved_slide/<id>/download/<fmt>`| Download an already-saved slide in the requested format         |
| POST   | `/api/compile`                        | Combine multiple saved slides into a single HTML deck           |
| POST   | `/api/clear_temp_files`               | Remove non-format temporary files in `data/saved_slides/`         |

### Example: Search for a song

```bash
curl "http://localhost:5000/api/search?song=Goodness%20of%20God&artist=Bethel&key=G"
```

The response is a JSON object containing `title`, `artist`, `content` (raw sectioned lyrics/chords), `original_key`, and (if a target key was requested) `key`.

---

## 🗂️ Project Structure

```
Band-Deck/
├── pyproject.toml             # Packaging metadata & runtime dependencies (hatchling + uv)
├── uv.lock                    # Resolved dependency lockfile (committed for reproducibility)
├── .python-version            # Pins Python 3.10 for `uv`
├── README.md                  # ← you are here
├── docs/
│   ├── USER_GUIDE.md           # End-user guide for the deployed app
│   ├── DATA_MODEL.md           # SongYAML structure, on-disk format, metadata fields
│   ├── ARCHITECTURE.md         # Module responsibilities + data flow
│   ├── API.md                  # Request/response reference per endpoint
│   ├── TESTING.md              # Test strategy and fixtures
│   ├── DEPLOYMENT.md           # Operational notes (Marp CLI, health checks, ...)
│   ├── DECISIONS.md            # Design rationale for non-obvious choices
├── .gitignore
├── src/
│   ├── main.py                # Flask app entry point
│   ├── run_tests.py           # Test runner
│   ├── __init__.py
│   ├── routes/
│   │   └── api.py             # API blueprint (search, preview, save_slide, etc.)
│   ├── utils/
│   │   ├── search.py          # Song-source scraper + chord transposition
│   │   ├── marp_generator.py  # Marp markdown generation (practice/performance/simple)
│   │   ├── html_renderer.py   # Marp CLI subprocess + safety checks
│   │   ├── yaml_models.py     # SongYAML dataclasses and JSON schema
│   │   ├── yaml_converter.py  # Search → SongYAML conversion
│   │   ├── compiler.py        # Multi-slide HTML deck assembler
│   │   ├── migration.py       # Backfill legacy slides with YAML/Marp/HTML
│   │   └── slide_storage.py   # Saves, lists, deletes slides (multi-format)
│   ├── static/                # Frontend (HTML, CSS, JS)
│   │   ├── index.html
│   │   ├── css/style.css
│   │   └── js/{app,slide_preview,song_editor,arrangement_editor}.js
│   └── saved_slides/          # Per-slide .yaml + .marp.md + .html + .json metadata
└── tests/
    └── test_*.py              # Unit + integration tests (add new files here)
```

---

## ⚖️ Legal & Copyright Notice

For full legal terms (intended use, licensing responsibilities, redistribution, template-data caveats), see [`docs/USER_GUIDE.md` → Legal Considerations](docs/USER_GUIDE.md#legal-considerations).

---

## 🛠️ Development Notes

- **Rate limiting** is currently disabled. Add a proper external limiter (for example, `Flask-Limiter` backed by Redis) before any public deployment that needs request throttling.
- **Logging** defaults to `INFO`. Adjust `logging.basicConfig(level=...)` in the modules to suit your environment.
- **Slide storage** is local-disk based. For multi-user or production deployments, swap `src/utils/slide_storage.py` for a database-backed implementation.
- **Marp CLI** must be installed for HTML rendering; if missing the renderer falls back to a static HTML placeholder so the slide stays loadable.

---

## 🙏 Acknowledgements

- Band-Deck pulls lyrics and chords from any number of public chord/lyric sites on the internet; today a default scraper ships in `src/utils/search.py`.
- HTML rendering powered by [Marp CLI](https://github.com/marp-team/marp-cli).
- Built with [Flask](https://flask.palletsprojects.com/).

---

> 💡 **Tip:** Run `python src/main.py` in debug mode (default) for auto-reload during development. Toggle it off (`debug=False`) for any production-like deployment.
