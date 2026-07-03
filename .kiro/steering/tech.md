# Tech Stack

## Language & Runtime
- Python 3.10+ (managed via `.python-version`)
- Dependency management: `uv` with `uv.lock` (committed, fully reproducible installs)

## Frameworks & Libraries
| Library | Purpose |
|---|---|
| Flask >= 3.0 | Web server and API routing |
| python-pptx >= 1.0 | PowerPoint generation |
| requests >= 2.30 | HTTP scraping from Worship Together |
| beautifulsoup4 >= 4.12 | HTML parsing of chord-pro-line content |
| pytest >= 7 + pytest-cov | Testing |
| ruff >= 0.4 | Linting and formatting |

## Build System
- `hatchling` as the PEP 517 build backend
- Dev dependencies are in a PEP 735 `[dependency-groups]` `dev` group in `pyproject.toml`

## Common Commands
```bash
uv sync                        # Install all deps (runtime + dev) into .venv
uv sync --no-dev               # Runtime only

uv run python src/main.py      # Start dev server on port 5000
uv run pytest                  # Run test suite
uv run pytest --cov            # Run tests with coverage
uv run ruff check .            # Lint
uv run ruff format .           # Format
```

## Test Configuration
- Test files follow the `test_*.py` naming convention

## Runtime Notes
- Server runs on `0.0.0.0:5000` in debug mode by default
- Rate limiting is implemented in-process (dict-based); no external cache/Redis required
