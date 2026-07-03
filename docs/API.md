# 🔌 Band-Deck API Reference

All endpoints are registered under the `/api/` prefix and are rate-limited to approximately **10 requests/minute per IP** (one request per 5 seconds).

---

## Endpoints

### `GET /api/search`

Search for a song and return structured lyrics/chords + a preview payload.

**Query Parameters**

| Parameter | Required | Description |
|-----------|----------|-------------|
| `song` | ✅ | Song name (e.g. `Amazing Grace`) |
| `artist` | ❌ | Artist name (improves URL matching, e.g. `Bethel`) |
| `key` | ❌ | Target key for transposition (e.g. `G`, `F#`, `Bb`) |

**Example**
```bash
curl "http://localhost:5000/api/search?song=Amazing%20Grace&artist=Traditional&key=G"
```

**Success Response** `200 OK`
```json
{
  "title": "Amazing Grace",
  "search_name": "Amazing Grace",
  "artist": "Traditional",
  "content": "Verse 1\nG          Em\nI love You Lord\n...",
  "source_url": "https://example.com/songs/amazing-grace-traditional/",
  "original_key": "A",
  "key": "G"
}
```

**Error Responses**

| Status | Body | Cause |
|--------|------|-------|
| `400` | `{"error": "Song name is required"}` | Missing `song` param |
| `404` | `{"error": "Song not found"}` | Scrape returned no result |

---

### `POST /api/save_slide`

Save a song in the requested formats (YAML, Marp markdown, HTML, and optionally PDF) plus a JSON metadata sidecar.

**Request Body** — JSON (same shape as the `search` response, without `pptx_preview`):
```json
{
  "title": "Amazing Grace",
  "search_name": "Amazing Grace",
  "artist": "Traditional",
  "content": "...",
  "original_key": "A",
  "key": "G"
}
```

**Success Response** `200 OK`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Amazing Grace",
  "artist": "Traditional",
  "key": "G",
  "filename": "550e8400-e29b-41d4-a716-446655440000.pptx"
}
```

**Error Responses**

| Status | Body | Cause |
|--------|------|-------|
| `400` | `{"error": "No song data provided"}` | Empty or missing JSON body |

---

### `GET /api/saved_slides`

List all slides currently in the library.

**Example**
```bash
curl "http://localhost:5000/api/saved_slides"
```

**Success Response** `200 OK`
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "Amazing Grace",
    "artist": "Traditional",
    "key": "G",
    "filename": "550e8400-e29b-41d4-a716-446655440000.pptx"
  }
]
```

Returns an empty array `[]` if no slides are saved.

---

### `GET /api/saved_slide/<slide_id>`

**Stub for the retired unversioned download endpoint.** Returns 404 with an explanatory message pointing callers to the per-format download route (`/api/saved_slide/<id>/download/<format>`).

The original route defaulted to PowerPoint; PowerPoint export is now retired, so the stub is the live behaviour of this URL.

---

### `DELETE /api/saved_slide/<slide_id>`

Delete a saved slide (removes both the `.pptx` and `.json` sidecar).

**Example**
```bash
curl -X DELETE "http://localhost:5000/api/saved_slide/550e8400-e29b-41d4-a716-446655440000"
```

**Success Response** `200 OK`
```json
{ "success": true }
```

**Error Responses**

| Status | Body | Cause |
|--------|------|-------|
| `404` | `{"error": "Slide not found"}` | Unknown `slide_id` |

---

### `GET /api/compile_slides`

**Removed.** This endpoint used to compile all saved slides into a single `.pptx` with a clickable index slide; PowerPoint export has been retired. The replacement is `POST /api/compile`, which assembles a single HTML deck with a clickable index for the supplied list of slide IDs.

---

### `POST /api/clear_temp_files`

Delete every file in `data/saved_slides/` that is not part of the saved-slide artefact set (i.e. anything other than `.yaml`, `.marp.md`, `.html`, `.json`, and any opt-in `.pdf`). This is safe to run at any time; it will never delete a saved slide or a compiled deck.

**Example**
```bash
curl -X POST "http://localhost:5000/api/clear_temp_files"
```

**Success Response** `200 OK`
```json
{ "success": true, "message": "Temporary files cleared." }
```

---

## Content Format

The `content` field returned by `/api/search` is a plain-text string with sections separated by `\n\n`. Each section starts with a header line, followed by alternating chord and lyric lines:

```
Verse 1
G          Em         C          D
I love You Lord       Oh I see Your goodness

Chorus
G    D    Em   C
All my life You have been faithful
```

Chord lines and lyric lines are space-aligned so chords appear directly above the corresponding syllables.
