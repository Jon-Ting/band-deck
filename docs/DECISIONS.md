# 📋 Architecture Decision Records

This file tracks significant design decisions made during development of Band-Deck. Each entry explains the **context**, the **decision**, and the **rationale**. This helps future contributors (and LLMs) understand *why* the code is the way it is.

---

## ADR-001 — Pluggable multi-source scraping

**Date**: Initial development  
**Status**: Active

### Context
Band-Deck needs reliable sources for songs with both lyrics and chords in a machine-parseable format, across many song genres. Most chord/lyric sites on the internet use inconsistent HTML, require accounts, or both, so the architecture is designed to be extended with additional pluggable scrapers, one at a time, as they become available.

### Decision
Design the scraping layer so the app can pull lyrics and chords from any number of public chord/lyric sites on the internet. Ship one default scraper registered in `src/utils/search.py` and consumed by the `/api/search` route so the rest of the pipeline can be validated end to end. Source registration lives behind a single seam — `src/utils/search.py` itself — so additional scrapers are added at that boundary without disturbing routes, validate, or slide generation.

### Rationale
- A pluggable, multi-source architecture keeps the app usable for as wide a range of songs as possible instead of being locked to a single catalogue; many sources are expected to ship over the app's lifetime.
- The boundary between scraping and the rest of the pipeline (`search_song` returning the same dict shape regardless of source) means new scrapers can be added without touching routes, validate, or slide generation.
- Shipping one default scraper today (rather than building an upfront plugin registry) keeps the seam small until a second source is wired in, which is exactly what motivates a fuller registry.

### Trade-offs
- Today's user-visible song catalogue mirrors whichever scrapers are wired in. Coverage widens as more scrapers ship, without further architectural change.
- Any single source may change its HTML structure without notice, breaking that scraper. The pluggable shape limits the blast radius so only one scraper needs fixing at a time; `src/utils/search.py` keeps fetch, parse, and transposition separable for that reason.
- The default scraper ships with two source-specific helpers — `format_worship_together_url()` and `extract_wt_chordpro_sections()` — whose names carry source-specific scope; deferring a rename or registry refactor until a second source is wired in keeps the change well-motivated.

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
**Status**: Superseded; rate limiting is currently disabled

### Context
Band-Deck's `/api/` endpoints scrape an external site. Unbounded scraping risks being blocked or causing harm to the source site.

### Decision
The previous simple per-IP timestamp dictionary in `api.py` was removed. Band-Deck currently does not enforce application-level request throttling.

### Rationale
- Keeps local rehearsal workflow requests from being blocked by app-level throttling.
- Avoids maintaining a single-process limiter that does not behave correctly under multi-worker deployment.

### Trade-offs
- No app-level protection against bulk requests.
- Recommendation: add `Flask-Limiter` + Redis, or equivalent reverse-proxy throttling, before any public deployment.

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
