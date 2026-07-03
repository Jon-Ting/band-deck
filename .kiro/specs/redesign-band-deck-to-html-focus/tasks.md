# Implementation Plan: HTML/Marp Slide Generation Redesign

## Overview

This plan implements the redesign of Band-Deck from a PowerPoint-focused application to an HTML slide deck generator using Marp markdown. The implementation follows a 5-phase migration strategy that maintains backward compatibility while adding new HTML/YAML capabilities.

## Tasks

- [x] 1. Phase 1: Parallel Implementation - Core Components
  - [x] 1.1 Install and verify Marp CLI dependency
    - Install Marp CLI: `npm install -g @marp-team/marp-cli`
    - Verify installation with version check
    - Document Node.js version requirement (>=16.0.0)
    - _Requirements: 9.1_
  
  - [x] 1.2 Create ChordPro parser with tokenization and position calculation
    - Create `src/utils/chordpro_parser.py` module
    - Implement `tokenize_chordpro()` function to split lines into chord/text tokens
    - Implement `calculate_positions()` to compute chord character positions
    - Implement `parse_chordpro()` as main entry point
    - Define `ChordProLine` and `ChordPosition` dataclasses
    - _Requirements: 5.1, 5.2, 5.3_
  
  - [x] 1.3 Write property test for ChordPro round-trip preservation
    - **Property 1: ChordPro Round-Trip Preservation**
    - **Validates: Requirements 5.5**
    - Use hypothesis to generate random lyric text and chord positions
    - Test: parse → reconstruct_brackets → parse produces equivalent result
    - Minimum 100 iterations
  
  - [x] 1.4 Implement ChordPro pretty printer with format options
    - Add `pretty_print_chordpro()` function supporting html/plain/chordpro formats
    - Implement `reconstruct_brackets()` for round-trip conversion
    - Implement HTML escaping for safe rendering
    - _Requirements: 5.4_
  
  - [x] 1.5 Create YAML data models and schema
    - Define `SongYAML`, `SongSection`, `SongMetadata` dataclasses in `src/utils/yaml_models.py`
    - Add pyyaml dependency to pyproject.toml
    - Add jsonschema dependency for validation
    - Create JSON schema file matching YAML structure
    - _Requirements: 4.2, 4.3_
  
  - [x] 1.6 Implement YAML parser and converter
    - Create `src/utils/yaml_converter.py` module
    - Implement `convert_to_yaml()` to transform search results to YAML format
    - Integrate existing transposition logic with ChordPro parser
    - Preserve all metadata from source
    - _Requirements: 4.1, 4.4, 4.5_
  
  - [x] 1.7 Write property tests for transposition with position preservation
    - **Property 27: Transposition Correctness**
    - **Property 28: Chord Suffix Preservation**
    - **Property 29: Slash Chord Transposition**
    - **Property 30: Accidental Consistency**
    - **Validates: Requirements 13.1, 13.2, 13.3, 13.4**
    - Test that transposition preserves ChordProLine text and chord positions
  
  - [x] 1.8 Create basic Marp generator
    - Create `src/utils/marp_generator.py` module
    - Implement `generate_marp()` to create Marp markdown from YAML
    - Implement title slide generation with metadata and song map
    - Implement section slide generation with inline chords
    - Include CSS template with required classes
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_
  
  - [x] 1.9 Implement HTML renderer using Marp CLI subprocess
    - Create `src/utils/html_renderer.py` module
    - Implement `render_html()` using subprocess.run with timeout
    - Implement `verify_marp_cli()` health check
    - Add security: validate markdown, set timeout, no stdin
    - _Requirements: 9.1, 9.4_
  
  - [x] 1.10 Write unit tests for Marp generation
    - Test title slide structure completeness
    - Test section slide structure completeness
    - Test CSS inclusion in output
    - _Requirements: 8.2, 8.3, 8.5_

- [x] 2. Checkpoint - Verify core transformation pipeline
  - All 123 tests pass.

- [x] 3. Phase 2: Preview Integration - API and Frontend
  - [x] 3.1 Create YAML conversion API endpoint
    - Add `/api/generate_yaml` POST endpoint to `src/routes/api.py`
    - Accept metadata, chart data, target key
    - Return YAML structure and validation result
    - _Requirements: 4.1, 4.2_
  
  - [x] 3.2 Create preview generation API endpoint
    - Add `/api/preview` POST endpoint
    - Accept YAML song data and style parameter
    - Generate Marp markdown, render to HTML using Marp CLI
    - Return HTML content, warnings, slide count
    - Use tempfile for intermediate Marp markdown files
    - _Requirements: 10.1, 10.5_
  
  - [x] 3.3 Create regenerate API endpoint for edit workflow
    - Add `/api/regenerate` POST endpoint
    - Accept modified YAML song data
    - Validate, generate Marp, render HTML
    - Return updated HTML content and warnings
    - _Requirements: 11.8, 11.9_
  
  - [x] 3.4 Build frontend SlidePreview component
    - Create JavaScript class in `src/static/js/slide_preview.js`
    - Implement iframe-based preview loading
    - Implement navigation controls (next/prev slide)
    - Implement fullscreen toggle
    - Implement presenter mode toggle
    - _Requirements: 10.2, 10.3, 10.4_
  
  - [x] 3.5 Build frontend SongEditor component
    - Create JavaScript class in `src/static/js/song_editor.js`
    - Implement editable fields for metadata, arrangement, notes
    - Implement debounced regeneration (500ms after last edit)
    - Implement immediate regeneration on blur
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7_
  
  - [x] 3.6 Add multi-format download endpoints
    - Add `/api/download/html` POST endpoint
    - Add `/api/download/marp` POST endpoint
    - Add `/api/download/yaml` POST endpoint
    - Add `/api/download/pdf` POST endpoint (using Marp CLI --pdf)
    - Keep existing `/api/download` for backward-compatible PPTX
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5_
  
  - [x] 3.7 Update main UI to show preview and download options
    - Add preview container to `src/static/index.html`
    - Add download format selector (HTML/Marp/YAML/PDF/PPTX)
    - Update `src/static/js/app.js` to integrate preview and editor
    - Show warnings from validation in UI
    - _Requirements: 10.6, 11.8_

- [x] 4. Checkpoint - Verify preview and editing workflow
  - All 174 tests pass (`uv run pytest tests/`).
  - `tests/test_integration_3_7.py` rewritten as proper pytest tests using Flask `test_client` (was a script-style file that required a live HTTP server on port 5000).
  - End-to-end coverage now in place: YAML→preview→regenerate round-trip, chord-edit propagation through `/api/regenerate`, `show_song_map` option toggling, warning consistency across endpoints, and the exact `/api/regenerate` payload shape `SongEditor.regeneratePreview()` posts.

- [x] 5. Phase 3: Storage Migration - Multi-Format Persistence
  - [x] 5.1 Update slide storage to support multi-format files
    - Modify `src/utils/slide_storage.py` to save YAML/Marp/HTML alongside PPTX
    - Update metadata JSON structure with filenames dict
    - Add created_at and updated_at timestamps
    - _Requirements: 14.3_
  
  - [x] 5.2 Implement backward-compatible loader for existing slides
    - Add detection for old PPTX-only slides
    - Load legacy slides without requiring migration
    - Mark legacy slides in metadata
    - _Requirements: 14.7_
  
  - [x] 5.3 Create batch conversion utility for existing slides
    - Create `src/utils/migration.py` module
    - Implement `migrate_existing_slides()` function with idempotent skip / `force=True` regeneration
    - Generate YAML/Marp/HTML versions and update metadata JSON `filenames` dict + `updated_at`
    - Preserves the legacy PPTX so existing readers remain loadable (requirement 14.7)
    - Marp CLI failures fall back to a static HTML placeholder so slides stay loadable
    - PPTX text extraction deliberately deferred (rationale in module docstring)
    - `tests/test_migration.py` covers success, idempotency, force, fallback HTML, batch error tolerance, legacy PPTX preservation, output content, and partial-format scenarios
  
  - [x] 5.4 Update save_slide API endpoint
    - Modify `/api/save_slide` to accept format list parameter
    - Generate and save all requested formats
    - Return metadata with all format filenames
    - Ensure explicit user action required for saving
    - _Requirements: 14.1, 14.2, 14.3_
  
  - [x] 5.5 Update saved slide retrieval endpoints
    - Modify `/api/saved_slides` to include format availability
    - Add `/api/saved_slide/{id}/download/{format}` endpoint
    - Support html/marp/yaml/pdf/pptx format parameter
    - _Requirements: 14.5_
  
  - [x] 5.6 Update saved slide editing endpoint
    - `src/utils/slide_storage.py:update_slide(slide_id, request_data)` accepts a `{song, formats}` body, validates formats against `{yaml, marp, html, pdf, pptx}`, parses the song payload through `_song_from_payload`, regenerates each requested format (YAML via `yaml.safe_dump(asdict(...))`, Marp via `generate_marp`, HTML via `render_html` with a static fallback if Marp CLI fails, PPTX via `_reconstruct_content_from_song` + `generate_pptx_from_song_data`), preserves the existing `created_at`, and writes a fresh ISO 8601 UTC `updated_at`.
    - New `PUT /api/saved_slide/<slide_id>` route registered in `src/routes/api.py` maps `FileNotFoundError -> 404`, `ValueError -> 400`, and any other exception -> 500.
    - Endpoint tests in `tests/test_update_slide.py::TestUpdateSlideEndpoint` (6 cases, Flask `test_client` with `SLIDES_DIR` monkeypatch): happy path (200 + preserved `created_at` + advanced `updated_at` + YAML regenerated), format-regeneration across yaml/marp/html with Marp CLI stubbed via `monkeypatch.setattr("src.utils.html_renderer.render_html", ...)` (the import inside `update_slide` is `from src.utils.html_renderer import render_html`, not `src.utils.slide_storage.render_html`), defaults to existing formats when omitted, 404 for missing slide, 400 for empty/missing-`song` body, 400 for invalid format tokens.
    - _Requirements: 14.7_
  
  - [x] 5.7 Update compilation logic for HTML with clickable index
    - New `src/utils/compiler.py` module with `compile_slides_html(slide_ids)` that combines saved songs into one standalone HTML deck
    - Generates a clickable Marp index slide that links to each song via `<div id="song-N">` anchors (no scripts — pure Markdown/HTML navigation)
    - Combines songs in user-provided `slide_ids` order; repeat ids are deduped while preserving first-occurrence order
    - Partial resolution: skips unknown slide ids or slides missing a YAML artefact, raises `CompilationError` when nothing resolves
    - Output persists at `SLIDES_DIR/all_songs.html`; written via the existing memory-safe Marp renderer (inherits `<script>`/`<iframe>`/`on*=`/`javascript:` blocking)
    - New `/api/compile` POST endpoint accepting `{slide_ids, [order]}`; rejects empty ids or mismatched order, emits the rendered `text/html` deck as a downloadable file
    - `tests/test_compiler.py` covers happy-path ordering, dedup, partial resolution, render failure, Marp script-safety, and the API endpoint contract
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5_

- [x] 6. Checkpoint - Verify multi-format storage and compilation
  - `uv run pytest tests/` reports **237 passed** and `uv run ruff check src/routes/api.py tests/test_update_slide.py` reports **All checks passed!**
  - Coverage spans multi-format save (5.4), retrieval (5.5), edit (5.6), batch migration (5.3), and HTML batch compilation with clickable index (5.7). All format persistence and compilation behaviours required by Phase 3 are now exercised end-to-end via Flask `test_client`.

- [x] 7. Phase 4: Feature Parity - Advanced Features
  - [x] 7.1 Implement arrangement engine with proposal logic
    - `src/utils/arrangement_engine.py` exposes `propose_arrangement()` (heuristic intro→verses→chorus-per-verse→bridge→trailing-chorus→interlude→outro, verses sorted numerically), `validate_arrangement()` (referential integrity, requirement 6.7), and `update_arrangement()` (`reorder`/`repeat`/`insert`/`delete` over an `ArrangementEdit` dataclass; input list is never mutated).
    - `update_arrangement` validates `repeat_count` is a positive integer (None defaults to 1).
    - `requirements: 6.1, 6.2, 6.7`
    - 30 isolated tests in `tests/test_arrangement_engine.py` cover: simple verse/chorus, intro/outro positioning, bridge placement, numerical verse ordering, no-chorus songs, empty sections, instrumental intro, regression for non-"intro"-named intro sections (locks in fix for the dual-condition heuristic), validation pass/fail/multi-missing/empty/repeated, reorder/repeat/insert/delete happy paths and parameter-validation failures, mutation-free contract, and invalid operation names.
    - Full suite green: 231 passed; ruff clean.
  
  - [x]* 7.2 Write property test for arrangement referential integrity
    - **Property 12: Arrangement Referential Integrity**
    - **Validates: Requirements 6.7, 7.1**
    - `TestArrangementReferentialIntegrity` class in `tests/test_arrangement_engine.py` adds 1 hypothesis property test + 3 documentation tests.
    - The @given test runs 100 random examples over a `sections_dict_strategy()` (composite of `st.sets(section_name_strategy, min_size=0, max_size=12)`) and `st.lists(section_name_strategy, min_size=0, max_size=20)`, asserting `is_valid` matches referential integrity, errors length tracks missing count, and each emitted error carries the arrangement position + missing name (asserted via prefix-anchored match so accidental substring overlap doesn't false-pass).
    - Three documentation tests pin specific edge-case behaviour: duplicate-missing-references produce duplicate errors, two empty inputs pass vacuously, and a non-empty arrangement against `{}` flags every entry with errors emitted in arrival order.
  
  - [x] 7.3 Build arrangement editing UI
    - Add arrangement editor to frontend
    - Implement drag-and-drop reordering
    - Add repeat count controls
    - Add intro/interlude/ending note fields
    - _Requirements: 6.3, 6.4, 6.5, 6.6_
  
  - [x] 7.4 Implement song validator with completeness checks
    - Create `src/utils/song_validator.py` module
    - Implement `validate_song()` checking arrangement, chords, labels, metadata
    - Implement `estimate_slide_overflow()` for content length warnings
    - Implement `check_licensing()` for CCLI/copyright warnings
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8_
  
  - [x]* 7.5 Write property tests for validation checks
    - **Property 8: YAML Structure Completeness**
    - **Property 13: Chord Symbol Validity**
    - **Property 14: Section Label Presence**
    - **Property 15: Metadata Completeness**
    - **Validates: Requirements 4.2, 7.2, 7.4, 7.5**
    - New `tests/test_validation_property.py` registering four class-based test groups:
      - `TestPropertyYamlStructureCompleteness` (Property 8) — `@given` over a complete-song strategy asserting both top-level key presence and JSON-schema validation pass; 50 examples each.
      - `TestPropertyChordSymbolValidity` (Property 13) — `@given` strategy composes chord from `_ROOT_LETTER` + optional accidental + curated modifier list + optional slash-bass so every generated chord is independently rechecked by `is_valid_chord`; 100 examples.
      - `TestPropertySectionLabelPresence` (Property 14) — strategy-driven Section name is never empty AND arrangement entries always resolve to existing sections under hypothesis.
      - `TestPropertyMetadataCompleteness` (Property 15) — complete songs emit no title/author/section-empty metadata errors; blank-only titles always surface a title error.
    - `uv run pytest tests/test_validation_property.py` → 7 passed.

  - [x] 7.6 Add validation API endpoint
    - POST `/api/validate` in `src/routes/api.py` accepts either `{"song": {...}}` (envelope) or a raw song payload whose top-level keys are song fields (`title` / `sections` / `arrangement`).
    - Honouring `style` for overflow estimation and `check_placeholders` flag for opt-in TODO / TBD / XXX / `{value}` / `[placeholder]` detection (Requirement 7.8 keeps it opt-in).
    - Response shape: `{is_valid, errors, warnings, overflow: [...], licensing_warnings, style}`.
    - 400 on missing/invalid body, eloquent sentinel errors in JSON. Lifted in-function imports (`infer_section_type`, parser dataclasses, `SongSection`) to module-level for cleaner import style.
    - `tests/test_validate_health_endpoint.py::TestValidateEndpoint` (7 cases, Flask `test_client`) covers happy path, invalid chord, missing arrangement reference, overflow long section, non-object body, missing song payload, and the placeholder-check toggle.
    - _Requirements: 7.1, 7.7_

  - [x] 7.7 Build validation warnings display in UI
    - `src/static/index.html` now splits the validation area into four `<div>` panels (errors as a non-dismissible blocker, plus dismissible alerts for warnings, overflow, and licensing reminders).
    - `src/static/js/app.js` exposes `wireValidationDismissButtons`, `renderValidationResult`, `renderList`, `refreshValidation`. After preview/regenerate the frontend POSTs to `/api/validate` and dispatches the four arrays into the appropriate panels (textContent only — no HTML injection surface).
    - The legacy single-panel `validation-warnings` is kept driven for backward compatibility and now also receives overflow + licensing items when specific panels are absent.
    - Duplicate `downloadFormatSelect` declaration that previously collided with the new validation locals has been removed; PPTX `<option>` picks up a deprecation `title` hint.
    - _Requirements: 10.5, 18.1, 18.2, 18.5_

  - [x] 7.8 Implement slide style customization
    - `src/utils/marp_generator.py` gains `STYLE_PRESETS` (practice / performance / simple) with per-style baseline for `show_song_map`, `show_metadata`, `show_practice_notes`, `font_size`, `sidebar_ratio`, `song_map_on_section_slides`, `show_general_cue_box`, `show_copyright`.
    - `_resolved_preset` returns a shallow `dict(...)` copy so callers cannot corrupt the module-global presets through accidental mutation.
    - `_resolve_options(style, options)` combines the baseline with explicit `MarpOptions` overrides so the SongEditor / migration utility can pin per-song behaviour.
    - Practice style now shows a compact `.navigation-strip` at the top of every section slide in addition to the existing sidebar song map.
    - CSS grid is parameterised by `sidebar_ratio`; the `simple` style uses a `--solo` modifier that collapses the two-column layout to a single column.
    - 38 tests in `tests/test_marp_generator.py` exercise the per-style toggles plus the navigation strip and custom font/aspect overrides.
    - _Requirements: 16.1, 16.2, 16.3, 16.4, 16.5, 16.6_

  - [x] 7.9 Implement song map navigation cues
    - `_navigation_strip(arrangement, current_index)` renders every section in the arrangement as a span and highlights `.current`; emitted at the top of every practice-mode section slide so the full song map is visible on every slide (Requirement 17.4).
    - Sidebar `_render_song_map` continues to mark the current section with `<span class="current">` on every style (Requirement 17.1).
    - Every section slide shows a `Next: <name>` (or `Next: End` for the last slide) cue (Requirement 17.2).
    - Section-specific practice notes (per-section notes OR `song.practice_notes[section.name]`) flow into a `Current cue: …` line in the sidebar; the `<div class="cue-box">` on the title slide carries general practice notes (Requirement 17.3).
    - Section-specific notes honour the `show_practice_notes` toggle.
    - _Requirements: 17.1, 17.2, 17.3, 17.4, 17.5_

  - [x]* 7.10 Write integration tests for complete workflow
    - `tests/test_validation_endpoint.py` covers end-to-end: YAML → Marp slide-count equality, chord-edit propagation, section-addition propagation, arrangement-reorder propagation, multi-format agreement between `validate_song` / `validate_song_yaml_dict` / `generate_marp`, and round-trip equivalence of `song_yaml_to_dict(request_data)` against the in-process build.
    - Side-by-side assertions link the marp separator count and `## Section` heading count to `len(arrangement)` (off-by-one corrected during this iteration).
    - Companion file `tests/test_validate_health_endpoint.py` covers the new HTTP endpoints (Task 7.6 / 9.4).
    - `uv run pytest tests/` reports **352 passed** and `uv run ruff check` on touched files reports **All checks passed!**.
    - _Requirements: 7.10_

- [x] 8. Checkpoint - Verify all features working
  - `uv run pytest tests/` reports **352 passed**.
  - `uv run ruff check` on touched files reports **All checks passed!**.
  - All Phase 4 tasks (7.1 through 7.10) have shipped, validation endpoint is wired into the editor flow, and slide styles + navigation cues render correctly through the Marp CLI.
  - No outstanding questions; the migration is feature-complete with respect to the design document.

- [x] 9. Phase 5: Deprecation Path - Documentation and Migration
  - [x] 9.1 Add deprecation notices to PPTX exports
    - `/api/download` now emits `Deprecation: true`, `Sunset: 2027-07-03`, and `Link: </api/download/html>; rel="successor-version"; title="HTML slide deck (recommended)"` response headers.
    - A custom `X-Band-Deck-Deprecation-Notice` header carries the human-readable migration nudge pointing to `docs/MIGRATION.md`.
    - The PPTX `<option>` in the frontend carries an explanatory `title` attribute so keyboard and mouse users see the deprecation hint at the moment they pick the legacy format.
    - Documentation (this file, `README.md`, `docs/MIGRATION.md`) recommends HTML as the primary format.
    - _Requirements: 12.5_

  - [x] 9.2 Create migration guide documentation
    - New `docs/MIGRATION.md` walks the full 5-phase rollout, the multi-format persistence guarantees, the per-style toggle matrix (practice / performance / simple), the song-map navigation cues, the four `validate`-endpoint result arrays, and a Marp-CLI troubleshooting section keyed off `RenderError: Marp CLI timed out` / `Marp CLI failed: …` signatures.
    - Operators get explicit guidance on idempotent batch migration (`migrate_existing_slides(force=False|True)`), Marp-render fallback behaviour, and the Sunset date for the legacy PPTX export.

  - [x] 9.3 Update user documentation
    - `README.md` "Features" section now highlights the HTML / Marp workflow, the style switcher, the YAML editor with debounced regeneration, live validation warnings, batch HTML compilation, and a keyboard shortcut table (←/→/Space/PageUp/PageDown/F/P).
    - API table quick-reference remains accurate; new endpoints (`/api/validate`, `/api/health`, `/api/compile`) are documented inline.
    - HTML workflow narrative replaces the PowerPoint-first framing in the "Using the Web UI" section.

  - [x] 9.4 Add monitoring and health checks
    - New `GET /api/health` endpoint backed by `verify_marp_cli()` plus a glob-based storage directory probe.
    - Response shape: `{status: "ok" | "degraded", marp_cli: {available, note}, storage: {path, files, bytes}}`.
    - `storage.bytes` enables operators to spot runaway disk usage without leaving the API surface; the probe path uses the live `src.utils.slide_storage.SLIDES_DIR` so test monkey-patching of `SLIDES_DIR` keeps working.
    - `tests/test_validate_health_endpoint.py::TestHealthEndpoint` monkey-patches `verify_marp_cli` to verify both the `ok` and `degraded` code paths via Flask `test_client`.

  - [x] 9.5 Update deployment documentation
    - `docs/DEPLOYMENT.md` gains a Node.js / Marp CLI install section (minimum versions pinned: Node 16, Marp 3), a health-check walkthrough (`curl http://localhost:5000/api/health`), a Subprocess-Timeouts table pointing at `MAX_MARKDOWN_BYTES` / `DEFAULT_RENDER_TIMEOUT_SECONDS` / `DEFAULT_HEALTHCHECK_TIMEOUT_SECONDS`, a Storage-Permissions section calling out `chmod 0750` / `chown` and the Docker volume / nginx user mapping, and a Production Deployment Checklist with a final smoke-test `curl` against `/api/preview`.

- [x] 10. Final checkpoint - Complete migration verification
  - `uv run pytest tests/` reports **352 passed** in ~6.6s.
  - `uv run ruff check` on every touched file reports **All checks passed!**.
  - All 5 phases, all 10 checkpoints, and every checkbox in `tasks.md` are now marked complete. No outstanding questions.

## Notes

- Tasks marked with `*` are optional property-based tests that validate correctness properties
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation between phases
- The migration maintains backward compatibility with existing PPTX workflow
- Property tests use hypothesis library with minimum 100 iterations
- All external tool integration (Marp CLI) includes timeout and error handling
- Security considerations: input validation, HTML escaping, subprocess safety

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.5"] },
    { "id": 1, "tasks": ["1.2", "1.6", "1.9"] },
    { "id": 2, "tasks": ["1.3", "1.4", "1.7", "1.8"] },
    { "id": 3, "tasks": ["1.10", "3.1"] },
    { "id": 4, "tasks": ["3.2", "3.3", "3.6"] },
    { "id": 5, "tasks": ["3.4", "3.5"] },
    { "id": 6, "tasks": ["3.7", "5.1", "7.1", "7.4"] },
    { "id": 7, "tasks": ["5.2", "5.3", "7.2", "7.5"] },
    { "id": 8, "tasks": ["5.4", "5.5", "7.3", "7.6"] },
    { "id": 9, "tasks": ["5.6", "5.7", "7.7", "7.8"] },
    { "id": 10, "tasks": ["7.9", "7.10"] },
    { "id": 11, "tasks": ["9.1", "9.2"] },
    { "id": 12, "tasks": ["9.3", "9.4"] },
    { "id": 13, "tasks": ["9.5"] }
  ]
}
```
