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
    assert result["yaml"]["ccli_number"] == "1234567"
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
