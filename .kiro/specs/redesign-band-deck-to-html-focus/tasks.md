# Implementation Plan: HTML/Marp Slide Generation Redesign

## Overview

This plan implements the redesign of Band-Deck from a PowerPoint-focused application to an HTML slide deck generator using Marp markdown. The implementation follows a 5-phase migration strategy that maintains backward compatibility while adding new HTML/YAML capabilities.

## Tasks

- [ ] 1. Phase 1: Parallel Implementation - Core Components
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
  
  - [ ]* 1.3 Write property test for ChordPro round-trip preservation
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
  
  - [ ] 1.6 Implement YAML parser and converter
    - Create `src/utils/yaml_converter.py` module
    - Implement `convert_to_yaml()` to transform search results to YAML format
    - Integrate existing transposition logic with ChordPro parser
    - Preserve all metadata from source
    - _Requirements: 4.1, 4.4, 4.5_
  
  - [ ]* 1.7 Write property tests for transposition with position preservation
    - **Property 27: Transposition Correctness**
    - **Property 28: Chord Suffix Preservation**
    - **Property 29: Slash Chord Transposition**
    - **Property 30: Accidental Consistency**
    - **Validates: Requirements 13.1, 13.2, 13.3, 13.4**
    - Test that transposition preserves ChordProLine text and chord positions
  
  - [ ] 1.8 Create basic Marp generator
    - Create `src/utils/marp_generator.py` module
    - Implement `generate_marp()` to create Marp markdown from YAML
    - Implement title slide generation with metadata and song map
    - Implement section slide generation with inline chords
    - Include CSS template with required classes
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_
  
  - [ ] 1.9 Implement HTML renderer using Marp CLI subprocess
    - Create `src/utils/html_renderer.py` module
    - Implement `render_html()` using subprocess.run with timeout
    - Implement `verify_marp_cli()` health check
    - Add security: validate markdown, set timeout, no stdin
    - _Requirements: 9.1, 9.4_
  
  - [ ]* 1.10 Write unit tests for Marp generation
    - Test title slide structure completeness
    - Test section slide structure completeness
    - Test CSS inclusion in output
    - _Requirements: 8.2, 8.3, 8.5_

- [ ] 2. Checkpoint - Verify core transformation pipeline
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 3. Phase 2: Preview Integration - API and Frontend
  - [ ] 3.1 Create YAML conversion API endpoint
    - Add `/api/generate_yaml` POST endpoint to `src/routes/api.py`
    - Accept metadata, chart data, target key
    - Return YAML structure and validation result
    - _Requirements: 4.1, 4.2_
  
  - [ ] 3.2 Create preview generation API endpoint
    - Add `/api/preview` POST endpoint
    - Accept YAML song data and style parameter
    - Generate Marp markdown, render to HTML using Marp CLI
    - Return HTML content, warnings, slide count
    - Use tempfile for intermediate Marp markdown files
    - _Requirements: 10.1, 10.5_
  
  - [ ] 3.3 Create regenerate API endpoint for edit workflow
    - Add `/api/regenerate` POST endpoint
    - Accept modified YAML song data
    - Validate, generate Marp, render HTML
    - Return updated HTML content and warnings
    - _Requirements: 11.8, 11.9_
  
  - [ ] 3.4 Build frontend SlidePreview component
    - Create JavaScript class in `src/static/js/slide_preview.js`
    - Implement iframe-based preview loading
    - Implement navigation controls (next/prev slide)
    - Implement fullscreen toggle
    - Implement presenter mode toggle
    - _Requirements: 10.2, 10.3, 10.4_
  
  - [ ] 3.5 Build frontend SongEditor component
    - Create JavaScript class in `src/static/js/song_editor.js`
    - Implement editable fields for metadata, arrangement, notes
    - Implement debounced regeneration (500ms after last edit)
    - Implement immediate regeneration on blur
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7_
  
  - [ ] 3.6 Add multi-format download endpoints
    - Add `/api/download/html` POST endpoint
    - Add `/api/download/marp` POST endpoint
    - Add `/api/download/yaml` POST endpoint
    - Add `/api/download/pdf` POST endpoint (using Marp CLI --pdf)
    - Keep existing `/api/download` for backward-compatible PPTX
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5_
  
  - [ ] 3.7 Update main UI to show preview and download options
    - Add preview container to `src/static/index.html`
    - Add download format selector (HTML/Marp/YAML/PDF/PPTX)
    - Update `src/static/js/app.js` to integrate preview and editor
    - Show warnings from validation in UI
    - _Requirements: 10.6, 11.8_

- [ ] 4. Checkpoint - Verify preview and editing workflow
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Phase 3: Storage Migration - Multi-Format Persistence
  - [ ] 5.1 Update slide storage to support multi-format files
    - Modify `src/utils/slide_storage.py` to save YAML/Marp/HTML alongside PPTX
    - Update metadata JSON structure with filenames dict
    - Add created_at and updated_at timestamps
    - _Requirements: 14.3_
  
  - [ ] 5.2 Implement backward-compatible loader for existing slides
    - Add detection for old PPTX-only slides
    - Load legacy slides without requiring migration
    - Mark legacy slides in metadata
    - _Requirements: 14.7_
  
  - [ ] 5.3 Create batch conversion utility for existing slides
    - Create `src/utils/migration.py` module
    - Implement `migrate_existing_slides()` function
    - Extract song data from existing PPTX files
    - Generate YAML/Marp/HTML versions
    - Update metadata JSON with new format filenames
    - _Requirements: 14.7_
  
  - [ ] 5.4 Update save_slide API endpoint
    - Modify `/api/save_slide` to accept format list parameter
    - Generate and save all requested formats
    - Return metadata with all format filenames
    - Ensure explicit user action required for saving
    - _Requirements: 14.1, 14.2, 14.3_
  
  - [ ] 5.5 Update saved slide retrieval endpoints
    - Modify `/api/saved_slides` to include format availability
    - Add `/api/saved_slide/{id}/download/{format}` endpoint
    - Support html/marp/yaml/pdf/pptx format parameter
    - _Requirements: 14.5_
  
  - [ ] 5.6 Update saved slide editing endpoint
    - Add `/api/saved_slide/{id}` PUT endpoint
    - Accept modified YAML song data
    - Regenerate all formats
    - Update metadata timestamps
    - _Requirements: 14.7_
  
  - [ ] 5.7 Update compilation logic for HTML with clickable index
    - Modify compilation to generate HTML with index slide
    - Create clickable navigation elements for each song
    - Combine all song sections in user-specified order
    - Add `/api/compile` POST endpoint accepting slide_ids and order
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5_

- [ ] 6. Checkpoint - Verify multi-format storage and compilation
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 7. Phase 4: Feature Parity - Advanced Features
  - [ ] 7.1 Implement arrangement engine with proposal logic
    - Create `src/utils/arrangement_engine.py` module
    - Implement `propose_arrangement()` based on section types
    - Implement `validate_arrangement()` for referential integrity
    - Implement `update_arrangement()` for reorder/repeat/insert operations
    - _Requirements: 6.1, 6.2, 6.7_
  
  - [ ]* 7.2 Write property test for arrangement referential integrity
    - **Property 12: Arrangement Referential Integrity**
    - **Validates: Requirements 6.7, 7.1**
    - Generate random arrangements and section dictionaries
    - Verify all arrangement references exist in sections
  
  - [ ] 7.3 Build arrangement editing UI
    - Add arrangement editor to frontend
    - Implement drag-and-drop reordering
    - Add repeat count controls
    - Add intro/interlude/ending note fields
    - _Requirements: 6.3, 6.4, 6.5, 6.6_
  
  - [ ] 7.4 Implement song validator with completeness checks
    - Create `src/utils/song_validator.py` module
    - Implement `validate_song()` checking arrangement, chords, labels, metadata
    - Implement `estimate_slide_overflow()` for content length warnings
    - Implement `check_licensing()` for CCLI/copyright warnings
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8_
  
  - [ ]* 7.5 Write property tests for validation checks
    - **Property 8: YAML Structure Completeness**
    - **Property 13: Chord Symbol Validity**
    - **Property 14: Section Label Presence**
    - **Property 15: Metadata Completeness**
    - **Validates: Requirements 4.2, 7.2, 7.4, 7.5**
  
  - [ ] 7.6 Add validation API endpoint
    - Add `/api/validate` POST endpoint
    - Accept song YAML and check_placeholders flag
    - Return validation result with errors, warnings, overflow estimates
    - _Requirements: 7.1, 7.7_
  
  - [ ] 7.7 Build validation warnings display in UI
    - Show validation errors preventing save
    - Show warnings as dismissible alerts
    - Show overflow warnings with section names
    - Display CCLI/copyright reminders
    - _Requirements: 10.5, 18.1, 18.2, 18.5_
  
  - [ ] 7.8 Implement slide style customization
    - Add style selection UI (practice/performance/simple)
    - Implement style-specific Marp generation logic
    - Apply styles to show/hide song map, metadata, practice notes
    - _Requirements: 16.1, 16.2, 16.3, 16.4, 16.5, 16.6_
  
  - [ ] 7.9 Implement song map navigation cues
    - Generate song map HTML with current position highlighting
    - Add next section display on each slide
    - Show section-specific practice notes on relevant slides
    - Ensure song map visible in practice mode on all slides
    - _Requirements: 17.1, 17.2, 17.3, 17.4, 17.5_
  
  - [ ]* 7.10 Write integration tests for complete workflow
    - Test end-to-end: search → parse → YAML → Marp → HTML
    - Test edit workflow: modify YAML → regenerate → verify updates
    - Test multi-format consistency: YAML/Marp/HTML represent same song

- [ ] 8. Checkpoint - Verify all features working
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 9. Phase 5: Deprecation Path - Documentation and Migration
  - [ ] 9.1 Add deprecation notices to PPTX exports
    - Update `/api/download` response with deprecation header
    - Add notice in UI near PPTX download button
    - Update documentation to recommend HTML format
    - _Requirements: 12.5_
  
  - [ ] 9.2 Create migration guide documentation
    - Document the 5-phase rollout strategy
    - Provide migration script usage instructions
    - Document new API endpoints and UI features
    - Include troubleshooting section for Marp CLI issues
  
  - [ ] 9.3 Update user documentation
    - Update README.md with HTML workflow
    - Document YAML format and editing capabilities
    - Document arrangement editing features
    - Add examples of each slide style
    - Document keyboard navigation and presenter mode
  
  - [ ] 9.4 Add monitoring and health checks
    - Add `/api/health` endpoint checking Marp CLI availability
    - Add logging for Marp CLI execution time and failures
    - Track preview regeneration latency
    - Monitor storage directory size
  
  - [ ] 9.5 Update deployment documentation
    - Document Node.js and Marp CLI installation requirements
    - Document subprocess timeout configuration
    - Document file permission requirements for saved_slides directory
    - Add production deployment checklist

- [ ] 10. Final checkpoint - Complete migration verification
  - Ensure all tests pass, ask the user if questions arise.

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
