# 🗄️ Band-Deck Data Model

## Overview

Band-Deck has no database. All state is stored as files on disk in `src/saved_slides/`. The core data structure is the **Song Data dict**, which flows through the entire pipeline.

---

## Song Data Dict

This is the central in-memory data structure passed between `search.py`, `pptx_generator.py`, `slide_storage.py`, and the API layer.

```python
{
    # Populated by search.py
    "title":        str,          # Song title scraped from the page <h1>
    "search_name":  str,          # User's original search input (shown on slides)
    "artist":       str,          # Artist name (from search input, not scraped)
    "content":      str,          # Sectioned lyrics+chords (see Content Format below)
    "source_url":   str,          # Canonical Worship Together URL
    "original_key": str | None,   # Key detected from page meta tag

    # Added by the API layer (api.py)
    "key":          str | None,   # User-requested target key (post-transposition)

    # Added by api.py /search only (not stored)
    "pptx_preview": {
        "title":    str,
        "artist":   str,
        "key":      str,
        "sections": [
            {"header": str, "content": str},
            ...
        ]
    }
}
```

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

Chords are space-padded so they align directly above the syllable they apply to. This alignment is significant — `pptx_generator.py` uses a monospace font (Consolas) to preserve it.

---

## Slide Metadata JSON (`.json` sidecar)

Each saved slide has a UUID-named JSON sidecar in `src/saved_slides/`.

```python
{
    "id":       str,   # UUID (also the filename stem)
    "title":    str,   # From search_name or title
    "artist":   str,
    "key":      str | None,
    "filename": str    # e.g. "550e8400-e29b-41d4-a716-446655440000.pptx"
}
```

This file is the source of truth for listing and downloading. The `.pptx` file is treated as a binary blob keyed by `id`.

---

## File Storage Layout

```
src/saved_slides/
├── <uuid>.pptx       ← Individual song slide (binary)
├── <uuid>.json       ← Metadata sidecar (text)
├── <uuid>.pptx
├── <uuid>.json
│   ...
└── all_songs.pptx    ← Compiled deck (regenerated on each compile call)
```

**Invariants:**
- Every `.json` file has a matching `.pptx` with the same stem.
- `all_songs.pptx` is always overwritten — it is not tracked in any sidecar.
- `clear_temp_files()` removes everything that is neither `.pptx` nor `.json`.

---

## Section Types

The following section names are recognized and parsed by `search.py`:

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

Used by the transposition engine in `search.py`:

```python
CHROMATIC_SCALE_SHARPS = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
CHROMATIC_SCALE_FLATS  = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']
```

The flat scale is used when the target key contains `b` (e.g. `Bb`, `Eb`). Enharmonic equivalents (`C#`/`Db`, etc.) are handled via a fallback mapping in `get_note_index()`.
