# 🎶 Band-Deck

## What is Band-Deck?

Band-Deck turns a song name (and an optional artist and key) into a ready-to-project PowerPoint with lyrics and chords. It pulls chords and lyrics from public sources, transposes to the key you ask for, and lays out clean slides — so worship leaders, band directors, music teachers, and solo performers can focus on the music instead of the formatting. Save slides to a personal library, batch them into a single clickable deck, and keep the music moving.

A Python Flask web application that creates musician-friendly PowerPoint slides with lyrics and chords for songs of any genre in one click. Search a song by name and (optionally) artist, transpose to any key, preview, and download a ready-to-use `.pptx` file.

![Status](https://img.shields.io/badge/status-active-success.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![Scope](https://img.shields.io/badge/scope-personal%20%26%20educational-blue.svg)

---

## ✨ Features

- 🔍 **Smart search** — Looks up songs by name and (optional) artist across supported public chord/lyric sources, with plans to broaden coverage across more genres
- 🎼 **Automatic chord transposition** — Request any key; chords are rewritten on the fly
- 📊 **Adaptive slide layout** — Content is auto-distributed across 2–4 columns with font size that fits the slide
- 👁️ **Live preview** — See how the slide will look before downloading
- 💾 **Slide library** — Save generated slides locally; re-download or delete any time
- 📦 **Compile all slides** — Bundle every saved song into a single `.pptx` with a clickable index page
- 🧹 **Cleanup** — One-click removal of temporary files
- ⚖️ **Rate-limited** — Public `/api/` endpoints are rate-limited per client (~10 req/min)

---

## 🧰 Tech Stack

- **Backend:** [Flask](https://flask.palletsprojects.com/) (Python 3.10+)
- **PowerPoint generation:** [python-pptx](https://python-pptx.readthedocs.io/)
- **HTML parsing:** [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/)
- **HTTP:** [requests](https://requests.readthedocs.io/)
- **Data validation:** [Pydantic](https://docs.pydantic.dev/)
- **Frontend:** Vanilla HTML / CSS / JavaScript (no build step)

---

## 📋 Prerequisites

- **[uv](https://docs.astral.sh/uv/)** (manages Python, virtual environments, and dependencies — replaces `pip` + `venv` + `pyenv`)
  > Install uv once: `curl -LsSf https://astral.sh/uv/install.sh | sh` (or `pip install uv`, or `brew install uv`).
- A modern web browser

> The repository ships with sample song files in `src/saved_slides/` — these are templates you can use or replace. The `.python-version` file pins Python 3.10 so `uv` picks the right interpreter automatically.

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

> Prefer plain `pip`? `uv` is optional — dev tooling is now in a PEP 735 group (`[dependency-groups]`), so pip needs at least **24.2** and the `--group` flag (e.g. `pip install --group dev`) to install it; for runtime deps alone, `pip install -e .` is unaffected.

**Contributors**: when you change dependencies in `pyproject.toml`, regenerate the lockfile first, then apply:

```bash
uv lock
uv sync
```

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
3. **Download PowerPoint** — Click to download a single-song `.pptx`.
4. **Save Slide** — Persist the slide locally for later use or batch compilation.
5. **Saved Slides** — Browse, re-download, or delete saved slides.
6. **Download All as PowerPoint** — Compile every saved slide into one `.pptx` with a clickable index page at the front.
7. **Cleanup Temporary Files** — Remove temp artifacts.

---

## 🔌 API Reference

All endpoints live under `/api/`. The public-facing endpoints are rate-limited (~10 requests/minute per client).

| Method | Endpoint                       | Description                                                              |
| :----- | :----------------------------- | :----------------------------------------------------------------------- |
| GET    | `/api/search`                  | Search a song. Params: `song`, optional `artist`, optional `key`         |
| GET    | `/api/download`                | Generate and stream a `.pptx`. Same params as `/api/search`             |
| POST   | `/api/save_slide`              | Save a slide JSON payload. Returns metadata including a UUID             |
| GET    | `/api/saved_slides`            | List metadata for every saved slide                                     |
| GET    | `/api/saved_slide/<slide_id>`  | Download the `.pptx` for a previously saved slide                        |
| DELETE | `/api/saved_slide/<slide_id>`  | Delete a saved slide                                                     |
| GET    | `/api/compile_slides`          | Build one `.pptx` containing all saved slides plus a clickable index     |
| POST   | `/api/clear_temp_files`        | Remove non-`.pptx`/`.json` temporary files in `src/saved_slides/`        |

### Example: Search for a song

```bash
curl "http://localhost:5000/api/search?song=Goodness%20of%20God&artist=Bethel&key=G"
```

The response is a JSON object containing `title`, `artist`, `content` (raw sectioned lyrics/chords), `original_key`, and a `pptx_preview` block.

---

## 🗂️ Project Structure

```
Band-Deck/
├── pyproject.toml             # Packaging metadata & runtime dependencies (hatchling + uv)
├── uv.lock                    # Resolved dependency lockfile (committed for reproducibility)
├── .python-version            # Pins Python 3.10 for `uv`
├── README.md                  # ← you are here
├── docs/
│   └── USER_GUIDE.md           # End-user guide for the deployed app
├── .gitignore
├── src/
│   ├── main.py                # Flask app entry point
│   ├── run_tests.py           # Test runner
│   ├── __init__.py
│   ├── routes/
│   │   └── api.py             # API blueprint (search, download, save_slide, etc.)
│   ├── utils/
│   │   ├── pptx_generator.py  # PowerPoint creation + transposition helpers
│   │   ├── search.py          # Song-source scraper + chord transposition
│   │   └── slide_storage.py   # Saves, lists, deletes, and compiles slides
│   ├── static/                # Frontend (HTML, CSS, JS)
│   │   ├── index.html
│   │   ├── css/style.css
│   │   └── js/app.js
│   └── saved_slides/          # Per-request .pptx + .json metadata + compiled outputs
└── tests/
    └── test_*.py              # Unit tests (add new files here)
```

---

## ⚖️ Legal & Copyright Notice

For full legal terms (intended use, licensing responsibilities, redistribution, template-data caveats), see [`docs/USER_GUIDE.md` → Legal Considerations](docs/USER_GUIDE.md#legal-considerations).

---

## 🛠️ Development Notes

- **Rate limiting** is enforced via a simple per-IP counter in `src/main.py`. Suitable for personal/small-team use; replace with a proper limiter (e.g. `Flask-Limiter`) for production.
- **Logging** defaults to `INFO`. Adjust `logging.basicConfig(level=...)` in the modules to suit your environment.
- **Slide storage** is local-disk based. For multi-user or production deployments, swap `src/utils/slide_storage.py` for a database-backed implementation.

---

## 🙏 Acknowledgements

- Lyrics and chords are sourced from [Worship Together](https://www.worshiptogether.com/).
- PowerPoint generation powered by [`python-pptx`](https://python-pptx.readthedocs.io/).
- Built with [Flask](https://flask.palletsprojects.com/).

---

> 💡 **Tip:** Run `python src/main.py` in debug mode (default) for auto-reload during development. Toggle it off (`debug=False`) for any production-like deployment.
