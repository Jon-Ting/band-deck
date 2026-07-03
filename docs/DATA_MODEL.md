# 🗄️ Band-Deck Data Model

## Overview

Band-Deck has no database. All state is stored as files on disk in `data/saved_slides/`. The core data structure is the **Song Data dict**, which flows through the entire pipeline.

---

## Song Data Dict

This is the central in-memory data structure passed between the registered scraper in `src/utils/search.py`, `yaml_converter.py`, `marp_generator.py`, `html_renderer.py`, `slide_storage.py`, and the API layer.

```python
{
    # Populated by the registered scraper
    "title":        str,          # Song title scraped from the page <h1>
    "search_name":  str,          # User's original search input (shown on slides)
    "artist":       str,          # Artist name (from search input, not scraped)
    "content":      str,          # Sectioned lyrics+chords (see Content Format below)
    "source_url":   str,          # Canonical URL of the scraped source page
    "original_key": str | None,   # Key detected by the active scraper; per-source convention varies

    # Added by the API layer (api.py)
    "key":          str | None,   # User-requested target key (post-transposition)
}
```

> The legacy `pptx_preview` field has been retired. The live editor now drives its preview pane from the rendered HTML returned by `POST /api/preview` (which embeds the same section/line structure internally).

> **Note**: `search_name` is preferred over `title` for display purposes (slide title, filename) because it reflects what the user typed, not what the scraper found. This allows searching "10000 Reasons" and getting a slide titled "10000 Reasons" even if the scraped title is "10,000 Reasons (Bless the Lord)".

---

## Content String Format

The `content` field is a plain-text string. Sections are separated by `\n\n`. The first line of each section is the section name; subsequent lines alternate between chord lines and lyric lines.

```
<Section Name>
<chord line>
<lyric line>
<chord line>
<lyric line>

<Next Section Name>
<chord line>
<lyric line>
```

**Example:**
```
Verse 1
G          Em         C          D
I love You Lord       Oh I see Your goodness

Chorus
G    D         Em        C
All my life    You have been faithful
```

Chords are space-padded so they align directly above the syllable they apply to. This alignment is significant — `src/utils/marp_generator.py` keeps the padded spacing verbatim in the Marp markdown, and the embedded `<style>` block uses a monospace typeface for chord/lyric lines so CSS layout preserves the alignment in the rendered HTML.

---

## Slide Metadata JSON (`.json` sidecar)

Each saved slide has a UUID-named JSON sidecar in `data/saved_slides/`.

```python
{
    "id":           str,                       # UUID (also the filename stem)
    "title":        str,                       # From search_name or title
    "artist":       str | None,
    "key":          str | None,
    "filenames":    {"yaml": "...yaml",
                     "marp": "...marp.md",
                     "html": "...html",
                     "pdf":  "...pdf"},        # Optional
    "created_at":   str,                       # ISO 8601 UTC
    "updated_at":   str,                       # ISO 8601 UTC
    "bpm":          int | None,                # Optional
    "time_signature": str | None,              # Optional
    "license_number":  str | None,                # Optional
}
```

This file is the source of truth for listing, downloading, and updating. The artefacts listed in `filenames` are the actual on-disk files keyed by `id`.

---

## File Storage Layout

```
data/saved_slides/
├── <uuid>.yaml       ← SongYAML source (typed dataclass tree, serialised via yaml.safe_dump)
├── <uuid>.marp.md    ← Marp markdown deck
├── <uuid>.html       ← Rendered HTML deck (from Marp CLI output)
├── <uuid>.json       ← Metadata sidecar
├── ...
└── (compiled.html    ← Compiled deck filename returned by /api/compile)
```

**Invariants:**
- Every `<uuid>.json` sidecar has at least one matching artefact (typically `.yaml` / `.marp.md` / `.html`) with the same stem.
- The compiled deck is a fresh output of `POST /api/compile`; it is not tracked in any sidecar.
- `clear_temp_files()` removes everything in `data/saved_slides/` whose extension is not in `{.yaml, .marp.md, .html, .json}` (PDF artefacts are also kept if present).

---

## Section Types

The following section names are recognized and parsed by the registered scraper:

| Name | Numbered? | Notes |
|------|-----------|-------|
| `Intro` | No | Treated as instrumental — chord-only lines kept |
| `Verse` | Yes (`Verse 1`, `Verse 2`, …) | |
| `Pre-Chorus` | No | |
| `Chorus` | Yes (`Chorus`, `Chorus 2`, …) | |
| `Interlude` | No | Treated as instrumental |
| `Instrumental.` | No | Treated as instrumental |
| `Bridge` | Yes | |
| `Tag` | No | Treated as instrumental |
| `Outro` | No | Treated as instrumental |

**Instrumental sections** only emit chord lines (lyric lines are suppressed unless they differ from the chord line).

`REPEAT *` lines are always stripped during parsing and never appear in `content`.

---

## Chromatic Scale Constants

Used by the transposition engine in `src/utils/search.py` (shared across the registered scrapers):

```python
CHROMATIC_SCALE_SHARPS = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
CHROMATIC_SCALE_FLATS  = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']
```

The flat scale is used when the target key contains `b` (e.g. `Bb`, `Eb`). Enharmonic equivalents (`C#`/`Db`, etc.) are handled via a fallback mapping in `get_note_index()`.
