# 🤝 Contributing to Band-Deck

## Getting Started

1. **Clone and install** (see [README.md](README.md) for full setup instructions):
   ```bash
   git clone <your-repo-url> Band-Deck
   cd Band-Deck
   uv sync
   ```

2. **Run the server** to verify your setup:
   ```bash
   uv run python src/main.py
   ```

3. **Run tests** before and after changes:
   ```bash
   uv run pytest
   ```

---

## Code Style

- **Formatter / Linter**: [Ruff](https://docs.astral.sh/ruff/). Run before committing:
  ```bash
  uv run ruff check .
  uv run ruff format .
  ```
- **Python version**: 3.10+. Use type hints where practical.
- **Docstrings**: Use triple-quoted docstrings for all public functions. Describe parameters and return values in plain English (no strict format required).
- **Logging**: Use `logging.getLogger(__name__)` — never `print()` in library code. `print()` is acceptable in CLI/debug scripts only.

---

## Project Layout Conventions

| Directory | What goes here |
|-----------|---------------|
| `src/routes/` | Flask Blueprint route handlers only — no business logic |
| `src/utils/` | Pure business logic — search, PPTX generation, slide storage |
| `src/static/` | Frontend (HTML, CSS, JS) — no build step, vanilla only |
| `tests/` | `test_*.py` files; mirror the `src/` module structure |
| `docs/` | User-facing and developer documentation |

---

## Naming Conventions

- **Files**: `snake_case.py`
- **Classes**: `PascalCase`
- **Functions / variables**: `snake_case`
- **Constants**: `UPPER_SNAKE_CASE`
- **PPTX filenames**: generated as `snake_case` from song title (see `to_snake_case()` in `pptx_generator.py`)

---

## Adding a New API Endpoint

1. Add the route handler to `src/routes/api.py`.
2. Keep business logic in a `src/utils/` module — routes should only call utilities and return responses.
3. Apply the existing rate-limiting pattern if the endpoint is public-facing.
4. Add at least one test in `tests/test_<module>.py`.
5. Update `docs/API.md` with the new endpoint.

---

## Adding a New Song Source

Currently only [Worship Together](https://www.worshiptogether.com/) is supported. To add a new source:

1. Add a new scraper in `src/utils/search.py` (or a new `src/utils/<source>_search.py`).
2. Return the same dict shape as `search_song()`:
   ```python
   {
       'title': str,
       'search_name': str,
       'artist': str,
       'content': str,    # Sectioned lyrics/chords as plain text
       'source_url': str,
       'original_key': str | None,
   }
   ```
3. Wire it into the `/api/search` and `/api/download` endpoints in `api.py`.
4. Document the new source in `docs/ARCHITECTURE.md`.

---

## Testing Guidelines

- Use `unittest.mock.patch` to mock HTTP requests — tests must **not** make real network calls.
- Test files live in `tests/` and must be named `test_*.py`.
- Aim to cover: happy path, missing/malformed data, transposition edge cases (e.g., enharmonic keys).
- See `docs/TESTING.md` for a full breakdown of the test strategy.

---

## Dependency Management

- Add runtime dependencies to `[project.dependencies]` in `pyproject.toml`.
- Add dev-only dependencies to `[dependency-groups] dev` in `pyproject.toml`.
- After changing dependencies, regenerate the lockfile:
  ```bash
  uv lock
  uv sync
  ```
- **Commit `uv.lock`** — it is pinned for reproducibility.

---

## Pull Request Checklist

- [ ] `uv run pytest` passes
- [ ] `uv run ruff check .` passes
- [ ] New/changed endpoints are documented in `docs/API.md`
- [ ] Significant design decisions are recorded in `docs/DECISIONS.md`
- [ ] No real network calls in tests
