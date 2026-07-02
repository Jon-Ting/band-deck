# 📋 Architecture Decision Records

This file tracks significant design decisions made during development of Band-Deck. Each entry explains the **context**, the **decision**, and the **rationale**. This helps future contributors (and LLMs) understand *why* the code is the way it is.

---

## ADR-001 — Use Worship Together as the sole song source

**Date**: Initial development  
**Status**: Active

### Context
Band-Deck needs a reliable source for songs with both lyrics and chords in a machine-parseable format. Most chord/lyric sites use inconsistent HTML or require accounts.

### Decision
Scrape [Worship Together](https://www.worshiptogether.com/) exclusively, parsing its `chord-pro-line` / `chord-pro-segment` HTML structure.

### Rationale
- WT uses a consistent, well-structured HTML chord-pro format that maps cleanly to aligned chord+lyric pairs.
- It includes a `<meta property="cludo:originalKey">` tag, enabling key detection without manual parsing.
- The target audience (worship musicians) overlaps heavily with WT's song catalogue.

### Trade-offs
- Limited to songs available on WT; popular secular/rock songs are absent.
- WT may change its HTML structure without notice, breaking the scraper.

---

## ADR-002 — Adaptive column layout instead of fixed layout

**Date**: Early development  
**Status**: Active

### Context
Songs vary enormously in length — a 2-verse song and a 6-section song with a bridge and tag need very different layouts to be readable on a projector.

### Decision
Dynamically determine column count (2–4) and font size (4–10pt) by iterating combinations until content fits within the slide bounds.

### Rationale
- A fixed layout would either waste space for short songs or overflow for long ones.
- Musicians project slides in real-time; overflow is not acceptable.
- The iteration approach is simple and deterministic (no ML, no heuristics beyond the grid math).

### Trade-offs
- Very long songs may still be unreadably small at 4pt / 4 columns. This is a hard limit of the approach.
- Section distribution is naive (even split by count, not by line density), so columns can be uneven.

---

## ADR-003 — Use `search_name` (user input) as the slide title and filename

**Date**: Early development  
**Status**: Active

### Context
The scraped `<h1>` title often differs from what users search for. For example, searching "10000 Reasons" returns a page titled "10,000 Reasons (Bless the Lord)".

### Decision
Store and display the user's original search string as `search_name`, preferring it over `title` for slide headings and filenames.

### Rationale
- Musicians search by the name they know. The slide should match their expectation.
- Snake-cased `search_name` makes filenames predictable (e.g. `10000_reasons.pptx`).

### Trade-offs
- If a user misspells the song name, the slide title will also be misspelled.

---

## ADR-004 — File-based storage with UUID filenames

**Date**: Initial development  
**Status**: Active

### Context
Band-Deck is a personal tool. Adding a database would increase operational complexity with no real benefit at this scale.

### Decision
Store each saved slide as a UUID-named pair: `<uuid>.pptx` + `<uuid>.json`. List slides by scanning for `.json` files.

### Rationale
- Zero infrastructure — no database server, no migrations.
- UUIDs avoid filename collisions even for songs with the same name.
- The JSON sidecar keeps metadata queryable without opening binary PPTX files.

### Trade-offs
- Not suitable for concurrent multi-user deployments (no locking, no transactions).
- Listing slides requires a directory scan, which is O(n) and has no indexing.
- If a `.pptx` is deleted without its `.json` (or vice versa), the pair is orphaned.

---

## ADR-005 — Monospace font (Consolas) for chord+lyric alignment

**Date**: Early development  
**Status**: Active

### Context
Chords must appear directly above the syllable they apply to. This alignment is encoded via space-padding in the `content` string.

### Decision
Use Consolas (a monospace font) for all slide content.

### Rationale
- With a proportional font, space-padded alignment breaks because characters have different widths.
- Consolas is available on all major platforms (Windows, macOS, Linux) and is embedded in the PPTX.

### Trade-offs
- Monospace fonts are less aesthetically pleasing than proportional fonts.
- No fallback if Consolas is unavailable on an unusual system.

---

## ADR-006 — In-memory rate limiting

**Date**: Initial development  
**Status**: Active (with known limitations)

### Context
Band-Deck's `/api/` endpoints scrape an external site. Unbounded scraping risks being blocked or causing harm to the source site.

### Decision
Implement a simple per-IP timestamp dictionary in `api.py` (5-second window → ~10 req/min).

### Rationale
- Simple to implement and reason about for a single-process personal server.
- No external dependencies (no Redis, no Flask-Limiter).

### Trade-offs
- State is lost on restart.
- Does not scale across multiple worker processes.
- Recommendation: replace with `Flask-Limiter` + Redis if ever deployed publicly.

---

## ADR-007 — Vanilla JS frontend (no framework, no build step)

**Date**: Initial development  
**Status**: Active

### Context
The frontend is a single-page UI for searching, previewing, and managing slides.

### Decision
Use plain HTML, CSS, and JavaScript served directly by Flask's `static` folder. No npm, no bundler.

### Rationale
- Zero build tooling to maintain or break.
- The UI is simple enough that a framework adds no real value.
- Python developers maintaining this project don't need to manage a JS ecosystem.

### Trade-offs
- No hot module reload during development.
- Refactoring the JS is harder without module bundling for large feature additions.
