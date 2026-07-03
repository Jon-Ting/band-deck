"""Tests for the HTML compilation utility and the /api/compile endpoint."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

from flask import Flask

import src.utils.slide_storage as storage_module
from src.routes.api import api_bp
from src.utils import compiler as compiler_module
from src.utils.compiler import COMPILED_HTML_FILENAME, compile_slides_html
from src.utils.html_renderer import RenderError
from src.utils.slide_storage import (
    SLIDES_DIR,
    _meta_path,
    _slide_path,
)


def make_client():
    app = Flask(__name__)
    app.register_blueprint(api_bp, url_prefix="/api")
    return app.test_client()


def _save_yaml(slide_id: str, song_payload: dict) -> str:
    """Write a SongYAML-shaped YAML artefact and matching metadata JSON."""
    yaml_path = _slide_path(slide_id, "yaml")
    meta_path = _meta_path(slide_id)
    os.makedirs(os.path.dirname(yaml_path), exist_ok=True)

    import yaml as pyyaml

    with open(yaml_path, "w", encoding="utf-8") as yaml_file:
        pyyaml.safe_dump(song_payload, yaml_file, sort_keys=False, allow_unicode=True)

    meta = {
        "id": slide_id,
        "title": song_payload["title"],
        "artist": song_payload["authors"][0] if song_payload.get("authors") else None,
        "key": song_payload.get("target_key"),
        "filenames": {"yaml": f"{slide_id}.yaml"},
        "created_at": "2024-01-01T00:00:00+00:00",
        "updated_at": "2024-01-01T00:00:00+00:00",
    }
    with open(meta_path, "w", encoding="utf-8") as meta_file:
        json.dump(meta, meta_file)
    return yaml_path


def _install_fake_marp(monkeypatch, body_prefix: str = "Compiled") -> None:
    """Replace Marp CLI subprocess so tests stay deterministic and script-free."""

    def fake_run(cmd, **kwargs):
        output_path = Path(cmd[cmd.index("-o") + 1])
        markdown = Path(cmd[1]).read_text(encoding="utf-8")
        output_path.write_text(
            f"<html><body><h1>{body_prefix}</h1><pre>{markdown}</pre></body></html>",
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr("src.utils.html_renderer.subprocess.run", fake_run)


def _verse_one_song(slide_id: str, title: str = "Amazing Grace") -> dict:
    return {
        "title": title,
        "authors": ["John Newton"],
        "target_key": "G",
        "sections": {
            "Verse 1": {
                "name": "Verse 1",
                "type": "verse",
                "lines": [
                    {
                        "text": "Amazing grace",
                        "chords": [{"chord": "G", "position": 0}],
                    }
                ],
            }
        },
        "arrangement": ["Verse 1"],
    }


class TestCompileSlidesHtml:
    """Isolated tests for ``compiler.compile_slides_html``."""

    def setup_method(self):
        self._original_slides_dir = SLIDES_DIR
        self.test_dir = tempfile.mkdtemp()
        storage_module.SLIDES_DIR = self.test_dir

    def teardown_method(self):
        storage_module.SLIDES_DIR = self._original_slides_dir
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_compiles_ordered_songs_to_single_html(self, monkeypatch):
        _install_fake_marp(monkeypatch)
        _save_yaml("slide-a", _verse_one_song("slide-a", "Amazing Grace"))
        _save_yaml("slide-b", _verse_one_song("slide-b", "How Great Thou Art"))

        output = compile_slides_html(["slide-a", "slide-b"])

        expected_path = os.path.join(self.test_dir, COMPILED_HTML_FILENAME)
        assert output == expected_path
        assert os.path.exists(expected_path)
        html_content = Path(expected_path).read_text(encoding="utf-8")
        # The Marp markdown should embed both songs in the requested order
        assert html_content.index("Amazing Grace") < html_content.index("How Great Thou Art")
        # The index slide should link to both songs in order
        assert "[Amazing Grace](#song-0)" in html_content
        assert "[How Great Thou Art](#song-1)" in html_content
        # Each song gets an anchor div on its first slide
        assert 'id="song-0"' in html_content
        assert 'id="song-1"' in html_content

    def test_raises_when_slide_ids_is_empty(self):
        with patch("src.utils.compiler.list_slides", return_value=[]):
            import pytest as _pytest

            _pytest.raises(compiler_module.CompilationError, compile_slides_html, [])

    def test_skips_unknown_and_unresolved_ids_then_errors(self, monkeypatch):
        _install_fake_marp(monkeypatch)
        # Neither id resolves; the call must fail loudly
        with patch("src.utils.compiler.list_slides", return_value=[]):
            import pytest as _pytest

            with _pytest.raises(compiler_module.CompilationError):
                compile_slides_html(["missing-1", "missing-2"])

    def test_partial_resolution_compiles_only_valid_slides(self, monkeypatch):
        _install_fake_marp(monkeypatch, body_prefix="Partial")
        _save_yaml("slide-keep", _verse_one_song("slide-keep", "Keep Me"))

        output = compile_slides_html(["slide-keep", "missing-1", "slide-keep"])

        assert os.path.exists(output)
        html_content = Path(output).read_text(encoding="utf-8")
        assert "Keep Me" in html_content
        # Repeated ids are deduped so the index and anchors stay unique.
        assert html_content.count("[Keep Me](#song-0)") == 1
        assert html_content.count('id="song-0"') == 1
        assert "song-1" not in html_content

    def test_marp_render_failure_propagates_rendererror(self, monkeypatch):
        _save_yaml("slide-x", _verse_one_song("slide-x", "Slide X"))

        def boom(cmd, **kwargs):
            raise RenderError("simulated CLI failure")

        monkeypatch.setattr("src.utils.html_renderer.subprocess.run", boom)

        import pytest as _pytest

        with _pytest.raises(RenderError):
            compile_slides_html(["slide-x"])

    def test_safety_check_blocks_unsafe_markdown(self, monkeypatch):
        """The compiled deck inherits Marp ``_validate_markdown`` safety rules."""
        _save_yaml("slide-evil", _verse_one_song("slide-evil", "<script>alert(1)</script>"))

        _install_fake_marp(monkeypatch, body_prefix="WouldRender")

        import pytest as _pytest

        with _pytest.raises(ValueError, match="unsafe HTML"):
            compile_slides_html(["slide-evil"])


class TestCompileEndpoint:
    """Tests for the /api/compile POST endpoint."""

    def setup_method(self):
        self._original_slides_dir = SLIDES_DIR
        self.test_dir = tempfile.mkdtemp()
        storage_module.SLIDES_DIR = self.test_dir

    def teardown_method(self):
        storage_module.SLIDES_DIR = self._original_slides_dir
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_post_compile_returns_html_deck(self, monkeypatch):
        _install_fake_marp(monkeypatch)
        _save_yaml("song-x", _verse_one_song("song-x", "Song X"))

        response = make_client().post(
            "/api/compile",
            json={"slide_ids": ["song-x"]},
        )

        assert response.status_code == 200
        assert response.mimetype == "text/html"
        assert b"Song X" in response.data
        assert b'id="song-0"' in response.data

    def test_post_compile_rejects_empty_slide_ids(self):
        response = make_client().post("/api/compile", json={"slide_ids": []})
        assert response.status_code == 400
        assert "non-empty list" in response.get_json()["error"]

    def test_post_compile_rejects_missing_slide_ids_field(self):
        response = make_client().post("/api/compile", json={})
        assert response.status_code == 400

    def test_post_compile_rejects_invalid_order_field(self, monkeypatch):
        _install_fake_marp(monkeypatch)
        _save_yaml("song-a", _verse_one_song("song-a", "Song A"))

        response = make_client().post(
            "/api/compile",
            json={"slide_ids": ["song-a"], "order": ["some-other-id"]},
        )

        assert response.status_code == 400
        assert response.get_json()["error"].startswith("order must list")

    def test_post_compile_returns_400_when_no_slides_resolve(self):
        response = make_client().post(
            "/api/compile",
            json={"slide_ids": ["definitely-missing-1", "definitely-missing-2"]},
        )

        assert response.status_code == 400
        assert "resolved" in response.get_json()["error"]

    def test_post_compile_returns_500_on_marp_render_failure(self, monkeypatch):
        _save_yaml("song-render", _verse_one_song("song-render", "Render Fail"))

        def boom(cmd, **kwargs):
            raise RenderError("simulated CLI failure")

        monkeypatch.setattr("src.utils.html_renderer.subprocess.run", boom)

        response = make_client().post(
            "/api/compile",
            json={"slide_ids": ["song-render"]},
        )

        assert response.status_code == 500
        assert response.get_json()["error"] == "Failed to render compiled deck"
