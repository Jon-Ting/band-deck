"""Tests for saved slide update endpoint."""

import os
import shutil
import tempfile

import pytest

from src.utils.slide_storage import save_slide, update_slide, SLIDES_DIR


SAMPLE_SONG_DATA = {
    "title": "Original Song",
    "search_name": "Original Song",
    "artist": "Original Artist",
    "key": "C",
    "content": """Verse 1
C       G       Am      F
This is a test song lyric
C       G       F       C
With some chords above it

Chorus
F       C       G       Am
Test chorus goes here
F       C       G       C
Ending of the chorus""",
    "bpm": 120,
    "time_signature": "4/4",
    "ccli_number": "1234567",
}


@pytest.fixture
def saved_slide():
    """Create a saved slide and return its metadata."""
    meta = save_slide(SAMPLE_SONG_DATA, formats=["yaml", "marp", "html"])
    yield meta
    # Cleanup after test
    from src.utils.slide_storage import delete_slide
    delete_slide(meta["id"])


def _modified_song_payload() -> dict:
    return {
        "title": "Updated Song Title",
        "authors": ["Updated Artist", "Co-Writer"],
        "target_key": "D",
        "sections": {
            "Verse 1": {
                "name": "Verse 1",
                "type": "verse",
                "lines": [
                    {"chordpro": "[D]This is [A]updated [Bm]lyrics [G]"}
                ]
            },
            "Chorus": {
                "name": "Chorus",
                "type": "chorus",
                "lines": [
                    {"chordpro": "[G]Updated [D]chorus [A]here [D]"}
                ]
            }
        },
        "arrangement": ["Verse 1", "Chorus"],
        "bpm": 140,
        "time_signature": "3/4",
        "ccli_number": "7654321",
    }


def test_update_slide_basic(saved_slide):
    """Test basic slide update with modified song data."""
    slide_id = saved_slide["id"]

    modified_song = _modified_song_payload()

    request_data = {
        "song": modified_song,
        "formats": ["yaml", "marp", "html"]
    }

    # Update the slide
    updated_meta = update_slide(slide_id, request_data)

    # Verify metadata was updated
    assert updated_meta["id"] == slide_id
    assert updated_meta["title"] == "Updated Song Title"
    assert updated_meta["artist"] == "Updated Artist, Co-Writer"
    assert updated_meta["key"] == "D"
    assert updated_meta["bpm"] == 140
    assert updated_meta["time_signature"] == "3/4"
    assert updated_meta["ccli_number"] == "7654321"
    assert updated_meta["created_at"] == saved_slide["created_at"]  # Preserved
    assert updated_meta["updated_at"] != saved_slide["updated_at"]  # Changed

    # Verify all formats were regenerated and PPTX is gone
    assert set(updated_meta["filenames"].keys()) == {"yaml", "marp", "html"}
    assert "pptx" not in updated_meta["filenames"]

    # Verify files exist
    for format in ["yaml", "marp", "html"]:
        file_path = os.path.join(SLIDES_DIR, updated_meta["filenames"][format])
        assert os.path.exists(file_path), f"{format} file should exist"


def test_update_slide_partial_formats(saved_slide):
    """Test updating only specific formats."""
    slide_id = saved_slide["id"]

    modified_song = {
        "title": "Partially Updated",
        "authors": ["Test Artist"],
        "target_key": "C",
        "sections": {
            "Verse 1": {
                "name": "Verse 1",
                "type": "verse",
                "lines": [{"chordpro": "[C]Test"}]
            }
        },
        "arrangement": ["Verse 1"],
    }

    request_data = {
        "song": modified_song,
        "formats": ["yaml", "marp"]  # Only regenerate these
    }

    updated_meta = update_slide(slide_id, request_data)

    # Verify only requested formats are in metadata
    assert set(updated_meta["filenames"].keys()) == {"yaml", "marp"}


def test_update_slide_default_formats(saved_slide):
    """Test updating with default formats (use existing formats)."""
    slide_id = saved_slide["id"]
    original_formats = set(saved_slide["filenames"].keys())

    modified_song = {
        "title": "Default Formats",
        "authors": ["Test Artist"],
        "target_key": "C",
        "sections": {
            "Verse 1": {
                "name": "Verse 1",
                "type": "verse",
                "lines": [{"chordpro": "[C]Test"}]
            }
        },
        "arrangement": ["Verse 1"],
    }

    request_data = {
        "song": modified_song,
        # No formats specified - should use existing formats
    }

    updated_meta = update_slide(slide_id, request_data)

    # Verify same formats as original
    assert set(updated_meta["filenames"].keys()) == original_formats


def test_update_slide_not_found():
    """Test updating a non-existent slide."""
    fake_id = "00000000-0000-0000-0000-000000000000"

    request_data = {
        "song": {
            "title": "Test",
            "authors": ["Test"],
            "target_key": "C",
            "sections": {"V1": {"name": "V1", "type": "verse", "lines": []}},
            "arrangement": ["V1"],
        }
    }

    with pytest.raises(FileNotFoundError):
        update_slide(fake_id, request_data)


def test_update_slide_missing_song_data(saved_slide):
    """Test updating without providing song data."""
    slide_id = saved_slide["id"]

    request_data = {}  # Missing 'song' key

    with pytest.raises(ValueError, match="Song data is required"):
        update_slide(slide_id, request_data)


def test_update_slide_invalid_song_data(saved_slide):
    """Test updating with invalid song data."""
    slide_id = saved_slide["id"]

    request_data = {
        "song": {
            # Missing required fields
            "sections": {},
            "arrangement": []
        }
    }

    with pytest.raises(ValueError, match="Invalid song data"):
        update_slide(slide_id, request_data)


def test_update_slide_invalid_formats(saved_slide):
    """Test updating with invalid format list (legacy pptx token rejected)."""
    slide_id = saved_slide["id"]

    modified_song = {
        "title": "Test",
        "authors": ["Test"],
        "target_key": "C",
        "sections": {
            "Verse 1": {
                "name": "Verse 1",
                "type": "verse",
                "lines": [{"chordpro": "[C]Test"}]
            }
        },
        "arrangement": ["Verse 1"],
    }

    request_data = {
        "song": modified_song,
        "formats": ["yaml", "invalid_format", "pptx"]
    }

    with pytest.raises(ValueError, match="Invalid formats"):
        update_slide(slide_id, request_data)


# ---------------------------------------------------------------------------
# PUT /api/saved_slide/{id} endpoint contract
# ---------------------------------------------------------------------------


class TestUpdateSlideEndpoint:
    """Endpoint-level tests for /api/saved_slide/<slide_id> PUT."""

    def setup_method(self):
        """Redirect SLIDES_DIR to a temp dir so each test is isolated."""
        from src.utils import slide_storage

        self.temp_dir = tempfile.mkdtemp(prefix="update-slide-ep-")
        self.original_slides_dir = slide_storage.SLIDES_DIR
        slide_storage.SLIDES_DIR = self.temp_dir

    def teardown_method(self):
        """Restore the production SLIDES_DIR."""
        from src.utils import slide_storage

        shutil.rmtree(self.temp_dir, ignore_errors=True)
        slide_storage.SLIDES_DIR = self.original_slides_dir

    def _make_client(self):
        """Build a Flask test_client wired to api_bp."""
        from flask import Flask

        from src.routes.api import api_bp

        app = Flask(__name__)
        app.register_blueprint(api_bp, url_prefix="/api")
        return app.test_client()

    def _seed_slide(self, song_data: dict, formats: list[str]) -> dict:
        """Helper: persist a slide directly through save_slide()."""
        return save_slide(song_data, formats=formats)

    def test_put_endpoint_returns_200_and_updated_metadata(self):
        """Happy path: PUT returns updated metadata with new title and timestamps."""
        meta = self._seed_slide(
            {
                "search_name": "Original Song",
                "title": "Original Song",
                "artist": "Original Artist",
                "key": "C",
            },
            formats=["yaml"],
        )

        client = self._make_client()
        response = client.put(
            f"/api/saved_slide/{meta['id']}",
            json={
                "song": _modified_song_payload(),
                "formats": ["yaml"],
            },
        )

        assert response.status_code == 200
        body = response.get_json()
        assert body["id"] == meta["id"]
        assert body["title"] == "Updated Song Title"
        assert body["key"] == "D"
        assert body["bpm"] == 140
        assert body["ccli_number"] == "7654321"
        # created_at is preserved; updated_at advances
        assert body["created_at"] == meta["created_at"]
        assert body["updated_at"] != meta["updated_at"]
        # yaml was regenerated
        assert "yaml" in body["filenames"]
        assert "pptx" not in body["filenames"]
        assert os.path.exists(
            os.path.join(self.temp_dir, body["filenames"]["yaml"])
        )

    def test_put_endpoint_rejects_legacy_pptx_token(self):
        """PUT must reject the legacy pptx token once PPTX export is gone."""
        meta = self._seed_slide(
            {"search_name": "Stub", "title": "Stub", "artist": "Stub"},
            formats=["yaml"],
        )

        client = self._make_client()
        response = client.put(
            f"/api/saved_slide/{meta['id']}",
            json={
                "song": _modified_song_payload(),
                "formats": ["yaml", "pptx"],
            },
        )

        assert response.status_code == 400
        assert "Invalid formats" in response.get_json()["error"]

    def test_put_endpoint_regenerates_requested_formats(self, monkeypatch):
        """When formats=['yaml','marp','html'], all three files regenerate.

        update_slide() does ``from src.utils.html_renderer import render_html``
        inside the function body, so the Marp CLI call must be patched on the
        source module (``src.utils.html_renderer``) — patching
        ``src.utils.slide_storage.render_html`` would set a module attribute
        that update_slide() never reads.
        """
        def stub_render_html(markdown, output_path=None, timeout=30):
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("<html><body>stub</body></html>")
            return output_path

        monkeypatch.setattr(
            "src.utils.html_renderer.render_html", stub_render_html
        )

        meta = self._seed_slide(
            {"search_name": "Stub", "title": "Stub", "artist": "Stub"},
            formats=["yaml"],
        )

        client = self._make_client()
        response = client.put(
            f"/api/saved_slide/{meta['id']}",
            json={
                "song": _modified_song_payload(),
                "formats": ["yaml", "marp", "html"],
            },
        )

        assert response.status_code == 200
        body = response.get_json()
        assert set(body["filenames"].keys()) == {"yaml", "marp", "html"}
        assert "pptx" not in body["filenames"]
        for fmt in ("yaml", "marp", "html"):
            assert os.path.exists(
                os.path.join(self.temp_dir, body["filenames"][fmt])
            ), f"missing {fmt} file"

    def test_put_endpoint_defaults_to_existing_formats_when_omitted(self):
        """Omitting formats regenerates the formats the slide already had."""
        meta = self._seed_slide(
            {"search_name": "Defaults", "title": "Defaults", "artist": "Defaults"},
            formats=["yaml", "html"],
        )

        client = self._make_client()
        response = client.put(
            f"/api/saved_slide/{meta['id']}",
            json={"song": _modified_song_payload()},
        )

        assert response.status_code == 200
        body = response.get_json()
        assert set(body["filenames"].keys()) == {"yaml", "html"}
        assert "pptx" not in body["filenames"]

    def test_put_endpoint_returns_404_for_nonexistent_slide(self):
        """Non-existent slide_id → 404 with explanatory error."""
        client = self._make_client()
        response = client.put(
            "/api/saved_slide/00000000-0000-0000-0000-000000000000",
            json={"song": _modified_song_payload(), "formats": ["yaml"]},
        )

        assert response.status_code == 404
        assert response.get_json()["error"] == "Slide not found"

    def test_put_endpoint_rejects_missing_song_data(self):
        """Empty body / missing 'song' key → 400."""
        meta = self._seed_slide(
            {"search_name": "NoSong", "title": "NoSong"},
            formats=["yaml"],
        )
        client = self._make_client()

        # Empty body
        r1 = client.put(f"/api/saved_slide/{meta['id']}", json={})
        assert r1.status_code == 400
        # Missing 'song' key
        r2 = client.put(
            f"/api/saved_slide/{meta['id']}", json={"formats": ["yaml"]}
        )
        assert r2.status_code == 400
        assert "Song data is required" in r2.get_json()["error"]

    def test_put_endpoint_rejects_invalid_format_tokens(self):
        """Unknown format tokens → 400 with Invalid formats."""
        meta = self._seed_slide(
            {"search_name": "BadFmt", "title": "BadFmt"},
            formats=["yaml"],
        )
        client = self._make_client()
        response = client.put(
            f"/api/saved_slide/{meta['id']}",
            json={
                "song": _modified_song_payload(),
                "formats": ["yaml", "bogus", "pptx"],
            },
        )

        assert response.status_code == 400
        assert "Invalid formats" in response.get_json()["error"]
