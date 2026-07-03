"""End-to-end workflow tests: Preview and Edit UI integration.

These tests exercise the full preview-and-edit workflow as a sequence of
endpoint calls against the same song payload, validating that the YAML →
Marp → HTML chain is internally consistent. Per-endpoint behavior is covered
in test_api_preview.py and test_generate_yaml_api.py.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from flask import Flask

from src.routes.api import api_bp


def make_client():
    app = Flask(__name__)
    app.register_blueprint(api_bp, url_prefix="/api")
    return app.test_client()


def _install_fake_renderer(monkeypatch, tag: str) -> None:
    """Replace Marp CLI subprocess so tests stay deterministic and fast."""

    def fake_run(cmd, **kwargs):
        output_path = Path(cmd[cmd.index("-o") + 1])
        markdown = Path(cmd[1]).read_text(encoding="utf-8")
        output_path.write_text(
            f"<html><body><h1>{tag}</h1><pre>{markdown}</pre></body></html>",
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)


def _song_with_single_section() -> dict:
    """A canonical song payload shaped like the SongEditor's POST body."""
    return {
        "title": "Amazing Grace",
        "authors": ["John Newton"],
        "target_key": "G",
        "bpm": 80,
        "time_signature": "3/4",
        "sections": {
            "Verse 1": {
                "name": "Verse 1",
                "lines": [
                    {"chordpro": "[G]Amazing [C]grace, how [G]sweet the sound"},
                    {"chordpro": "That [G]saved a [D]wretch like [G]me"},
                ],
            },
        },
        "arrangement": ["Verse 1"],
    }


def test_workflow_round_trip_yaml_preview_regenerate(monkeypatch):
    """The full pipeline produces consistent results across all three endpoints."""
    _install_fake_renderer(monkeypatch, "Rendered")

    client = make_client()

    # 1. Generate structured YAML from raw metadata + chart
    yaml_response = client.post(
        "/api/generate_yaml",
        json={
            "metadata": {
                "title": "Amazing Grace",
                "authors": ["John Newton"],
                "original_key": "G",
            },
            "chart": {
                "content": "Verse 1\n    G      C\n[G]Amazing [C]grace",
            },
            "target_key": "G",
        },
    )
    assert yaml_response.status_code == 200
    song = yaml_response.get_json()["yaml"]

    # 2. Generate a preview from the structured YAML produced in step 1
    preview_response = client.post(
        "/api/preview",
        json={"song": song, "style": "practice"},
    )
    assert preview_response.status_code == 200
    preview = preview_response.get_json()
    assert preview["slide_count"] == 2  # title slide + one section
    assert preview["warnings"] == []

    # 3. Regenerate the preview from the same YAML and confirm stable output
    regen_response = client.post(
        "/api/regenerate",
        json={"song": song, "style": "practice"},
    )
    assert regen_response.status_code == 200
    regen = regen_response.get_json()

    # The slide structure must match between preview and regenerate
    assert regen["slide_count"] == preview["slide_count"]
    assert regen["marp_markdown"] == preview["marp_markdown"]
    assert regen["html_content"] == preview["html_content"]
    assert regen["validation"]["valid"] is True


def test_edit_chord_then_regenerate_reflects_change(monkeypatch):
    """Editing a chord in the editor payload must propagate to regenerated HTML."""
    _install_fake_renderer(monkeypatch, "Regenerated")

    client = make_client()
    base_payload = _song_with_single_section()

    # Original regenerate uses the C major chord on the first line
    initial = client.post(
        "/api/regenerate", json={"song": base_payload, "style": "practice"}
    ).get_json()
    assert '<span class="chord">G       C          G</span>' in initial["marp_markdown"]
    assert initial["slide_count"] == 2  # title + Verse 1

    # Simulate the editor changing C→D on the first line
    edited = {
        **base_payload,
        "sections": {
            "Verse 1": {
                "name": "Verse 1",
                "lines": [
                    {"chordpro": "[G]Amazing [D]grace, how [G]sweet the sound"},
                    {"chordpro": "That [G]saved a [D]wretch like [G]me"},
                ],
            },
        },
    }
    updated = client.post(
        "/api/regenerate", json={"song": edited, "style": "practice"}
    ).get_json()

    # The C→D edit must remove the C chord row and add D at the expected column.
    assert (
        '<span class="chord">G       C          G</span>'
        not in updated["marp_markdown"]
    )
    assert '<span class="chord">G       D          G</span>' in updated["marp_markdown"]
    # Chord-only edits must not change slide count
    assert updated["slide_count"] == initial["slide_count"]


def test_show_song_map_option_controls_song_map_rendering(monkeypatch):
    """Toggling the show_song_map option must add or remove the title-slide song-map marker."""
    _install_fake_renderer(monkeypatch, "Rendered")

    client = make_client()
    song = _song_with_single_section()

    with_map = client.post(
        "/api/preview",
        json={"song": song, "style": "practice", "options": {"show_song_map": True}},
    ).get_json()

    without_map = client.post(
        "/api/preview",
        json={"song": song, "style": "practice", "options": {"show_song_map": False}},
    ).get_json()

    # The two renders must differ when the option changes
    assert with_map["marp_markdown"] != without_map["marp_markdown"]
    # Title-slide song-map marker only appears when the option is enabled
    assert "**Song map:**" in with_map["marp_markdown"]
    assert "**Song map:**" not in without_map["marp_markdown"]


def test_warnings_are_consistent_across_preview_and_regenerate(monkeypatch):
    """An arrangement drift warning must surface in BOTH preview and regenerate."""
    _install_fake_renderer(monkeypatch, "Rendered")

    client = make_client()
    song = _song_with_single_section()
    song["arrangement"] = ["Verse 1", "Bridge"]

    expected_warning = ["Arrangement references missing section: Bridge"]

    preview = client.post(
        "/api/preview", json={"song": song, "style": "practice"}
    ).get_json()
    regen = client.post(
        "/api/regenerate", json={"song": song, "style": "practice"}
    ).get_json()

    # Warnings propagate to both endpoints because both surface _preview_warnings
    assert preview["warnings"] == expected_warning
    assert regen["warnings"] == expected_warning
    # Schema remains valid here because the song structure is correct; only the
    # arrangement references a missing section, which is a preview warning, not
    # a schema violation.
    assert regen["validation"]["valid"] is True


def test_song_editor_payload_shape_renders_full_preview(monkeypatch):
    """The exact POST body shape from song_editor.js must round-trip end-to-end."""
    _install_fake_renderer(monkeypatch, "Rendered")

    client = make_client()

    # This mirrors SongEditor.regeneratePreview() in src/static/js/song_editor.js
    response = client.post(
        "/api/regenerate",
        json={
            "song": _song_with_single_section(),
            "style": "practice",
            "options": {
                "show_metadata": True,
                "show_song_map": True,
                "show_practice_notes": True,
                "font_size": "28px",
                "aspect_ratio": "16:9",
            },
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["html_content"].startswith("<html>")
    assert payload["marp_markdown"].startswith("---\nmarp: true")
    assert payload["slide_count"] == 2  # title + Verse 1
    assert payload["warnings"] == []
    assert payload["validation"]["valid"] is True
