# Design Document: HTML/Marp Slide Generation Redesign

## Overview

This design transforms Band-Deck from a PowerPoint-focused application into an HTML slide deck generator using Marp markdown. The redesigned system converts worship songs into structured YAML data, generates Marp markdown with ChordPro-formatted lyrics, renders standalone HTML slide decks, and provides an interactive web-based preview and editing workflow.

### Key Design Principles

1. **Structured data as source of truth**: YAML/JSON format stores all song information (metadata, sections, chords, arrangement)
2. **ChordPro for chord notation**: Industry-standard format with round-trip parsing guarantee
3. **Marp for slide generation**: Markdown-based slides with custom CSS styling
4. **Standalone HTML output**: Browser-viewable files with no external dependencies
5. **Interactive preview workflow**: Edit-regenerate loop with live preview
6. **Backward compatibility**: Optional PPTX export for migration path

## Architecture

### High-Level Component Flow

```
User Input (Song Name)
       ↓
   Song_Identifier → External sources (Worship Together, CCLI)
       ↓
   Chart_Retriever → Priority: user chart → official → CCLI → manual
       ↓
   Song_Parser → ChordPro Parser → Structured YAML
       ↓
   Arrangement_Engine → Song Map (section sequence)
       ↓
   Song_Validator → Completeness & correctness checks
       ↓
   Marp_Generator → ChordPro Pretty Printer → Marp Markdown
       ↓
   HTML_Renderer → Marp CLI → Standalone HTML
       ↓
   Slide_Previewer → Browser preview with navigation
       ↓
   [Edit Loop] → Modify YAML → Regenerate preview
       ↓
   Download (HTML / Marp MD / YAML / PDF / PPTX)
```

### Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Flask Application                        │
│  (src/main.py + src/routes/api.py)                         │
└─────────────────────────────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ↓                  ↓                  ↓
┌──────────────┐  ┌─────────────────┐  ┌──────────────┐
│ Song Search  │  │ YAML Processing │  │ Slide Render │
│   Layer      │  │     Layer       │  │    Layer     │
└──────────────┘  └─────────────────┘  └──────────────┘
        │                  │                  │
┌───────────────┐  ┌──────────────┐  ┌──────────────┐
│ Identifier    │  │ Parser       │  │ Marp Gen     │
│ Retriever     │  │ Validator    │  │ HTML Render  │
│ Transposer    │  │ Arrangement  │  │ Previewer    │
└───────────────┘  └──────────────┘  └──────────────┘
        │                  │                  │
┌───────────────┐  ┌──────────────┐  ┌──────────────┐
│ External APIs │  │ YAML Storage │  │ Marp CLI     │
│ (WT, CCLI)    │  │ (disk files) │  │ (subprocess) │
└───────────────┘  └──────────────┘  └──────────────┘
```

## Components and Interfaces

### 1. Song_Identifier

**Responsibility**: Search external sources and disambiguate song matches.

**Public Interface**:
```python
def identify_song(song_name: str, artist: str | None = None) -> list[SongMatch]:
    """
    Search for songs matching the name/artist.
    Returns list of matches with metadata for disambiguation.
    """

def select_match(match_id: str) -> SongMetadata:
    """
    User selects a specific match. Returns full metadata.
    """
```

**Data Structures**:
```python
@dataclass
class SongMatch:
    match_id: str
    title: str
    authors: list[str]
    ccli_number: str | None
    original_key: str | None
    bpm: int | None
    time_signature: str | None
    source_url: str
    confidence: float  # 0.0-1.0

@dataclass
class SongMetadata:
    title: str
    authors: list[str]
    ccli_number: str | None
    copyright: str | None
    original_key: str | None
    bpm: int | None
    time_signature: str | None
    source_urls: list[str]
```

### 2. Chart_Retriever

**Responsibility**: Fetch lyrics and chords from priority sources.

**Public Interface**:
```python
def retrieve_chart(
    metadata: SongMetadata,
    user_chart: str | None = None
) -> ChartData:
    """
    Fetch chart from priority sources: user → official → CCLI.
    Returns raw chart data with source information.
    """

def flag_for_review(chart: ChartData) -> ReviewPrompt:
    """
    Generate review prompts for human verification.
    """
```

**Data Structures**:
```python
@dataclass
class ChartData:
    raw_text: str
    source_type: str  # "user", "official", "ccli", "manual"
    source_url: str | None
    needs_review: bool
    review_items: list[str]  # ["lyrics", "chords", "ccli", "key"]
```


### 3. Song_Parser

**Responsibility**: Convert raw chord charts into structured YAML with ChordPro notation.

**Public Interface**:
```python
def parse_chordpro(raw_text: str) -> list[ChordProLine]:
    """
    Parse ChordPro notation: [Chord]lyric text
    Returns structured representation of chords and positions.
    """

def convert_to_yaml(
    metadata: SongMetadata,
    chart: ChartData,
    target_key: str | None = None
) -> SongYAML:
    """
    Convert chart to structured YAML format.
    Applies transposition if target_key specified.
    """

def transpose_chords(
    lines: list[ChordProLine],
    from_key: str,
    to_key: str
) -> list[ChordProLine]:
    """
    Transpose all chords while preserving positioning.
    """
```

**Data Structures**:
```python
@dataclass
class ChordProLine:
    text: str  # Lyric text
    chords: list[ChordPosition]
    
@dataclass
class ChordPosition:
    chord: str  # E.g., "G", "Bm", "C/G"
    position: int  # Character position in text

@dataclass
class SongSection:
    name: str  # E.g., "Verse 1", "Chorus", "IntroTurn"
    type: str  # "verse", "chorus", "bridge", "instrumental"
    lines: list[ChordProLine]
    repeat: int = 1
    notes: list[str] | None = None

@dataclass
class SongYAML:
    title: str
    authors: list[str]
    ccli_number: str | None
    copyright: str | None
    original_key: str | None
    target_key: str
    bpm: int | None
    time_signature: str | None
    capo: str | None
    sections: dict[str, SongSection]  # key = section name
    arrangement: list[str]  # ordered section names
    practice_notes: dict[str, list[str]] | None
```

### 4. Arrangement_Engine

**Responsibility**: Create and manage song maps (section sequences).

**Public Interface**:
```python
def propose_arrangement(sections: dict[str, SongSection]) -> list[str]:
    """
    Generate default arrangement based on section types.
    Returns ordered list of section names.
    """

def validate_arrangement(
    arrangement: list[str],
    sections: dict[str, SongSection]
) -> tuple[bool, list[str]]:
    """
    Verify all arrangement items reference existing sections.
    Returns (is_valid, error_messages).
    """

def update_arrangement(
    current: list[str],
    modification: ArrangementEdit
) -> list[str]:
    """
    Apply reorder/repeat/insert operations to arrangement.
    """
```


**Data Structures**:
```python
@dataclass
class ArrangementEdit:
    operation: str  # "reorder", "repeat", "insert", "delete"
    section_name: str
    target_position: int | None = None
    repeat_count: int | None = None
```

### 5. Song_Validator

**Responsibility**: Check song data for completeness and correctness.

**Public Interface**:
```python
def validate_song(song: SongYAML, check_placeholders: bool = False) -> ValidationResult:
    """
    Validate song data completeness, chord symbols, arrangement references.
    Optional placeholder text checking.
    """

def estimate_slide_overflow(song: SongYAML, style: str) -> list[OverflowWarning]:
    """
    Estimate if any slides will overflow based on content length.
    """

def check_licensing(song: SongYAML) -> list[str]:
    """
    Return copyright/CCLI warnings if information incomplete.
    """
```

**Data Structures**:
```python
@dataclass
class ValidationResult:
    is_valid: bool
    errors: list[str]
    warnings: list[str]

@dataclass
class OverflowWarning:
    section_name: str
    estimated_lines: int
    max_lines: int
    suggestion: str
```

### 6. Marp_Generator

**Responsibility**: Convert YAML to Marp markdown with styled ChordPro.

**Public Interface**:
```python
def generate_marp(
    song: SongYAML,
    style: str = "practice",
    options: MarpOptions | None = None
) -> str:
    """
    Generate Marp markdown from structured song data.
    Returns markdown string.
    """

def format_chordpro_line(line: ChordProLine) -> str:
    """
    Pretty print ChordPro line with inline chord spans.
    Example: 'Who <span class="chord">Bm</span> else commands'
    """
```

**Data Structures**:
```python
@dataclass
class MarpOptions:
    show_song_map: bool = True
    show_metadata: bool = True
    show_practice_notes: bool = True
    font_size: str = "24px"  # CSS size for lyrics
    aspect_ratio: str = "16:9"
```


### 7. HTML_Renderer

**Responsibility**: Convert Marp markdown to standalone HTML.

**Public Interface**:
```python
def render_html(
    marp_markdown: str,
    output_path: str | None = None
) -> str:
    """
    Execute Marp CLI to render HTML.
    Returns path to generated HTML file.
    """

def verify_marp_cli() -> bool:
    """
    Check if Marp CLI is installed and accessible.
    """
```

**Implementation Notes**:
- Uses subprocess to invoke `marp` command
- Marp CLI must be installed: `npm install -g @marp-team/marp-cli`
- HTML output is fully standalone (embedded CSS, no external deps)
- Security: validate and sanitize markdown before rendering

### 8. Slide_Previewer

**Responsibility**: Display HTML slides with navigation in browser.

**Public Interface** (Frontend JavaScript):
```javascript
class SlidePreview {
  constructor(htmlContent, containerId)
  loadSlide(slideIndex)
  nextSlide()
  prevSlide()
  togglePresenterMode()
  toggleFullscreen()
  getOverflowWarnings()
}
```

**Backend API**:
```python
@api_bp.route('/preview', methods=['POST'])
def generate_preview(song_data: dict) -> dict:
    """
    Generate HTML preview from song data.
    Returns {html_content, warnings, slide_count}.
    """
```

## Data Models

### YAML Song Structure

The structured YAML format matches the existing JSON schema with ChordPro extensions:

```yaml
title: Only A Holy God
authors:
  - Michael Farren
  - Jonny Robinson
  - Dustin Smith
  - Rich Thompson
ccli_number: 7073332
copyright: "© 2016 CityAlight Music"

source:
  type: official_chord_chart
  provider: CityAlight
  source_key: D
  target_key: D
  bpm: 74
  time_signature: 6/8
  verify_before_use:
    - exact lyrics
    - exact chords
    - church CCLI permission/reporting
    - whether target key should remain D

arrangement:
  - IntroTurn
  - Verse 1
  - Verse 2
  - Chorus
  - Verse 3
  - Chorus
  - Chorus
  - Verse 4
  - Chorus

sections:
  IntroTurn:
    type: instrumental
    repeat: 2
    lines:
      - chordpro: "[Bm]      [G]      [D]      [A]"

  Verse 1:
    type: verse
    lines:
      - chordpro: "Who [Bm]else commands the [G]time with His [D]hand?"
      - chordpro: "Who [Bm]else reveals the [G]mysteries of [D]man?"
      - chordpro: "Who [Bm]else has power to [G]raise the [D]dead?"
      - chordpro: "Who [Bm]else but [G]O - [A]nly our [D]God?"

  Chorus:
    type: chorus
    lines:
      - chordpro: "Come and [Bm]behold [G]Him"
      - chordpro: "The [D]One and the [A]O - nly"
      - chordpro: "Cry [Bm]out, He is [G]holy"
      - chordpro: "A[D]wesome in [A]splendor"
      - chordpro: "[G]O - nly a [A]holy [Bm]God"

practice_notes:
  general:
    - "Keep the verses restrained so the repeated choruses can build."
    - "Consider a quieter Verse 4 before final Chorus."
  intro:
    - "Use IntroTurn progression x2."
  chorus:
    - "Chorus after Verse 3 is repeated twice."
  ending:
    - "Confirm whether to end after final Chorus or add extra tag."
```


### ChordPro Parsing Data Model

**Input Format**: ChordPro notation with brackets
```
[G]Amazing [D/F#]grace how [Em]sweet the [C]sound
```

**Parsed Representation**:
```python
ChordProLine(
    text="Amazing grace how sweet the sound",
    chords=[
        ChordPosition(chord="G", position=0),
        ChordPosition(chord="D/F#", position=8),
        ChordPosition(chord="Em", position=17),
        ChordPosition(chord="C", position=27)
    ]
)
```

**Pretty-Printed Output** (for Marp markdown):
```html
<span class="chord">G</span>Amazing <span class="chord">D/F#</span>grace how <span class="chord">Em</span>sweet the <span class="chord">C</span>sound
```

### Storage Model

The persistent storage structure mirrors the current system but adds YAML files:

```
src/saved_slides/
├── <uuid>.yaml       ← Structured song data (source of truth)
├── <uuid>.marp.md    ← Generated Marp markdown
├── <uuid>.html       ← Rendered HTML slide deck
├── <uuid>.json       ← Metadata sidecar (title, artist, key, filenames)
├── <uuid>.pptx       ← Optional backward-compatible PPTX export
└── all_songs.html    ← Compiled multi-song deck with index
```

**Metadata JSON** (enhanced):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Only A Holy God",
  "artist": "CityAlight",
  "key": "D",
  "bpm": 74,
  "time_signature": "6/8",
  "ccli_number": "7073332",
  "filenames": {
    "yaml": "550e8400-e29b-41d4-a716-446655440000.yaml",
    "marp": "550e8400-e29b-41d4-a716-446655440000.marp.md",
    "html": "550e8400-e29b-41d4-a716-446655440000.html",
    "pptx": "550e8400-e29b-41d4-a716-446655440000.pptx"
  },
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:35:00Z"
}
```

## ChordPro Parser Design

### Parsing Algorithm

**Phase 1: Tokenization**
```python
def tokenize_chordpro(raw_line: str) -> list[Token]:
    """
    Split line into chord tokens [Chord] and text tokens.
    Example: "Who [Bm]else" → [Text("Who "), Chord("Bm"), Text("else")]
    """
    tokens = []
    pattern = r'\[([^\]]+)\]'
    last_pos = 0
    
    for match in re.finditer(pattern, raw_line):
        # Add text before chord
        if match.start() > last_pos:
            tokens.append(Text(raw_line[last_pos:match.start()]))
        # Add chord
        tokens.append(Chord(match.group(1)))
        last_pos = match.end()
    
    # Add remaining text
    if last_pos < len(raw_line):
        tokens.append(Text(raw_line[last_pos:]))
    
    return tokens
```

**Phase 2: Position Calculation**
```python
def calculate_positions(tokens: list[Token]) -> ChordProLine:
    """
    Calculate character positions for each chord.
    """
    text_parts = []
    chords = []
    current_pos = 0
    
    for token in tokens:
        if isinstance(token, Text):
            text_parts.append(token.value)
            current_pos += len(token.value)
        elif isinstance(token, Chord):
            chords.append(ChordPosition(
                chord=token.value,
                position=current_pos
            ))
    
    return ChordProLine(
        text=''.join(text_parts),
        chords=chords
    )
```


### Pretty Printing Algorithm

**Goal**: Convert ChordProLine back to displayable format with inline chord styling.

```python
def pretty_print_chordpro(line: ChordProLine, format: str = "html") -> str:
    """
    Generate styled output with chords inline with lyrics.
    Format options: "html" (Marp), "plain" (terminal), "chordpro" (bracket notation)
    """
    if format == "chordpro":
        # Reconstruct bracket notation for round-trip
        return reconstruct_brackets(line)
    
    elif format == "html":
        # Generate HTML with <span class="chord"> tags
        result = []
        last_pos = 0
        
        for chord_pos in sorted(line.chords, key=lambda c: c.position):
            # Add text before chord
            if chord_pos.position > last_pos:
                result.append(escape_html(line.text[last_pos:chord_pos.position]))
            # Add chord
            result.append(f'<span class="chord">{escape_html(chord_pos.chord)}</span>')
            last_pos = chord_pos.position
        
        # Add remaining text
        if last_pos < len(line.text):
            result.append(escape_html(line.text[last_pos:]))
        
        return ''.join(result)
    
    elif format == "plain":
        # Terminal-friendly: chord line above lyric line
        return format_two_line_display(line)

def reconstruct_brackets(line: ChordProLine) -> str:
    """
    Reconstruct original bracket notation for round-trip property.
    """
    result = []
    last_pos = 0
    
    for chord_pos in sorted(line.chords, key=lambda c: c.position):
        # Add text before chord
        result.append(line.text[last_pos:chord_pos.position])
        # Add bracketed chord
        result.append(f'[{chord_pos.chord}]')
        last_pos = chord_pos.position
    
    # Add remaining text
    result.append(line.text[last_pos:])
    
    return ''.join(result)
```

### Transposition with Position Preservation

```python
def transpose_line(line: ChordProLine, semitones: int, use_flats: bool) -> ChordProLine:
    """
    Transpose all chords while preserving exact positions.
    """
    return ChordProLine(
        text=line.text,  # Text unchanged
        chords=[
            ChordPosition(
                chord=transpose_chord(cp.chord, semitones, use_flats),
                position=cp.position  # Position preserved
            )
            for cp in line.chords
        ]
    )
```

## Marp Markdown Generation Strategy

### Template Structure

Each song generates a multi-slide Marp presentation:

**Slide 1: Title Slide**
- Song title, authors, CCLI
- Key, BPM, time signature, capo
- Complete song map (arrangement sequence)
- General practice notes
- Copyright notice

**Slides 2-N: Section Slides**
- Section header (e.g., "Verse 1", "Chorus")
- Metadata bar (key, BPM, time, capo)
- Lyrics with inline chords (styled spans)
- Song map with current position highlighted
- Section-specific practice notes

### Marp Markdown Example

```markdown
---
marp: true
theme: default
paginate: true
size: 16:9
---

<style>
section { font-family: Arial, sans-serif; color: #111827; padding: 34px 42px; }
h1 { color: #1d4ed8; font-size: 44px; margin: 0 0 12px; }
h2 { color: #1d4ed8; font-size: 36px; margin: 0 0 10px; }
.meta { display: flex; gap: 18px; font-size: 18px; font-weight: 700; 
        border-bottom: 2px solid #d1d5db; padding-bottom: 8px; margin-bottom: 16px; }
.layout { display: grid; grid-template-columns: 2.1fr 0.9fr; gap: 22px; }
.line { font-family: "Courier New", monospace; font-size: 24px; 
        line-height: 1.3; margin: 10px 0; }
.chord { color: #c2410c; font-weight: 800; }
.lyric { color: #111827; }
.song-map { font-size: 18px; line-height: 1.5; }
.current { background: #dbeafe; color: #1d4ed8; font-weight: 800; 
           padding: 2px 6px; border-radius: 4px; }
.cue-box { background: #eef2f7; border-left: 6px solid #64748b; 
           padding: 12px 14px; font-size: 21px; line-height: 1.35; }
</style>

# [Song Title]

<div class="meta">
<span>Key: [D]</span><span>BPM: [74]</span><span>Time: [6/8]</span><span>Capo: [none]</span>
</div>

**Authors:** [Author List]  
**Song map:** IntroTurn → Verse 1 → Verse 2 → Chorus → ...

<div class="cue-box">[General practice notes]</div>

---

## [Section Name]

<div class="meta">
<span>Key: [D]</span><span>BPM: [74]</span><span>Time: [6/8]</span><span>Capo: [none]</span>
</div>

<div class="layout">
<div>
<div class="line">[ChordPro line rendered as HTML]</div>
<div class="line">[ChordPro line rendered as HTML]</div>
</div>
<div class="song-map">
Section1 → <span class="current">Section2</span> → Section3<br><br>
Current cue: [Section-specific note]<br>
Next: [Next section name]
</div>
</div>
```


### Generation Algorithm

```python
def generate_marp_slides(song: SongYAML, style: str) -> str:
    """
    Generate complete Marp markdown document.
    """
    slides = []
    
    # Title slide
    slides.append(generate_title_slide(song, style))
    
    # Section slides following arrangement
    for idx, section_name in enumerate(song.arrangement):
        section = song.sections[section_name]
        next_section = song.arrangement[idx + 1] if idx + 1 < len(song.arrangement) else None
        slides.append(generate_section_slide(
            section_name=section_name,
            section=section,
            song_map=song.arrangement,
            current_index=idx,
            next_section=next_section,
            metadata=extract_metadata(song),
            style=style
        ))
    
    # Combine with frontmatter and CSS
    return assemble_marp_document(slides, style)

def generate_section_slide(
    section_name: str,
    section: SongSection,
    song_map: list[str],
    current_index: int,
    next_section: str | None,
    metadata: dict,
    style: str
) -> str:
    """
    Generate markdown for a single section slide.
    """
    lines_html = []
    for line in section.lines:
        lines_html.append(f'<div class="line">{pretty_print_chordpro(line, "html")}</div>')
    
    song_map_html = render_song_map(song_map, current_index)
    
    return f"""
## {section_name}

<div class="meta">
<span>Key: {metadata['key']}</span><span>BPM: {metadata['bpm']}</span>
<span>Time: {metadata['time']}</span><span>Capo: {metadata['capo']}</span>
</div>

<div class="layout">
<div>
{''.join(lines_html)}
</div>
<div class="song-map">
{song_map_html}<br><br>
Next: {next_section or "End"}
</div>
</div>
"""
```

## HTML Rendering Approach

### Marp CLI Integration

**Installation**: `npm install -g @marp-team/marp-cli`

**Rendering Command**:
```python
def render_html(marp_file: str, output_file: str) -> subprocess.CompletedProcess:
    """
    Execute Marp CLI to render standalone HTML.
    """
    cmd = [
        'marp',
        marp_file,
        '--html',
        '--allow-local-files',
        '-o', output_file
    ]
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=30  # Prevent hanging
    )
    
    if result.returncode != 0:
        raise RenderError(f"Marp CLI failed: {result.stderr}")
    
    return result
```

**Security Considerations**:
- Validate markdown content before rendering (no script injection)
- Use `--no-stdin` to prevent interactive input
- Set timeout to prevent resource exhaustion
- Run in isolated process with limited permissions
- Sanitize any user-provided text in markdown

### HTML Output Features

The generated HTML includes:
- **Embedded CSS**: All styles inline, no external dependencies
- **Keyboard navigation**: Arrow keys, Page Up/Down
- **Presenter mode**: Speaker notes (practice notes) in presenter view
- **Fullscreen support**: F11 or fullscreen API
- **Print-friendly**: CSS print styles for PDF export via browser
- **Self-contained**: Single file with no external resources


## Frontend Preview and Editing Workflow

### Preview Interface Components

**HTML Slide Container**:
```javascript
class SlidePreview {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.currentSlide = 0;
    this.totalSlides = 0;
    this.htmlContent = null;
  }
  
  loadPreview(htmlContent) {
    // Inject HTML into iframe for isolation
    const iframe = document.createElement('iframe');
    iframe.srcdoc = htmlContent;
    this.container.innerHTML = '';
    this.container.appendChild(iframe);
    
    // Parse slide count from HTML
    this.totalSlides = this.extractSlideCount(htmlContent);
  }
  
  navigate(direction) {
    // Send postMessage to iframe to change slides
    // Marp HTML has built-in navigation we can trigger
  }
  
  togglePresenterMode() {
    // Enable Marp presenter mode
  }
  
  toggleFullscreen() {
    if (document.fullscreenElement) {
      document.exitFullscreen();
    } else {
      this.container.requestFullscreen();
    }
  }
}
```

### Edit-Regenerate Workflow

**Backend API Endpoint**:
```python
@api_bp.route('/regenerate', methods=['POST'])
def regenerate_preview():
    """
    Regenerate preview after user edits.
    Input: Modified SongYAML as JSON
    Output: { html_content, marp_markdown, warnings, slide_count }
    """
    song_data = request.json
    
    # Validate song data
    song = parse_song_yaml(song_data)
    validation = validate_song(song)
    
    if not validation.is_valid:
        return jsonify({'error': validation.errors}), 400
    
    # Generate Marp markdown
    marp_md = generate_marp(song, style=song_data.get('style', 'practice'))
    
    # Render HTML
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as md_file:
        md_file.write(marp_md)
        md_path = md_file.name
    
    with tempfile.NamedTemporaryFile(mode='r', suffix='.html', delete=False) as html_file:
        html_path = html_file.name
    
    try:
        render_html(md_path, html_path)
        
        with open(html_path, 'r') as f:
            html_content = f.read()
        
        return jsonify({
            'html_content': html_content,
            'marp_markdown': marp_md,
            'warnings': validation.warnings,
            'slide_count': count_slides(marp_md)
        })
    finally:
        os.unlink(md_path)
        os.unlink(html_path)
```

**Frontend Edit Form**:
```javascript
class SongEditor {
  constructor(songData) {
    this.songData = songData;
    this.debounceTimer = null;
  }
  
  onFieldEdit(field, value) {
    // Update local song data
    this.updateField(field, value);
    
    // Debounce regeneration (wait 500ms after last edit)
    clearTimeout(this.debounceTimer);
    this.debounceTimer = setTimeout(() => {
      this.regeneratePreview();
    }, 500);
  }
  
  onBlur() {
    // Immediate regeneration on blur
    clearTimeout(this.debounceTimer);
    this.regeneratePreview();
  }
  
  async regeneratePreview() {
    const response = await fetch('/api/regenerate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(this.songData)
    });
    
    const result = await response.json();
    
    if (result.html_content) {
      slidePreview.loadPreview(result.html_content);
      this.displayWarnings(result.warnings);
    }
  }
}
```

### Editable Fields

- **Metadata**: Key, capo, BPM, time signature, leader, practice notes
- **Arrangement**: Reorder sections, add/remove repeats
- **Lyrics/Chords**: Direct ChordPro editing with syntax highlighting
- **Slide Style**: Toggle between practice/performance/simple
- **Display Options**: Font size, song map visibility, metadata visibility


## API Endpoints

### New/Modified Endpoints

**Song Search and Identification**
```
GET /api/identify?song={name}&artist={artist}
Response: { matches: [SongMatch], single_match: bool }

POST /api/select_match
Body: { match_id: string }
Response: { metadata: SongMetadata, chart_sources: [string] }
```

**Chart Retrieval**
```
POST /api/retrieve_chart
Body: { metadata: SongMetadata, user_chart?: string, target_key?: string }
Response: { chart: ChartData, review_prompt: ReviewPrompt }

POST /api/confirm_chart
Body: { chart_id: string, verified_items: [string] }
Response: { confirmed: bool }
```

**YAML Generation**
```
POST /api/generate_yaml
Body: { metadata: SongMetadata, chart: ChartData, target_key?: string }
Response: { yaml: SongYAML, validation: ValidationResult }
```

**Preview and Editing**
```
POST /api/preview
Body: { song: SongYAML, style: string, options?: MarpOptions }
Response: { html_content: string, marp_markdown: string, warnings: [string], slide_count: int }

POST /api/regenerate
Body: { song: SongYAML, style: string, options?: MarpOptions }
Response: { html_content: string, marp_markdown: string, warnings: [string], slide_count: int }
```

**Download Endpoints**
```
POST /api/download/html
Body: { song: SongYAML, style: string }
Response: File download (standalone HTML)

POST /api/download/marp
Body: { song: SongYAML, style: string }
Response: File download (Marp markdown)

POST /api/download/yaml
Body: { song: SongYAML }
Response: File download (YAML source)

POST /api/download/pdf
Body: { song: SongYAML, style: string }
Response: File download (PDF via Marp CLI)

POST /api/download/pptx
Body: { song: SongYAML }
Response: File download (PowerPoint - backward compatibility)
```

**Library Management**
```
POST /api/save_slide
Body: { song: SongYAML, style: string, formats: [string] }
Response: { id: string, metadata: dict, filenames: dict }

GET /api/saved_slides
Response: { slides: [SlideMetadata] }

GET /api/saved_slide/{id}
Response: { metadata: dict, yaml: SongYAML, filenames: dict }

GET /api/saved_slide/{id}/download/{format}
Response: File download (html/marp/yaml/pdf/pptx)

DELETE /api/saved_slide/{id}
Response: { success: bool }

PUT /api/saved_slide/{id}
Body: { song: SongYAML, style: string }
Response: { updated: bool, metadata: dict }
```

**Batch Compilation**
```
POST /api/compile
Body: { slide_ids: [string], order: [string], style: string }
Response: File download (compiled HTML with index)
```

**Validation Endpoints**
```
POST /api/validate
Body: { song: SongYAML, check_placeholders: bool }
Response: { validation: ValidationResult, overflow_warnings: [OverflowWarning] }

POST /api/transpose
Body: { song: SongYAML, target_key: string }
Response: { transposed: SongYAML, semitones: int }
```

### Error Response Format

All endpoints return errors in consistent format:
```json
{
  "error": "Human-readable error message",
  "error_code": "VALIDATION_FAILED",
  "details": {
    "field": "specific field with error",
    "reason": "detailed explanation"
  }
}
```


## Migration Strategy from PPTX System

### Phase 1: Parallel Implementation (Weeks 1-2)

**Goal**: Add new HTML/Marp pipeline without breaking existing PPTX functionality.

**Tasks**:
1. Install Marp CLI and verify in development environment
2. Implement ChordPro parser with round-trip tests
3. Create YAML schema validation
4. Build Marp generator for basic slides
5. Add HTML rendering wrapper around Marp CLI

**Testing**:
- Existing PPTX tests continue to pass
- New ChordPro parser tests verify round-trip property
- Marp rendering tests validate HTML output

### Phase 2: Preview Integration (Weeks 3-4)

**Goal**: Add web-based preview with HTML slides alongside PPTX downloads.

**Tasks**:
1. Create `/api/preview` endpoint returning HTML
2. Build frontend SlidePreview component
3. Add YAML editor with live regeneration
4. Implement multi-format download (HTML, Marp MD, YAML, PPTX)
5. Update UI to show both preview and PPTX download options

**Testing**:
- Preview loads and navigates correctly
- Edit-regenerate workflow functions without errors
- All download formats produce valid output

### Phase 3: Storage Migration (Weeks 5-6)

**Goal**: Migrate saved_slides directory to include YAML/HTML files.

**Tasks**:
1. Update `slide_storage.py` to save YAML + Marp + HTML alongside PPTX
2. Enhance metadata JSON with multi-format filenames
3. Add backward-compatible loader for old PPTX-only slides
4. Implement batch conversion utility for existing slides
5. Update compilation logic for HTML index slides

**Migration Script**:
```python
def migrate_existing_slides():
    """
    Convert existing PPTX-only slides to new format.
    Preserves existing files, adds new YAML/HTML versions.
    """
    slides = list_slides()
    
    for slide_meta in slides:
        slide_id = slide_meta['id']
        
        # Check if already migrated
        yaml_path = _yaml_path(slide_id)
        if os.path.exists(yaml_path):
            continue
        
        # Load PPTX and extract song data
        pptx_path = _slide_path(slide_id)
        song_data = extract_song_data_from_pptx(pptx_path)
        
        # Generate YAML from extracted data
        song_yaml = convert_legacy_to_yaml(song_data)
        
        # Save new formats
        save_yaml(slide_id, song_yaml)
        generate_and_save_marp(slide_id, song_yaml)
        generate_and_save_html(slide_id, song_yaml)
        
        # Update metadata JSON
        update_metadata_with_formats(slide_id)
        
        logger.info(f"Migrated slide {slide_id}: {slide_meta['title']}")
```

### Phase 4: Feature Parity (Weeks 7-8)

**Goal**: Achieve feature parity with existing PPTX system.

**Tasks**:
1. Implement arrangement editing UI
2. Add song map visualization
3. Build practice notes editor
4. Create validation warnings display
5. Implement batch compilation with clickable index

**Testing**:
- All existing user workflows work with new system
- Performance benchmarks meet or exceed PPTX system
- User acceptance testing with real worship teams

### Phase 5: Deprecation Path (Week 9+)

**Goal**: Phase out PPTX generation, make HTML the primary format.

**Options**:
- **Option A (Soft Deprecation)**: Keep PPTX as "legacy export" option
- **Option B (Hard Deprecation)**: Remove PPTX generation entirely after migration period
- **Recommended**: Option A for 6-12 months, then evaluate Option B

**Communication**:
- Add deprecation notice to PPTX download: "PPTX export is legacy. HTML is recommended."
- Update documentation to emphasize HTML workflow
- Collect user feedback on PPTX necessity

### Rollback Plan

If critical issues arise:

1. **Immediate Rollback**: Feature flag to disable HTML preview, restore PPTX-only mode
2. **Data Safety**: All migrations preserve original PPTX files
3. **API Compatibility**: Old `/api/download` endpoint continues to work
4. **Monitoring**: Track error rates on new endpoints, auto-disable if threshold exceeded


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property Assessment

This feature combines pure data transformation logic (ChordPro parsing, transposition, YAML generation) with infrastructure integration (Marp CLI execution, file I/O, external API calls) and UI interaction. Property-based testing (PBT) is appropriate for the pure transformation components but NOT for infrastructure, external services, or UI workflows.

**PBT IS appropriate for:**
- ChordPro parsing and pretty printing (round-trip property)
- Chord transposition algorithms (preservation properties)
- YAML structure validation (schema conformance)
- Data preservation through transformations
- Referential integrity validation

**PBT is NOT appropriate for:**
- Marp CLI execution (external tool integration)
- File I/O operations (infrastructure)
- External API calls (Worship Together, CCLI)
- UI interactions and workflows
- Browser rendering behavior

The correctness properties below focus on the testable data transformation logic.

### Property 1: ChordPro Round-Trip Preservation

*For any* valid ChordProLine, parsing the reconstructed bracket notation SHALL produce an equivalent ChordProLine with identical text and chord positions.

**Validates: Requirements 5.5**

**Implementation Note**: This is the critical property for ChordPro correctness. Given a ChordProLine, convert to bracket notation via `reconstruct_brackets()`, parse back via `parse_chordpro()`, and verify the resulting ChordProLine matches the original.

### Property 2: User Input Preservation Through Workflow

*For any* valid song input including optional parameters (target key, arrangement, style, notes), processing through the complete workflow SHALL preserve all original input values in the final output.

**Validates: Requirements 1.5**

### Property 3: Metadata Completeness in Search Results

*For any* successful song search result, the metadata SHALL contain all required fields (title, authors, ccli_number, original_key, bpm, time_signature, source_urls) with either valid values or explicit null indicators.

**Validates: Requirements 2.2**

### Property 4: Chart Retrieval Priority Ordering

*For any* set of available chart sources, the Chart_Retriever SHALL select the highest priority available source according to the defined order: user-provided → official publisher → official artist → CCLI → manual.

**Validates: Requirements 3.1**

### Property 5: Chart Review Flag Consistency

*For any* chart retrieved from any source, the ChartData SHALL have the needs_review flag set to true and include non-empty review_items list.

**Validates: Requirements 3.2**

### Property 6: Review Prompt Completeness

*For any* chart requiring review, the ReviewPrompt SHALL include all four verification items: lyrics accuracy, chord accuracy, CCLI permission status, and target key appropriateness.

**Validates: Requirements 3.3**

### Property 7: Chart Source Metadata Preservation

*For any* retrieved chart, the ChartData SHALL include both source_type and source_url (or explicit null if URL unavailable), preserving the origin information.

**Validates: Requirements 3.5**


### Property 8: YAML Structure Completeness

*For any* Song_Parser output, the resulting YAML SHALL contain all required top-level fields: title, authors, key, bpm, time_signature, ccli_number, sections, and arrangement.

**Validates: Requirements 4.2**

### Property 9: ChordPro Format Validity in YAML Sections

*For any* YAML section containing lyrics, all line entries SHALL contain valid ChordPro notation with properly paired brackets and valid chord symbols.

**Validates: Requirements 4.3**

### Property 10: Chord Position Preservation During Parsing

*For any* raw chord chart with known chord positions, after parsing the relative positions of chords to lyric syllables SHALL remain unchanged.

**Validates: Requirements 4.4**

### Property 11: ChordPro Parser Coverage

*For any* valid ChordPro line containing chords in brackets and plain text lyrics (including lines with 0, 1, or multiple chords), the parser SHALL successfully extract all chord symbols and their positions without errors.

**Validates: Requirements 5.1, 5.2**

### Property 12: Arrangement Referential Integrity

*For any* song with an arrangement sequence, all section names referenced in the arrangement SHALL correspond to existing sections in the sections dictionary.

**Validates: Requirements 6.7, 7.1**

### Property 13: Chord Symbol Validity

*For any* chord symbol in a parsed song, the symbol SHALL match the valid chord pattern (root note + optional accidental + optional suffix like m, maj7, sus4, dim, aug, add9, etc.) or be flagged as invalid by the validator.

**Validates: Requirements 7.2**

### Property 14: Section Label Presence

*For any* song section in the YAML structure, the section SHALL have a non-empty name/label that uniquely identifies it within that song.

**Validates: Requirements 7.4**

### Property 15: Metadata Completeness Validation

*For any* song passed to the validator, the validation result SHALL correctly identify whether all required metadata fields (title, authors, key) are present and non-empty.

**Validates: Requirements 7.5**

### Property 16: Licensing Warning Generation

*For any* song with missing or incomplete CCLI number or copyright information, the validator SHALL generate appropriate warning messages in the ValidationResult.

**Validates: Requirements 7.6, 18.1, 18.2**

### Property 17: Marp Title Slide Structure

*For any* song converted to Marp markdown, the first slide SHALL contain all required elements: title, authors, key, BPM, time signature, complete song map sequence, and copyright notice (if available).

**Validates: Requirements 8.2**

### Property 18: Marp Section Slide Completeness

*For any* section in the arrangement sequence, the generated Marp slide SHALL include: section header, metadata bar (key/BPM/time/capo), lyrics with inline chord spans, song map with current position indicator, and next section cue.

**Validates: Requirements 8.3**

### Property 19: Inline Chord Formatting

*For any* ChordProLine rendered to HTML format, chords SHALL appear as `<span class="chord">` elements positioned inline with the corresponding lyric text at the correct character positions.

**Validates: Requirements 8.4**

### Property 20: CSS Inclusion in Marp Output

*For any* generated Marp markdown document, the output SHALL include a complete `<style>` block defining all required CSS classes (chord, lyric, meta, song-map, current, cue-box, etc.).

**Validates: Requirements 8.5**

### Property 21: HTML Standalone Property

*For any* rendered HTML slide deck, the document SHALL contain no external resource references (no `<link>`, `<script src>`, or `<img src>` tags pointing to external URLs), ensuring standalone operation.

**Validates: Requirements 9.2**

### Property 22: Style Preservation in HTML Rendering

*For any* Marp markdown with custom CSS styles, the rendered HTML SHALL preserve all style definitions, ensuring visual consistency between markdown and HTML output.

**Validates: Requirements 9.4**

### Property 23: Multi-Format Storage Consistency

*For any* saved slide, the storage SHALL contain all three primary formats (YAML, Marp markdown, HTML) with consistent content derived from the same source YAML.

**Validates: Requirements 14.3**


### Property 24: Compilation Completeness

*For any* set of selected slides for compilation, the compiled HTML SHALL contain all sections from all selected songs in the user-specified order.

**Validates: Requirements 15.2, 15.4**

### Property 25: Clickable Index Functionality

*For any* compiled multi-song deck, the index slide SHALL contain clickable elements for each included song, with each element correctly linked to that song's first slide.

**Validates: Requirements 15.3**

### Property 26: Style-Specific Element Inclusion

*For any* song rendered with "practice" style, the output SHALL include song map, full metadata, and practice notes; with "performance" style, the output SHALL emphasize lyrics and minimize metadata; with "simple" style, the output SHALL use minimal formatting.

**Validates: Requirements 16.1, 16.2, 16.3, 16.5**

### Property 27: Transposition Correctness

*For any* valid original key and target key pair with a valid chord, transposing the chord SHALL produce a chord that is exactly the calculated semitone distance from the original, maintaining the same chord quality.

**Validates: Requirements 13.1**

### Property 28: Chord Suffix Preservation During Transposition

*For any* chord with a suffix (m, maj7, sus4, dim, aug, add9, etc.), transposing the chord SHALL preserve the exact suffix while only changing the root note.

**Validates: Requirements 13.2**

### Property 29: Slash Chord Transposition

*For any* slash chord (root/bass notation like C/G), transposing SHALL correctly transpose both the root note and the bass note by the same semitone interval.

**Validates: Requirements 13.3**

### Property 30: Accidental Consistency in Transposition

*For any* target key, all transposed chords SHALL consistently use either sharps or flats according to the target key's convention (sharp keys use sharps, flat keys use flats).

**Validates: Requirements 13.4**

### Property 31: Enharmonic Equivalence Handling

*For any* chord using an enharmonic equivalent (C# vs Db, D# vs Eb, etc.), the transposition algorithm SHALL correctly interpret the input and produce output in the appropriate enharmonic form for the target key.

**Validates: Requirements 13.5**

### Property 32: Song Map Current Position Highlighting

*For any* slide displaying a song map, exactly one section in the map SHALL be marked as current (highlighted), corresponding to the section displayed on that slide.

**Validates: Requirements 17.1**

### Property 33: Next Section Display

*For any* slide except the final slide, the song map or cue area SHALL display the name of the next section in the arrangement sequence.

**Validates: Requirements 17.2**

### Property 34: Section-Specific Note Display

*For any* section with associated practice notes, those notes SHALL appear on the slide(s) displaying that section, and SHALL NOT appear on slides for sections without associated notes.

**Validates: Requirements 17.3**

### Property 35: Practice Mode Song Map Visibility

*For any* song rendered in practice mode, the song map SHALL appear on all slides (both title slide and all section slides).

**Validates: Requirements 17.4**

### Property 36: Complete Arrangement Sequence in Song Map

*For any* song map display, the complete ordered sequence of all sections in the arrangement SHALL be shown without omissions.

**Validates: Requirements 17.5**

### Property 37: Copyright Notice Inclusion

*For any* song with copyright information, the title slide SHALL display the copyright notice text.

**Validates: Requirements 18.3**

### Property 38: CCLI Number Display

*For any* song with a CCLI number, the title slide SHALL include the CCLI number; for songs without a CCLI number, no CCLI field SHALL be displayed or it SHALL be marked as absent.

**Validates: Requirements 18.4**

### Property 39: CCLI Permission Reminder

*For any* song validated by the Song_Validator, the validation output SHALL include a reminder message about verifying CCLI permission before use.

**Validates: Requirements 18.5**


## Error Handling

### Error Categories

**Parse Errors**:
- Invalid ChordPro syntax: malformed brackets, unclosed chords
- Invalid YAML structure: schema violations, missing required fields
- Invalid chord symbols: unrecognized chord notation

**Validation Errors**:
- Arrangement references non-existent sections
- Missing required metadata (title, authors)
- Incomplete licensing information (CCLI, copyright)
- Content overflow warnings

**External Service Errors**:
- Song search API failures (timeouts, rate limits, connection errors)
- Chart retrieval failures (404, access denied)
- Marp CLI errors (not installed, execution failure, timeout)

**File System Errors**:
- Storage directory inaccessible
- Disk space exhausted
- File permissions issues

### Error Handling Strategy

**Parse Errors**: Return detailed error with line/position information, allow user correction

**Validation Errors**: Return warnings list, allow proceeding with warnings or require fixes based on severity

**External Service Errors**: Retry with exponential backoff (3 attempts), fallback to manual input if all attempts fail

**File System Errors**: Fail fast with clear error message, suggest resolution steps

### Error Response Structure

```python
@dataclass
class ErrorResponse:
    error_code: str  # Machine-readable: "PARSE_ERROR", "VALIDATION_FAILED"
    message: str  # Human-readable description
    details: dict | None = None  # Additional context
    recoverable: bool = True  # Whether user can fix and retry
    suggestions: list[str] | None = None  # Resolution steps
```

### Retry Logic

```python
def retry_with_backoff(func, max_attempts=3, base_delay=1.0):
    """
    Retry function with exponential backoff.
    """
    for attempt in range(max_attempts):
        try:
            return func()
        except RetryableError as e:
            if attempt == max_attempts - 1:
                raise
            delay = base_delay * (2 ** attempt)
            time.sleep(delay)
```

## Testing Strategy

### Unit Testing

**Core Transformation Logic** (PBT appropriate):
- ChordPro parser: round-trip property tests with 100+ iterations
- Transposition: property tests for suffix preservation, slash chord handling, accidental consistency
- YAML validation: schema conformance with generated valid/invalid inputs
- Arrangement validation: referential integrity with random section sets
- Metadata completeness: validation with various combinations of present/missing fields

**Helper Functions** (Example-based):
- URL formatting
- File path construction
- Metadata extraction
- CSS generation

**Test Framework**: pytest with hypothesis for property-based testing

**Minimum Iterations**: 100 per property test (due to randomization)

**Example Property Test**:
```python
from hypothesis import given, strategies as st
import pytest

@given(st.text(min_size=1))
def test_chordpro_round_trip(lyric_text):
    """
    Property: For any lyric text and chord positions, 
    parse → print → parse produces equivalent result.
    """
    # Generate random chord positions
    positions = generate_random_chord_positions(lyric_text)
    chords = generate_random_chords(len(positions))
    
    original = ChordProLine(
        text=lyric_text,
        chords=[ChordPosition(chord=c, position=p) 
                for c, p in zip(chords, positions)]
    )
    
    # Round trip
    bracket_notation = reconstruct_brackets(original)
    parsed = parse_chordpro(bracket_notation)
    
    # Verify equivalence
    assert parsed.text == original.text
    assert len(parsed.chords) == len(original.chords)
    for parsed_chord, original_chord in zip(parsed.chords, original.chords):
        assert parsed_chord.chord == original_chord.chord
        assert parsed_chord.position == original_chord.position
```

**Property Test Tags**: Each property test includes comment referencing design property
```python
# Feature: redesign-band-deck-to-html-focus, Property 1: ChordPro Round-Trip Preservation
def test_chordpro_round_trip_property():
    ...
```

### Integration Testing

**External Tool Integration**:
- Marp CLI execution with sample markdown
- File I/O operations with test directory
- Subprocess timeout handling

**API Endpoints**:
- End-to-end workflow tests: search → parse → generate → render
- Error response formatting
- File download endpoints

**Multi-Format Consistency**:
- Save slide, verify YAML/Marp/HTML all represent same song
- Edit YAML, regenerate, verify updates propagate

### Browser Testing

**HTML Rendering**:
- Load generated HTML in headless browser
- Verify slide navigation works
- Check fullscreen API availability
- Validate no external resource loads

**Cross-Browser**:
- Chrome, Firefox, Safari (manual or Selenium-based)

### Performance Testing

**Parsing**: ChordPro parser should handle 1000+ line songs in <100ms

**Rendering**: Marp CLI should render typical song (10 slides) in <2 seconds

**Storage**: Save operation should complete in <500ms

**Preview Regeneration**: Edit → regenerate → display should complete in <3 seconds

### Security Testing

**Input Validation**:
- ChordPro injection attempts (malicious bracket patterns)
- YAML bomb attempts (deeply nested structures)
- Path traversal in file operations

**Subprocess Safety**:
- Marp CLI command injection attempts
- Timeout enforcement (prevent resource exhaustion)

**XSS Prevention**:
- HTML entity escaping in chord/lyric display
- Script tag injection in markdown

## Dependencies and Technology Stack

### Python Libraries

**Core Dependencies** (add to pyproject.toml):
```toml
dependencies = [
  "Flask>=3.0",
  "requests>=2.30",
  "beautifulsoup4>=4.12",
  "pyyaml>=6.0",              # YAML parsing and generation
  "jsonschema>=4.20",         # YAML schema validation
]
```

**Development Dependencies**:
```toml
[dependency-groups]
dev = [
  "pytest>=7",
  "pytest-cov>=4",
  "hypothesis>=6.90",         # Property-based testing
  "ruff>=0.4",
]
```

### External Tools

**Marp CLI** (required for HTML rendering):
- Installation: `npm install -g @marp-team/marp-cli`
- Version: >=3.0.0
- Documentation: https://github.com/marp-team/marp-cli

**Node.js** (required for Marp CLI):
- Version: >=16.0.0
- Installation: via system package manager or nvm

### Frontend Libraries

**No build step required** - vanilla JavaScript with:
- Native Fetch API for HTTP requests
- Native Fullscreen API
- Native DOM manipulation
- No framework dependencies

### File Format Standards

**ChordPro**: https://www.chordpro.org/chordpro/chordpro-file-format-specification/
**YAML 1.2**: https://yaml.org/spec/1.2/spec.html
**JSON Schema 2020-12**: https://json-schema.org/draft/2020-12/schema

## Deployment Considerations

### Environment Setup

**Development**:
```bash
# Install Python dependencies
uv sync

# Install Marp CLI
npm install -g @marp-team/marp-cli

# Verify Marp CLI
marp --version

# Run development server
uv run python src/main.py
```

**Production**:
- Ensure Node.js and Marp CLI installed on server
- Configure subprocess timeout limits
- Set up proper file permissions for saved_slides directory
- Configure rate limiting appropriately
- Enable logging to track Marp CLI errors

### Resource Requirements

**Disk Space**: ~10MB per saved song (HTML includes embedded assets)
**Memory**: Marp CLI subprocess: ~50-100MB per render
**CPU**: Negligible except during Marp rendering (1-2 seconds)

### Monitoring

**Key Metrics**:
- Marp CLI execution time and failure rate
- Preview regeneration latency
- Storage directory size
- API endpoint error rates
- External API (Worship Together) success rates

**Health Checks**:
- Marp CLI availability: `marp --version` in health check endpoint
- Storage directory writability
- External API reachability

## Open Questions and Future Enhancements

### Open Questions

1. **Chart Source Priority**: Should user-provided charts bypass verification, or always require review?
2. **Compilation Size Limits**: Maximum number of songs in compiled deck?
3. **Preview Timeout**: What timeout for complex songs with many slides?
4. **Storage Retention**: Automatic cleanup of old/unused saved slides?

### Future Enhancements

**Phase 2 Features**:
- Multiple arrangement variants per song (rehearsal vs. service version)
- Setlist management with songs grouped by service date
- Collaborative editing with conflict resolution
- Mobile-optimized preview interface
- Offline PWA mode with service worker caching

**Advanced Features**:
- Audio sync: slide advancement tied to audio playback
- Chord diagram generation for guitar/piano
- Automatic key suggestion based on vocal range analysis
- Integration with Planning Center, ChurchTools, etc.
- Export to other formats: OpenSong, SongSelect, ProPresenter

**AI/ML Enhancements**:
- Automatic arrangement proposal using ML trained on common patterns
- Chord chart OCR for printed sheet music
- Automatic section detection from unstructured lyrics

## Conclusion

This design provides a comprehensive roadmap for transforming Band-Deck from a PowerPoint-centric tool into a modern HTML slide deck generator. The core innovations are:

1. **Structured data as source of truth**: YAML format enables editing and version control
2. **ChordPro standard adoption**: Industry-standard notation with round-trip guarantees
3. **Marp markdown generation**: Flexible, customizable slide styling
4. **Standalone HTML output**: Browser-viewable with no dependencies
5. **Interactive preview workflow**: Edit-regenerate loop for rapid iteration

The design maintains backward compatibility with PPTX export while prioritizing HTML as the primary format. The phased migration strategy allows incremental rollout with minimal risk, and the comprehensive testing strategy (combining property-based and example-based tests) ensures correctness of the core transformation logic.
