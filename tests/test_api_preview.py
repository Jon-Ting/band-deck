"""Tests for the HTML preview API endpoint."""

from __future__ import annotations

import subprocess
from pathlib import Path

from flask import Flask

from src.routes.api import api_bp


def make_client():
    app = Flask(__name__)
    app.register_blueprint(api_bp, url_prefix="/api")
    return app.test_client()


def make_song_payload() -> dict:
    return {
        "title": "Example Song",
        "authors": ["Example Writer"],
        "target_key": "D",
        "sections": {
            "Verse 1": {
                "name": "Verse 1",
                "type": "verse",
                "lines": [
                    {
                        "text": "Placeholder lyric",
                        "chords": [{"chord": "D", "position": 0}],
                    }
                ],
            },
            "Chorus": {
                "name": "Chorus",
                "type": "chorus",
                "lines": [
                    {
                        "text": "Lift the hook",
                        "chords": [{"chord": "G", "position": 0}],
                    }
                ],
            },
        },
        "arrangement": ["Verse 1", "Chorus"],
        "practice_notes": {"general": ["Watch the transition"]},
    }


def test_preview_endpoint_returns_rendered_html_warnings_and_slide_count(monkeypatch):
    def fake_run(cmd, **kwargs):
        output_path = Path(cmd[cmd.index("-o") + 1])
        markdown = Path(cmd[1]).read_text(encoding="utf-8")
        output_path.write_text(
            f"<html><body><h1>Rendered</h1><pre>{markdown}</pre></body></html>",
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    response = make_client().post(
        "/api/preview",
        json={"song": make_song_payload(), "style": "practice"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["html_content"].startswith("<html>")
    assert "# Example Song" in payload["marp_markdown"]
    assert "## Verse 1" in payload["marp_markdown"]
    assert payload["warnings"] == []
    assert payload["slide_count"] == 3


def test_preview_endpoint_warns_about_missing_arrangement_sections(monkeypatch):
    def fake_run(cmd, **kwargs):
        output_path = Path(cmd[cmd.index("-o") + 1])
        output_path.write_text("<html><body>Rendered</body></html>", encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    song = make_song_payload()
    song["arrangement"].append("Bridge")

    response = make_client().post(
        "/api/preview",
        json={"song": song, "style": "practice"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["slide_count"] == 3
    assert payload["warnings"] == ["Arrangement references missing section: Bridge"]


def test_preview_endpoint_rejects_missing_song_payload():
    response = make_client().post("/api/preview", json={"style": "practice"})

    assert response.status_code == 400
    assert response.get_json()["error"] == "Song data is required"


def test_regenerate_endpoint_returns_updated_html_warnings_and_slide_count(monkeypatch):
    def fake_run(cmd, **kwargs):
        output_path = Path(cmd[cmd.index("-o") + 1])
        markdown = Path(cmd[1]).read_text(encoding="utf-8")
        output_path.write_text(
            f"<html><body><h1>Regenerated</h1><pre>{markdown}</pre></body></html>",
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    edited_song = make_song_payload()
    edited_song["title"] = "Edited Example Song"
    edited_song["sections"]["Chorus"]["lines"][0]["text"] = "Edited hook"

    response = make_client().post(
        "/api/regenerate",
        json={"song": edited_song, "style": "practice"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["html_content"].startswith("<html>")
    assert "# Edited Example Song" in payload["marp_markdown"]
    assert "Edited hook" in payload["marp_markdown"]
    assert payload["warnings"] == []
    assert payload["slide_count"] == 3


def test_regenerate_endpoint_rejects_invalid_modified_yaml():
    response = make_client().post(
        "/api/regenerate",
        json={"song": {"title": "Missing Sections", "authors": ["Example Writer"]}},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "Song sections are required"


def test_regenerate_endpoint_rejects_schema_invalid_modified_yaml(monkeypatch):
    def fail_if_rendered(cmd, **kwargs):
        raise AssertionError("Invalid song YAML should not be rendered")

    monkeypatch.setattr(subprocess, "run", fail_if_rendered)
    song = make_song_payload()
    song["target_key"] = "H"

    response = make_client().post(
        "/api/regenerate",
        json={"song": song, "style": "practice"},
    )

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["error"] == "Invalid song YAML"
    assert payload["validation"]["valid"] is False
    assert any("target_key" in error["path"] for error in payload["validation"]["errors"])
