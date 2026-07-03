"""Tests for the YAML generation API endpoint."""

from flask import Flask

from src.routes.api import api_bp


def make_client():
    app = Flask(__name__)
    app.register_blueprint(api_bp, url_prefix="/api")
    return app.test_client()


def test_generate_yaml_converts_metadata_chart_and_target_key():
    client = make_client()

    response = client.post(
        "/api/generate_yaml",
        json={
            "metadata": {
                "title": "Requested Title",
                "authors": ["Writer One", "Writer Two"],
                "ccli_number": "1234567",
                "copyright": "Copyright 2026 Example Publisher",
                "original_key": "G",
                "bpm": 72,
                "time_signature": "4/4",
                "source_urls": ["https://example.test/song"],
            },
            "chart": {
                "content": "Verse 1\n    G      D\nPlaceholder lyric line",
            },
            "target_key": "G",
        },
    )

    assert response.status_code == 200
    result = response.get_json()

    assert result["validation"] == {"valid": True, "errors": []}
    assert result["yaml"]["title"] == "Requested Title"
    assert result["yaml"]["authors"] == ["Writer One", "Writer Two"]
    assert result["yaml"]["license_number"] == "1234567"
    assert result["yaml"]["copyright"] == "Copyright 2026 Example Publisher"
    assert result["yaml"]["original_key"] == "G"
    assert result["yaml"]["target_key"] == "G"
    assert result["yaml"]["bpm"] == 72
    assert result["yaml"]["time_signature"] == "4/4"
    assert result["yaml"]["source_urls"] == ["https://example.test/song"]
    assert result["yaml"]["arrangement"] == ["Verse 1"]
    assert result["yaml"]["sections"]["Verse 1"]["lines"] == [
        {
            "text": "Placeholder lyric line",
            "chords": [
                {"chord": "G", "position": 4},
                {"chord": "D", "position": 11},
            ],
        }
    ]


def test_generate_yaml_returns_validation_errors_for_invalid_song_yaml():
    client = make_client()

    response = client.post(
        "/api/generate_yaml",
        json={
            "metadata": {
                "title": "No Sections",
                "authors": ["Example Writer"],
                "original_key": "G",
            },
            "chart": {"content": ""},
            "target_key": "H",
        },
    )

    assert response.status_code == 200
    result = response.get_json()

    assert result["yaml"]["title"] == "No Sections"
    assert result["validation"]["valid"] is False
    assert any("sections" in error["path"] for error in result["validation"]["errors"])
    assert any("target_key" in error["path"] for error in result["validation"]["errors"])


def test_generate_yaml_requires_json_body():
    client = make_client()

    response = client.post("/api/generate_yaml")

    assert response.status_code == 400
    assert response.get_json() == {"error": "No song data provided"}


def test_generate_yaml_accepts_search_response_key_as_target_key_fallback():
    """Regression: /api/search returns the user-requested key under the
    ``key`` field rather than ``target_key``. /api/generate_yaml must accept
    it directly so the frontend can POST the raw search payload without
    having to forward/rename the field.

    The fixture below mirrors the shape ``search_song`` returns from
    src/utils/search.py (via /api/search in src/routes/api.py) for a song in
    original key A requested in target key G.
    """
    client = make_client()

    response = client.post(
        "/api/generate_yaml",
        json={
            "title": "Requested Title",
            "search_name": "Requested Title",
            "artist": "Writer One",
            "content": "Verse 1\n    G      D\nPlaceholder lyric line",
            "source_url": "https://example.test/song",
            "original_key": "A",
            "key": "G",
        },
    )

    assert response.status_code == 200
    result = response.get_json()

    assert result["validation"] == {"valid": True, "errors": []}
    assert result["yaml"]["title"] == "Requested Title"
    assert result["yaml"]["authors"] == ["Writer One"]
    assert result["yaml"]["original_key"] == "A"
    assert result["yaml"]["target_key"] == "G"
    assert result["yaml"]["source_urls"] == ["https://example.test/song"]
    assert result["yaml"]["arrangement"] == ["Verse 1"]
    assert result["yaml"]["sections"]["Verse 1"]["lines"] == [
        {
            "text": "Placeholder lyric line",
            "chords": [
                {"chord": "G", "position": 4},
                {"chord": "D", "position": 11},
            ],
        }
    ]


def test_generate_yaml_target_key_takes_precedence_over_key():
    """If a caller explicitly sets ``target_key`` (alongside ``key``), the
    explicit value wins — we never want the search-response key to silently
    override an editor-supplied target key."""
    client = make_client()

    response = client.post(
        "/api/generate_yaml",
        json={
            "title": "Both Keys",
            "artist": "Writer One",
            "content": "Verse 1\n    A\nPlaceholder lyric line",
            "original_key": "C",
            "key": "G",          # what /api/search would return
            "target_key": "D",   # what the editor/regenerate flow sends
        },
    )

    assert response.status_code == 200
    result = response.get_json()

    assert result["yaml"]["target_key"] == "D"


def test_generate_yaml_falls_back_to_original_key_when_no_key_or_target_key():
    """When the caller did not pick a key (no ``key`` and no ``target_key``),
    /api/generate_yaml must fall back to ``original_key`` so the preview
    displays in the song's source key instead of silently defaulting to C.
    This is what lets the frontend POST the raw /api/search payload without
    having to forward/rename any key field."""
    client = make_client()

    response = client.post(
        "/api/generate_yaml",
        json={
            "title": "Source Key Only",
            "artist": "Writer One",
            "content": "Verse 1\n    A\nPlaceholder lyric line",
            "original_key": "A",
        },
    )

    assert response.status_code == 200
    result = response.get_json()

    assert result["yaml"]["original_key"] == "A"
    assert result["yaml"]["target_key"] == "A"
