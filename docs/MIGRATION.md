# Band-Deck 5-Phase Migration Guide

This document captures the rollout strategy for moving Band-Deck from a
PowerPoint-only pipeline to an HTML/Marp slide deck generator while
maintaining backward compatibility with the existing PPTX workflow.

The migration is staged so each phase ships behind feature flags, retains
the old behaviour, and adds the new capability alongside it. After
Phase 5, PPTX becomes a legacy export; HTML is the recommended primary
format.

---

## Phase 1: Parallel Implementation

**Goal:** add the new HTML/Marp pipeline without breaking PPTX.

**Shipped in this phase:**
- ChordPro parser with round-trip preservation (`src/utils/chordpro_parser.py`).
- YAML data models and JSON schema (`src/utils/yaml_models.py`,
  `src/schema/song.schema.json`).
- YAML conversion utility (`src/utils/yaml_converter.py`).
- Marp markdown generator (`src/utils/marp_generator.py`).
- HTML renderer wrapping the Marp CLI (`src/utils/html_renderer.py`).

**What does NOT change:**
- `/api/search` still returns the legacy search payload.
- `/api/download` still serves a `.pptx`.
- `slide_storage.py` keeps using the same on-disk layout.

---

## Phase 2: Preview Integration

**Goal:** surface a live HTML preview alongside the PPTX download.

**Shipped:**
- `/api/generate_yaml`, `/api/preview`, `/api/regenerate`.
- Frontend `SlidePreview` and `SongEditor` classes
  (`src/static/js/slide_preview.js`, `src/static/js/song_editor.js`).
- Multi-format download endpoint register (HTML/Marp/YAML/PDF/PPTX).

**Operational note:** the Marp CLI must be installed
(`npm install -g @marp-team/marp-cli`) before the preview endpoint
returns a rendered HTML deck. See [`DEPLOYMENT.md`](DEPLOYMENT.md).

---

## Phase 3: Storage Migration

**Goal:** persist every saved slide in YAML + Marp + HTML in addition to
the original PPTX file.

**Shipped:**
- Multi-format persistence (`slide_storage.update_slide`,
  `save_slide` with a `formats` list).
- New `/api/saved_slide/<id>/download/<format>` endpoint.
- Batch migration utility (`src/utils/migration.py`) that walks the
  existing saved slides and generates the new formats. The legacy PPTX
  is preserved.
- HTML batch compilation (`src/utils/compiler.py`,
  `/api/compile`).

**Operator notes:**
- Migration is idempotent. Re-running it without `force=True` skips
  slides that already have YAML artefacts.
- Marp CLI failures are isolated per-slide: a failed slide gets a static
  HTML placeholder so the rest of the deck still renders. Review the
  logs from `migrate_existing_slides()` and address gaps manually.

---

## Phase 4: Feature Parity

**Goal:** achieve feature parity with the existing PPTX workflow and
introduce capabilities unique to HTML (live preview, edit-regenerate).

**Shipped:**
- `ArrangementEngine` (`src/utils/arrangement_engine.py`) with proposal,
  validation, and update operations.
- `SongValidator` (`src/utils/song_validator.py`) with the
  completeness, chord symbol, arrangement referential integrity, and
  slide overflow checks.
- Frontend `ArrangementEditor` (`src/static/js/arrangement_editor.js`)
  with drag-and-drop reordering, repeat counts, and intro/interlude/ending
  note fields.
- Slide style customisation (practice/performance/simple) — see below.

### Slide styles

| Style       | Metadata bar | Song map on every slide | Practice notes | Font size |
| :---------- | :----------- | :---------------------- | :------------- | :-------- |
| practice    | yes          | yes (top strip + sidebar) | yes          | 24px      |
| performance | hidden       | sidebar only            | hidden         | 28px      |
| simple      | hidden       | hidden                  | hidden         | 30px      |

Set the style on each saved slide via the SongEditor switch in the
arrangement panel, or pass `style=` to `/api/regenerate`,
`/api/preview`, and `/api/download/html`.

### Song map navigation cues

- Practice style shows the full song map in a top navigation strip on
  every section slide with the current position highlighted
  (`.navigation-strip .current`).
- All styles highlight the current position in the sidebar (`<span
  class="current">`).
- The next section name is always shown (`Next: <name>` or `Next: End`
  on the final slide).

### Validation warnings

`/api/validate` returns four distinct arrays:

- `errors` — missing title, bad chord symbols, arrangement references
  to non-existent sections; render these into a non-dismissible panel.
- `warnings` — missing authors, missing target key, etc.
- `overflow` — sections that may not fit on a single slide for the
  chosen style, each with a split/reduce suggestion.
- `licensing_warnings` — CCLI / copyright / permission reminders,
  always including the unconditional "verify CCLI permission" message.

Pass `check_placeholders=true` to additionally flag
`TODO` / `TBD` / `XXX` / `[placeholder]` / `{value}` markers.

---

## Phase 5: Deprecation Path

**Goal:** phase out PPTX generation in favour of HTML.

**Status:** PPTX remains available, with explicit deprecation signals:

- `/api/download` now emits:
  - `Deprecation: true`
  - `Sunset: 2027-07-03`
  - `Link: </api/download/html>; rel="successor-version"; ...`
  - `X-Band-Deck-Deprecation-Notice: PPTX export is legacy; HTML is the recommended format.`

- The frontend `<option value="pptx">` carries an explanatory `title`
  attribute and the user guide recommends HTML.

**Operator actions:**
- Monitor traffic on `/api/download` (still accepted until the Sunset
  date). Drop the route once zero unique callers remain for one billing
  cycle.
- Encourage users via the in-app notice and the user guide to
  re-download saved slides as HTML.

---

## Troubleshooting Marp CLI

If you see `RenderError: Marp CLI timed out` or
`RenderError: Marp CLI failed: ...`:

1. Verify the CLI is installed and on the PATH:
   ```bash
   marp --version
   # Expected: something like "Marp CLI v3.x.x"
   ```
2. If not, install:
   ```bash
   # Requires Node.js >= 16
   npm install -g @marp-team/marp-cli
   ```
3. Run the health check endpoint:
   ```bash
   curl http://localhost:5000/api/health
   ```
   The `marp_cli.available` flag is `true` when the CLI is found.
4. If Marp renders succeed but the generated HTML contains script tags
   or `javascript:` URLs, the markdown violated the safety pattern in
   `html_renderer.UNSAFE_MARKDOWN_PATTERNS`. Sanitize user input
   upstream before calling `render_html`.

For deeper deployment notes, see [`DEPLOYMENT.md`](DEPLOYMENT.md).
