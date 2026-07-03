# 🧪 Testing Guide

## Running Tests

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run a specific test file
uv run pytest tests/test_search.py

# Run a specific test case
uv run pytest tests/test_search.py::TestSearchFunctionality::test_url_formatting
```

---

## Test Structure

Tests live in `tests/` and follow the `test_*.py` naming convention so pytest discovers them automatically.

```
tests/
├── test_search.py        ← Tests for the registered scraper helpers in src/utils/search.py
└── test_yaml_converter.py ← Tests for src/utils/yaml_converter.py
```

---

## Current Test Coverage

### `tests/test_search.py` — `TestSearchFunctionality`

| Test | What it covers |
|------|---------------|
| `test_url_formatting` | `format_worship_together_url()` — per-source URL slug generation for the default scraper; new sources ship their own |
| `test_successful_song_search` | `search_song()` happy path with a mocked 200 response |
| `test_failed_song_search` | `search_song()` returns `None` on a network error (`RequestException`) |
| `test_missing_elements` | `search_song()` returns `None` when the page lacks expected HTML structure |
| `test_lyrics_extraction` | `search_song()` correctly extracts and structures sections from the default scraper's source HTML |

> The `format_worship_together_url()` helper is retained today because it ships as the default scraper's per-source URL slug builder. New scrapers register their own per-source slug helper alongside it in `src/utils/search.py`. Once a second scraper is wired in, helper names will move behind per-source adapters.

---

## Testing Philosophy

### 1. No Real Network Calls
Tests must **never** make real HTTP requests. Always mock `requests.get` using `unittest.mock.patch`:

```python
@patch('requests.get')
def test_something(self, mock_get):
    mock_response = MagicMock()
    mock_response.text = "<html>...</html>"
    mock_response.status_code = 200
    mock_get.return_value = mock_response
    ...
```

### 2. Test the Public Interface, Not Implementation Details
Test what a function returns, not how it works internally. Prefer asserting on the shape and values of the returned dict over testing private helpers.

### 3. Cover Edge Cases for Transposition
Chord transposition has many edge cases. When adding transposition tests, include:

- Same key (no transposition)
- Upward shift (e.g. C → G, +7 semitones)
- Downward shift (e.g. G → C, +5 semitones via wrapping)
- Enharmonic equivalents (e.g. original key `A#` → target key `Bb`)
- Bass notes (e.g. `C/G`, `Eb/Bb`)
- Complex chord suffixes (e.g. `Dm7`, `Gsus4`, `Faug`)
- Flat keys (target key `Bb`, `Eb`, `Ab`, `Db`, `Gb`)

---

## What to Test When Adding New Features

### New Scraper (new song source)
- URL/slug generation for the new source
- Successful parse of the expected HTML structure
- Graceful failure (returns `None`) when the response is malformed
- Section grouping correctness (sections are named correctly, lines are in the right order)
- Chord transposition still works through the new source's data
- The new scraper is registered alongside the default in `src/utils/search.py`

### New API Endpoint
Use Flask's test client:

```python
import unittest
from src.main import app

class TestMyEndpoint(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_happy_path(self):
        response = self.app.get('/api/my_endpoint?param=value')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('expected_key', data)

    def test_missing_required_param(self):
        response = self.app.get('/api/my_endpoint')
        self.assertEqual(response.status_code, 400)
```

### Slide Generation (yaml → marp → html)
When `search_song()` produces a chart, the live preview and downloaded deck both flow through `src/utils/yaml_converter.py → src/utils/marp_generator.py → src/utils/html_renderer.py`. Cover at least:
- Converted `SongYAML` round-trips through `convert_to_yaml()`; section names, types, and `arrangement` ordering preserved (`tests/test_yaml_converter.py`)
- Transposition preserve lyric text and chord positions across the chromatic scale (`tests/test_yaml_converter.py::TestTranspositionProperties`)
- The default scraper + any new scraper both feed the same dict shape into the YAML pipeline

---

## Linting

```bash
uv run ruff check .
uv run ruff format .
```

Ruff is configured in `pyproject.toml`. Fix lint errors before committing.

---

## Continuous Integration

There is currently no CI pipeline configured. To add one, a GitHub Actions workflow would look like:

```yaml
# .github/workflows/test.yml
name: Test
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync
      - run: uv run pytest
      - run: uv run ruff check .
```
