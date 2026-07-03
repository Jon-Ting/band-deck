# Band-Deck - User Guide

## Application Overview

Band-Deck is a web application that lets you quickly build musician-friendly slides with lyrics and chord notations. The application uses pluggable chord/lyric scrapers and pulls lyrics and chords from any number of public chord/lyric sites on the internet. It turns the raw chart into a typed `SongYAML`, then renders it as a Marp markdown deck and an HTML slide preview. You edit the YAML live in the browser, save the slide as one or more formats (YAML, Marp markdown, HTML, optional PDF), redownload any saved format later, and combine saved slides into a single HTML deck for projection during services, concerts, rehearsals, or lessons.

## Features

- **Simple Search Interface**: Enter a song name and optionally an artist to find your desired song
- **Live HTML Preview**: Render the Marp-backed HTML deck in an embedded iframe so chords, sections, and overflow look right before you commit
- **YAML-Based Editing**: Tweak metadata, target key, BPM, time signature, section arrangement, and practice notes in the YAML editor pane; the preview auto-regenerates after a short debounce and `/api/validate` surfaces structural errors, slide-overflow warnings, and licensing notices inline
- **Multi-format Save & Download**: Save slides as YAML source, Marp markdown, and rendered HTML; all three formats stay available for re-download after editing. PDF is part of the format contract and will be honoured by future renderer output, but the standard `save_slide` path currently does not emit a `.pdf` artefact.
- **Slide Library**: List, re-download, update, or delete any saved slide from the **Saved Slides** panel without re-searching
- **Batch Compilation**: Combine multiple saved slides into a single HTML deck with a clickable index page that the whole band can scroll through
- **Cleanup**: One-click removal of orphan / scratch files under `data/saved_slides/` via the **Cleanup Temporary Files** action (handy when the renderer leaves stray outputs behind)
- **Error Handling**: Clear feedback when a song cannot be found, the Marp CLI is missing, validation fails, or the slide-storage layer refuses an I/O operation

## How to Use

1. **Access the Application**: Run the Flask app locally per the docs (see [README → Installation](../README.md)) and open **http://localhost:5000** in your browser.

2. **Search for a Song**:
   - Enter the song name in the "Song Name" field
   - Optionally enter the artist name for more accurate results
   - Click "Generate Slide"

3. **Preview & Edit**:
   - Once found, the song appears in the live HTML preview pane (orbit-style navigation: `→` / `Space` / `PageDown` for next, `←` / `PageUp` for previous)
   - Switch the slide style between `practice` (chords above lyrics), `performance` (lyrics only), or `simple` from the style picker
   - Edit metadata, target key, BPM, time signature, section arrangement, or practice notes directly in the YAML editor — the preview re-renders after a 500 ms debounce, and `/api/validate` flags any structural issues (overflow, missing fields, licensing markers) inline

4. **Save the Slide**:
   - Click **Save Slide** to persist the current YAML/Marp/HTML artefacts to `data/saved_slides/`
   - The save response carries the slide UUID and the `filenames` map so you can see exactly which formats landed on disk

5. **Download a Specific Format**:
   - From the **Saved Slides** panel pick the slide and choose a format:
     - `HTML` — the rendered Marp-backed deck (open in any modern browser, no network required)
     - `Marp` — the underlying Marp markdown (re-render with the Marp CLI on another machine)
     - `YAML` — the structured song definition (round-trippable through `/api/preview` and `/api/regenerate`)
     - `PDF` — `pdf` is accepted by `/api/saved_slide/<id>/download/pdf` so the route stays stable, but the standard save path does not write a `.pdf` artefact today, so a download will return `404 Format pdf not available for this slide` until a PDF-emitting renderer is integrated
   - Each download is a single file attachment served from `GET /api/saved_slide/<id>/download/<format>`

6. **Batch Compile Multiple Songs**:
   - Tick the slides you want in the **Saved Slides** panel
   - Click **Compile Selected** — the app posts to `/api/compile` and returns a single `Compiled_Slide_Deck.html` with a clickable index page at the front and one anchor per slide
   - Open the compiled deck in any browser and use it during a full set without switching tabs

7. **Start a New Search**:
   - Type a new song name into the **Song Name** field and click "Generate Slide" to search for another song

## Data Sources

Band-Deck is built around pluggable chord/lyric scrapers — lyrics and chords are pulled from public sites on the internet, one site at a time. The current build ships with one default scraper wired directly into `/api/search`; new sources register alongside it in `src/utils/search.py`.

## Legal Considerations

This tool is intended for **personal study, educational, and live-performance use only**. All content is retrieved from public sources and should be consumed in compliance with applicable copyright laws.

By using this application you acknowledge that:

- Generated slides may be subject to copyright. You are responsible for ensuring appropriate licensing (e.g. **CCLI** for worship use, or **ASCAP / BMI / SESAC** for general public performance) before projection or distribution.
- Acceptable use includes (but is not limited to) worship services, concerts, rehearsals, and lessons.
- Rate limiting is currently disabled; avoid bulk scraping and follow source-site terms.
- This project ships with template/sample songs only — please verify each song's licensing status for your jurisdiction and use case.
- The maintainers do not endorse redistribution of copyrighted lyrics or chord charts outside the bounds of fair use.

## Printing & Projection

The downloaded artefacts can be opened directly in any modern browser (HTML), re-rendered through the Marp CLI (Marp markdown), or re-imported into `/api/preview` (YAML). From there you can:

1. **Project from the browser**: open the downloaded `.html` deck — Marp's `<script>` disables arrow-key scrolling on the page so it cycles slides cleanly. Use `F` for fullscreen, `P` for presenter mode, and `→` / `Space` / `PageDown` / `←` / `PageUp` to navigate
2. **Print to paper**: open the HTML in your browser and print to PDF (`Ctrl/Cmd-P` → "Save as PDF") or send directly to a printer — use **landscape** orientation and **Fit to page** for best results
3. **Re-render on another machine**: take the `.marp.md` file and run `marp --html <file>.marp.md -o <file>.html` with any Marp CLI 3.x install
4. **Project directly from the application** during services, concerts, rehearsals, or lessons — `http://localhost:5000` keeps the live preview in sync with your edits

## Troubleshooting

- **Song Not Found**: Try checking the spelling or searching with just the song name without the artist
- **Download Issues**: Ensure your browser allows downloads from the application
- **Display Problems**: If the preview appears incorrect, try a different song or open an issue on the project repository

## Technical Information

- The application is built using Flask (Python) on the backend and vanilla HTML / CSS / JavaScript on the frontend — no build step, no framework
- The `SongYAML → Marp markdown → HTML` pipeline lives in `src/utils/marp_generator.py` and `src/utils/html_renderer.py`; the Marp CLI must be installed for HTML rendering (the app reports `status: degraded` on `/api/health` if it isn't, and falls back to a static HTML placeholder so the slide stays loadable)
- Saved slides live under `data/saved_slides/` as `<uuid>.yaml` + `<uuid>.marp.md` + `<uuid>.html` + `<uuid>.json` artefacts (PDF where emitted); `clear_temp_files()` removes everything that isn't in that set
- Rate limiting is currently **disabled** at the application layer (see the Development Notes in `README.md` for production deployment guidance and recommended external throttles)

---

Thank you for using Band-Deck!
