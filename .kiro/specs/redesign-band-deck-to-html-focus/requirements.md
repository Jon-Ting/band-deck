# Requirements Document

## Introduction

This document specifies the requirements for redesigning Band-Deck from a PowerPoint-focused application to an HTML slide deck generator using Marp markdown. The redesigned system converts worship songs into structured YAML data, generates Marp markdown, renders standalone HTML slide decks suitable for band practice, and provides an interactive web-based preview and editing workflow.

## Glossary

- **Band_Deck_App**: The Flask web application that orchestrates the song-to-slides workflow
- **Song_Identifier**: Component that searches for and disambiguates song matches from external sources
- **Chart_Retriever**: Component that fetches lyrics and chords from various sources in priority order
- **Song_Parser**: Component that converts raw chord charts into structured YAML format
- **Arrangement_Engine**: Component that creates and manages song maps (section sequences)
- **Song_Validator**: Component that checks song data for completeness and correctness
- **Marp_Generator**: Component that converts structured song YAML into Marp markdown
- **HTML_Renderer**: Component that converts Marp markdown into standalone HTML slide decks
- **Slide_Previewer**: Component that displays rendered HTML slides with navigation controls
- **YAML_Source**: Structured song data in YAML/JSON format containing metadata, sections, and arrangement
- **Marp_Markdown**: Markdown file with Marp directives for slide generation
- **HTML_Slide_Deck**: Standalone HTML file containing the complete slide presentation
- **ChordPro_Format**: Industry-standard format for representing chords inline with lyrics
- **Song_Map**: Ordered sequence of sections defining the arrangement (e.g., Intro → V1 → Chorus)
- **CCLI**: Christian Copyright Licensing International - licensing authority for worship songs
- **Section**: Named portion of a song (Verse, Chorus, Bridge, Intro, etc.)
- **Structured_Data**: Canonical YAML/JSON representation that serves as the source of truth

## Requirements

### Requirement 1: Minimal Song Input

**User Story:** As a worship musician, I want to start with just a song name, so that I can quickly generate slides without gathering extensive metadata upfront.

#### Acceptance Criteria

1. THE Band_Deck_App SHALL accept a song name as the only required input
2. THE Band_Deck_App SHALL accept optional inputs for target key, preferred arrangement, slide style, and band notes
3. WHEN a song name is provided, THE Band_Deck_App SHALL initiate the song identification workflow
4. IF the song identification workflow fails to start due to system errors or resource constraints, THEN THE Band_Deck_App SHALL display an error message to the user
5. THE Band_Deck_App SHALL preserve all user-provided inputs throughout the workflow

### Requirement 2: Song Identification and Disambiguation

**User Story:** As a worship musician, I want the app to find the correct song from my search term, so that I don't get slides for the wrong song.

#### Acceptance Criteria

1. WHEN a song name is provided, THE Song_Identifier SHALL search external sources for matching songs
2. THE Song_Identifier SHALL retrieve metadata including title, authors, CCLI number, original key, BPM, time signature, and source links
3. IF multiple matches are found, THEN THE Song_Identifier SHALL present options to the user
4. THE Song_Identifier SHALL allow the user to select the correct match from the presented options
5. WHEN a single unambiguous match is found, THE Song_Identifier SHALL proceed without user intervention

### Requirement 3: Chart Retrieval with Priority Sources

**User Story:** As a worship musician, I want the app to fetch accurate lyrics and chords from reliable sources, so that my slides contain correct information.

#### Acceptance Criteria

1. THE Chart_Retriever SHALL attempt to fetch lyrics and chords in this priority order: user-provided chart, official publisher chart, official artist chart, CCLI source, manually pasted text
2. WHEN a chart is retrieved, THE Chart_Retriever SHALL flag it for human review
3. THE Chart_Retriever SHALL prompt the user to verify lyrics accuracy, chord accuracy, CCLI permission status, and target key appropriateness
4. THE Chart_Retriever SHALL allow the user to provide a chart manually if automated retrieval fails
5. THE Chart_Retriever SHALL store the source type and source URL with the retrieved chart

### Requirement 4: Structured Song Data Conversion

**User Story:** As a worship musician, I want my song stored in a structured format, so that I can easily edit and regenerate slides.

#### Acceptance Criteria

1. THE Song_Parser SHALL convert raw chord charts into YAML format
2. THE YAML_Source SHALL contain title, authors, key, BPM, time signature, and CCLI number
3. THE YAML_Source SHALL contain sections with ChordPro-formatted lines
4. THE Song_Parser SHALL preserve chord positioning relative to lyrics
5. THE YAML_Source SHALL serve as the single source of truth for all downstream operations

### Requirement 5: ChordPro Parsing and Pretty Printing

**User Story:** As a developer, I want robust parsing and formatting of ChordPro notation, so that chord positioning is preserved correctly.

#### Acceptance Criteria

1. THE Song_Parser SHALL parse ChordPro notation including chords in brackets and plain text lyrics
2. THE Song_Parser SHALL extract chord symbols and their positions relative to lyrics
3. THE Song_Parser SHALL handle multiple chords per line
4. THE Marp_Generator SHALL include a pretty printer that formats ChordPro lines for display
5. FOR ALL valid Structured_Data, parsing then pretty printing then parsing again SHALL produce equivalent data (round-trip property)

### Requirement 6: Arrangement Proposal and Editing

**User Story:** As a worship musician, I want to create a song map showing the order of sections, so that my band knows the arrangement.

#### Acceptance Criteria

1. THE Arrangement_Engine SHALL propose a default arrangement based on the song sections
2. THE Arrangement_Engine SHALL display the song map as a sequence (e.g., Intro → V1 → V2 → Chorus)
3. THE Arrangement_Engine SHALL allow the user to reorder sections
4. THE Arrangement_Engine SHALL allow the user to add repeats to any section
5. THE Arrangement_Engine SHALL allow the user to add intro, interlude, and ending notes
6. THE Arrangement_Engine SHALL allow the user to modify key, capo, and practice notes
7. THE Arrangement_Engine SHALL validate that all arrangement items reference existing sections

### Requirement 7: Song Data Validation

**User Story:** As a worship musician, I want to be warned about incomplete or invalid song data, so that I can fix issues before generating slides.

#### Acceptance Criteria

1. THE Song_Validator SHALL verify that all arrangement items reference existing sections
2. THE Song_Validator SHALL verify that all chord symbols are valid
3. THE Song_Validator SHALL warn if any slide would overflow based on content length
4. THE Song_Validator SHALL verify that all sections have clear labels
5. THE Song_Validator SHALL verify that metadata fields are complete
6. THE Song_Validator SHALL display copyright and CCLI warnings if licensing information is incomplete
7. WHEN explicitly triggered, THE Song_Validator SHALL check for unresolved placeholder text
8. WHEN placeholder checking is disabled or skipped, THE Band_Deck_App SHALL allow songs to be processed without placeholder validation

### Requirement 8: Marp Markdown Generation

**User Story:** As a worship musician, I want the app to generate Marp-compatible markdown, so that I can customize slides if needed.

#### Acceptance Criteria

1. THE Marp_Generator SHALL convert YAML_Source into Marp_Markdown
2. THE Marp_Markdown SHALL include a title slide with metadata and song map
3. FOR EACH section in the arrangement, THE Marp_Generator SHALL create a slide with section title, lyrics with inline chords, key/BPM/time signature, song map with current position highlighted, and optional band notes
4. THE Marp_Generator SHALL format chords inline with lyrics using styled spans
5. THE Marp_Generator SHALL include custom CSS for consistent styling

### Requirement 9: HTML Slide Deck Rendering

**User Story:** As a worship musician, I want a standalone HTML file I can open in any browser, so that I don't need special software during practice.

#### Acceptance Criteria

1. THE HTML_Renderer SHALL execute Marp rendering to convert Marp_Markdown into HTML_Slide_Deck
2. THE HTML_Slide_Deck SHALL be standalone and require no external dependencies
3. THE HTML_Slide_Deck SHALL be viewable in any modern web browser
4. THE HTML_Renderer SHALL preserve all styling from the Marp_Markdown
5. THE HTML_Slide_Deck SHALL support keyboard navigation between slides

### Requirement 10: Interactive Slide Preview

**User Story:** As a worship musician, I want to preview my slides in the browser before downloading, so that I can verify they look correct.

#### Acceptance Criteria

1. THE Slide_Previewer SHALL display the rendered HTML_Slide_Deck in the browser
2. THE Slide_Previewer SHALL provide navigation controls for moving between slides
3. THE Slide_Previewer SHALL provide a presenter mode option
4. THE Slide_Previewer SHALL provide a fullscreen mode option
5. THE Slide_Previewer SHALL display warnings if any slides may overflow
6. THE Slide_Previewer SHALL provide download buttons for HTML, Marp Markdown, and YAML files

### Requirement 11: Edit and Regenerate Workflow

**User Story:** As a worship musician, I want to edit the song data and regenerate the preview, so that I can fine-tune the slides.

#### Acceptance Criteria

1. THE Band_Deck_App SHALL allow the user to modify the arrangement
2. THE Band_Deck_App SHALL allow the user to modify key and transposition settings
3. THE Band_Deck_App SHALL allow the user to modify chords and lyrics
4. THE Band_Deck_App SHALL allow the user to modify slide style and font size
5. THE Band_Deck_App SHALL allow the user to toggle song map visibility
6. THE Band_Deck_App SHALL allow the user to modify practice notes
7. THE Band_Deck_App SHALL allow the user to split sections across multiple slides
8. WHEN the user finishes editing a field, THE Band_Deck_App SHALL regenerate the preview
9. THE Band_Deck_App SHALL regenerate the preview on blur, enter keypress, or after a brief pause in user input

### Requirement 12: Multi-Format Download

**User Story:** As a worship musician, I want to download the slides in multiple formats, so that I have flexibility in how I present them.

#### Acceptance Criteria

1. THE Band_Deck_App SHALL provide standalone HTML as the primary download format
2. THE Band_Deck_App SHALL provide Marp Markdown as a download option
3. THE Band_Deck_App SHALL provide YAML source as a download option
4. THE Band_Deck_App SHALL provide PDF export as an optional format
5. THE Band_Deck_App SHALL provide PPTX export as an optional format for backward compatibility

### Requirement 13: Chord Transposition

**User Story:** As a worship musician, I want to transpose songs to different keys, so that they match my vocalist's range.

#### Acceptance Criteria

1. WHEN a target key is specified, THE Song_Parser SHALL transpose all chords from the original key to the target key
2. THE Song_Parser SHALL preserve chord suffixes during transposition (m, maj7, sus4, etc.)
3. THE Song_Parser SHALL handle slash chords correctly (e.g., C/G → D/A)
4. THE Song_Parser SHALL use sharps or flats consistently based on the target key
5. THE Song_Parser SHALL handle enharmonic equivalents (C# ↔ Db)

### Requirement 14: Persistent Slide Library

**User Story:** As a worship musician, I want to save generated slides to a library, so that I can reuse them for future services.

#### Acceptance Criteria

1. THE Band_Deck_App SHALL allow the user to save generated slides with a unique identifier
2. THE Band_Deck_App SHALL save slides only when the user explicitly initiates a save action
3. THE Band_Deck_App SHALL store the YAML_Source, Marp_Markdown, and HTML_Slide_Deck for each saved slide
4. THE Band_Deck_App SHALL provide a list view of all saved slides
5. THE Band_Deck_App SHALL allow the user to re-download any saved slide
6. THE Band_Deck_App SHALL allow the user to delete saved slides
7. THE Band_Deck_App SHALL allow the user to edit and regenerate saved slides

### Requirement 15: Batch Compilation

**User Story:** As a worship musician, I want to combine multiple saved slides into one presentation, so that I can have all songs for a service in one file.

#### Acceptance Criteria

1. THE Band_Deck_App SHALL allow the user to select multiple saved slides for compilation
2. THE Band_Deck_App SHALL generate a single HTML_Slide_Deck containing all selected songs
3. THE Band_Deck_App SHALL include a clickable index slide at the beginning
4. THE Band_Deck_App SHALL preserve song order as specified by the user
5. THE Band_Deck_App SHALL support navigation between songs within the compiled deck

### Requirement 16: Slide Style Customization

**User Story:** As a worship musician, I want to choose between different slide styles, so that slides match my intended use (practice vs. performance).

#### Acceptance Criteria

1. THE Band_Deck_App SHALL support a "practice" style that includes song map, metadata, and practice notes
2. THE Band_Deck_App SHALL support a "performance" style that emphasizes lyrics and minimizes metadata
3. THE Band_Deck_App SHALL support a "simple" style with minimal formatting
4. THE Band_Deck_App SHALL allow the user to select the slide style during arrangement editing
5. THE Marp_Generator SHALL apply the selected style when generating Marp_Markdown
6. IF the Marp_Generator fails to apply the selected style due to a technical error, THEN THE Marp_Generator SHALL generate slides with a default style and continue processing

### Requirement 17: Song Map Navigation Cues

**User Story:** As a worship musician, I want to see where I am in the song arrangement, so that I know what's coming next.

#### Acceptance Criteria

1. WHEN a slide is displayed, THE Slide_Previewer SHALL highlight the current section in the song map
2. THE Slide_Previewer SHALL display the next section as a visual cue
3. THE Slide_Previewer SHALL display section-specific practice notes on the appropriate slides
4. THE Song_Map SHALL be visible on all slides in practice mode
5. THE Song_Map SHALL show the complete arrangement sequence

### Requirement 18: Copyright and Licensing Warnings

**User Story:** As a worship leader, I want to be reminded about copyright compliance, so that I respect licensing requirements.

#### Acceptance Criteria

1. IF CCLI number is missing, THEN THE Song_Validator SHALL display a warning
2. IF copyright information is incomplete, THEN THE Song_Validator SHALL display a warning
3. THE Band_Deck_App SHALL display a copyright notice on the title slide
4. THE Band_Deck_App SHALL include CCLI number on the title slide if available
5. THE Song_Validator SHALL remind the user to verify CCLI permission before use

