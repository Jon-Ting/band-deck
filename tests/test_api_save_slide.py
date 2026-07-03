"""Tests for the /api/save_slide endpoint (Task 5.4)."""

from __future__ import annotations

import os
import tempfile

from flask import Flask

from src.routes.api import api_bp
from src.utils import slide_storage


def make_client():
    """Create a Flask test client with the API blueprint."""
    app = Flask(__name__)
    app.register_blueprint(api_bp, url_prefix="/api")
    return app.test_client()


def make_song_data() -> dict:
    """Create sample song data for testing."""
    return {
        "search_name": "Amazing Grace",
        "title": "Amazing Grace",
        "artist": "John Newton",
        "key": "G",
        "bpm": 80,
        "time_signature": "3/4",
        "ccli_number": "12345",
        "content": "Amazing grace, how sweet the sound",
    }


class TestSaveSlideEndpoint:
    """Test suite for /api/save_slide endpoint."""

    def setup_method(self):
        """Create temporary directory for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_slides_dir = slide_storage.SLIDES_DIR
        slide_storage.SLIDES_DIR = self.temp_dir

    def teardown_method(self):
        """Clean up temporary directory after each test."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)
        slide_storage.SLIDES_DIR = self.original_slides_dir

    def test_save_slide_backward_compatibility_no_formats_parameter(self):
        """Test backward compatibility - omitting formats defaults to PPTX."""
        client = make_client()
        song_data = make_song_data()

        response = client.post("/api/save_slide", json=song_data)

        assert response.status_code == 200
        result = response.get_json()

        # Verify metadata structure
        assert "id" in result
        assert result["title"] == "Amazing Grace"
        assert result["artist"] == "John Newton"
        assert result["key"] == "G"
        assert "filenames" in result
        assert "pptx" in result["filenames"]
        assert result["filenames"]["pptx"].endswith(".pptx")

        # Verify only PPTX was generated
        assert len(result["filenames"]) == 1
        assert "yaml" not in result["filenames"]
        assert "marp" not in result["filenames"]
        assert "html" not in result["filenames"]

    def test_save_slide_with_single_format(self):
        """Test saving with a single format specified."""
        client = make_client()
        song_data = make_song_data()
        song_data["formats"] = ["pptx"]

        response = client.post("/api/save_slide", json=song_data)

        assert response.status_code == 200
        result = response.get_json()

        assert "filenames" in result
        assert "pptx" in result["filenames"]
        assert len(result["filenames"]) == 1

    def test_save_slide_with_multiple_formats(self):
        """Test saving with multiple formats (YAML, Marp, HTML, PPTX)."""
        client = make_client()
        song_data = make_song_data()
        song_data["formats"] = ["yaml", "marp", "html", "pptx"]

        response = client.post("/api/save_slide", json=song_data)

        assert response.status_code == 200
        result = response.get_json()

        # Verify all requested formats in filenames dict
        assert "filenames" in result
        assert "yaml" in result["filenames"]
        assert "marp" in result["filenames"]
        assert "html" in result["filenames"]
        assert "pptx" in result["filenames"]

        # Verify filename extensions
        assert result["filenames"]["yaml"].endswith(".yaml")
        assert result["filenames"]["marp"].endswith(".marp.md")
        assert result["filenames"]["html"].endswith(".html")
        assert result["filenames"]["pptx"].endswith(".pptx")

        # Verify files exist
        slide_id = result["id"]
        assert os.path.exists(os.path.join(self.temp_dir, f"{slide_id}.yaml"))
        assert os.path.exists(os.path.join(self.temp_dir, f"{slide_id}.marp.md"))
        assert os.path.exists(os.path.join(self.temp_dir, f"{slide_id}.html"))
        assert os.path.exists(os.path.join(self.temp_dir, f"{slide_id}.pptx"))

    def test_save_slide_with_partial_formats(self):
        """Test saving only specific formats (e.g., YAML and HTML)."""
        client = make_client()
        song_data = make_song_data()
        song_data["formats"] = ["yaml", "html"]

        response = client.post("/api/save_slide", json=song_data)

        assert response.status_code == 200
        result = response.get_json()

        # Verify only requested formats
        assert "filenames" in result
        assert "yaml" in result["filenames"]
        assert "html" in result["filenames"]
        assert "pptx" not in result["filenames"]
        assert "marp" not in result["filenames"]

    def test_save_slide_nested_structure(self):
        """Test saving with nested song_data and formats structure."""
        client = make_client()
        request_data = {"song_data": make_song_data(), "formats": ["yaml", "pptx"]}

        response = client.post("/api/save_slide", json=request_data)

        assert response.status_code == 200
        result = response.get_json()

        assert "filenames" in result
        assert "yaml" in result["filenames"]
        assert "pptx" in result["filenames"]
        assert len(result["filenames"]) == 2

    def test_save_slide_rejects_invalid_formats(self):
        """Test that invalid format values are rejected."""
        client = make_client()
        song_data = make_song_data()
        song_data["formats"] = ["pptx", "invalid_format", "another_bad_one"]

        response = client.post("/api/save_slide", json=song_data)

        assert response.status_code == 400
        result = response.get_json()
        assert "error" in result
        assert "Invalid formats" in result["error"]
        assert "valid_formats" in result

    def test_save_slide_rejects_non_list_formats(self):
        """Test that formats parameter must be a list."""
        client = make_client()
        song_data = make_song_data()
        song_data["formats"] = "pptx"  # String instead of list

        response = client.post("/api/save_slide", json=song_data)

        assert response.status_code == 400
        result = response.get_json()
        assert "error" in result
        assert "must be a list" in result["error"]

    def test_save_slide_rejects_empty_request(self):
        """Test that empty request body is rejected."""
        client = make_client()

        response = client.post("/api/save_slide", json={})

        assert response.status_code == 400
        result = response.get_json()
        assert "error" in result

    def test_save_slide_returns_metadata_with_timestamps(self):
        """Test that response includes created_at and updated_at timestamps."""
        client = make_client()
        song_data = make_song_data()
        song_data["formats"] = ["pptx"]

        response = client.post("/api/save_slide", json=song_data)

        assert response.status_code == 200
        result = response.get_json()

        assert "created_at" in result
        assert "updated_at" in result

        # Verify ISO 8601 format
        from datetime import datetime

        datetime.fromisoformat(result["created_at"])  # Should not raise
        datetime.fromisoformat(result["updated_at"])  # Should not raise

    def test_save_slide_returns_optional_metadata_fields(self):
        """Test that optional metadata fields are included when present."""
        client = make_client()
        song_data = make_song_data()
        song_data["formats"] = ["pptx"]

        response = client.post("/api/save_slide", json=song_data)

        assert response.status_code == 200
        result = response.get_json()

        # Optional fields from song_data should be in response
        assert result["bpm"] == 80
        assert result["time_signature"] == "3/4"
        assert result["ccli_number"] == "12345"

    def test_save_slide_explicit_user_action_required(self):
        """
        Test that save requires explicit POST request (Requirement 14.2).
        This test verifies the endpoint only accepts POST method.
        """
        client = make_client()

        # GET should not be allowed
        response = client.get("/api/save_slide")
        assert response.status_code == 405  # Method Not Allowed

        # PUT should not be allowed
        response = client.put("/api/save_slide", json=make_song_data())
        assert response.status_code == 405

        # Only POST should work
        response = client.post("/api/save_slide", json=make_song_data())
        assert response.status_code == 200

    def test_save_slide_all_supported_formats(self):
        """Test saving with all supported formats to verify none are missing."""
        client = make_client()
        song_data = make_song_data()
        # Note: 'pdf' is listed in requirements but not yet implemented in save_slide()
        # Testing only implemented formats for now
        song_data["formats"] = ["yaml", "marp", "html", "pptx"]

        response = client.post("/api/save_slide", json=song_data)

        assert response.status_code == 200
        result = response.get_json()

        for format in ["yaml", "marp", "html", "pptx"]:
            assert format in result["filenames"], f"Missing format: {format}"
