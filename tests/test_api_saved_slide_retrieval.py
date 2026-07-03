"""Tests for saved slide retrieval endpoints."""

from __future__ import annotations

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


class TestSavedSlideRetrievalEndpoints:
    """Test suite for /api/saved_slides and /api/saved_slide/{id}/download/{format} endpoints."""

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

    def test_list_slides_includes_format_availability(self):
        """Test that /api/saved_slides includes filenames dict showing format availability."""
        client = make_client()

        # Save a slide with multiple formats
        song_data = make_song_data()
        song_data["formats"] = ["yaml", "html", "marp"]
        response = client.post("/api/save_slide", json=song_data)
        assert response.status_code == 200

        # List slides
        response = client.get("/api/saved_slides")
        assert response.status_code == 200

        slides = response.get_json()
        assert len(slides) == 1

        slide = slides[0]
        assert "filenames" in slide
        assert set(slide["filenames"].keys()) == {"yaml", "html", "marp"}
        assert "pptx" not in slide["filenames"]

    def test_list_slides_shows_different_format_availability_per_slide(self):
        """Test that different slides can have different available formats."""
        client = make_client()

        # Save first slide with YAML only
        song_data1 = make_song_data()
        song_data1["search_name"] = "Song 1"
        song_data1["formats"] = ["yaml"]
        response1 = client.post("/api/save_slide", json=song_data1)
        assert response1.status_code == 200

        # Save second slide with multiple formats
        song_data2 = make_song_data()
        song_data2["search_name"] = "Song 2"
        song_data2["formats"] = ["yaml", "marp", "html"]
        response2 = client.post("/api/save_slide", json=song_data2)
        assert response2.status_code == 200

        # List slides
        response = client.get("/api/saved_slides")
        assert response.status_code == 200

        slides = response.get_json()
        assert len(slides) == 2

        # Find each slide by title
        slide1 = next(s for s in slides if s["title"] == "Song 1")
        slide2 = next(s for s in slides if s["title"] == "Song 2")

        # Verify format availability differs
        assert set(slide1["filenames"].keys()) == {"yaml"}
        assert "pptx" not in slide1["filenames"]

        assert set(slide2["filenames"].keys()) == {"yaml", "marp", "html"}
        assert "pptx" not in slide2["filenames"]

    def test_download_slide_legacy_pptx_format_rejected(self):
        """The legacy PPTX format is no longer a valid download option."""
        client = make_client()

        song_data = make_song_data()
        song_data["formats"] = ["yaml"]
        response = client.post("/api/save_slide", json=song_data)
        slide_id = response.get_json()["id"]

        response = client.get(f"/api/saved_slide/{slide_id}/download/pptx")
        # PPTX is no longer in valid_formats, so the request is rejected as
        # an invalid format rather than being treated as a missing file.
        assert response.status_code == 400
        body = response.get_json()
        assert "Invalid format" in body["error"]
        assert "pptx" not in body["valid_formats"]

    def test_download_slide_format_html(self):
        """Test downloading a slide in HTML format."""
        client = make_client()

        # Save a slide with HTML format
        song_data = make_song_data()
        song_data["formats"] = ["html"]
        response = client.post("/api/save_slide", json=song_data)
        slide_id = response.get_json()["id"]

        # Download HTML
        response = client.get(f"/api/saved_slide/{slide_id}/download/html")
        assert response.status_code == 200
        assert response.mimetype == "text/html"
        assert "Amazing Grace - John Newton.html" in response.headers.get("Content-Disposition", "")

    def test_download_slide_format_yaml(self):
        """Test downloading a slide in YAML format."""
        client = make_client()

        # Save a slide with YAML format
        song_data = make_song_data()
        song_data["formats"] = ["yaml"]
        response = client.post("/api/save_slide", json=song_data)
        slide_id = response.get_json()["id"]

        # Download YAML
        response = client.get(f"/api/saved_slide/{slide_id}/download/yaml")
        assert response.status_code == 200
        assert response.mimetype == "text/yaml"
        assert "Amazing Grace - John Newton.yaml" in response.headers.get("Content-Disposition", "")

    def test_download_slide_format_marp(self):
        """Test downloading a slide in Marp markdown format."""
        client = make_client()

        # Save a slide with Marp format
        song_data = make_song_data()
        song_data["formats"] = ["marp"]
        response = client.post("/api/save_slide", json=song_data)
        slide_id = response.get_json()["id"]

        # Download Marp
        response = client.get(f"/api/saved_slide/{slide_id}/download/marp")
        assert response.status_code == 200
        assert response.mimetype == "text/markdown"
        assert "Amazing Grace - John Newton.marp.md" in response.headers.get("Content-Disposition", "")

    def test_download_slide_format_unavailable(self):
        """Test that requesting an unavailable format returns 404."""
        client = make_client()

        # Save a slide with only YAML format
        song_data = make_song_data()
        song_data["formats"] = ["yaml"]
        response = client.post("/api/save_slide", json=song_data)
        slide_id = response.get_json()["id"]

        # Try to download HTML (not available)
        response = client.get(f"/api/saved_slide/{slide_id}/download/html")
        assert response.status_code == 404
        result = response.get_json()
        assert "error" in result
        assert "not available" in result["error"]
        assert "available_formats" in result
        assert set(result["available_formats"]) == {"yaml"}

    def test_download_slide_invalid_format(self):
        """Test that requesting an invalid format returns 400."""
        client = make_client()

        # Save a slide
        song_data = make_song_data()
        song_data["formats"] = ["yaml"]
        response = client.post("/api/save_slide", json=song_data)
        slide_id = response.get_json()["id"]

        # Try to download with invalid format
        response = client.get(f"/api/saved_slide/{slide_id}/download/invalid")
        assert response.status_code == 400
        result = response.get_json()
        assert "error" in result
        assert "Invalid format" in result["error"]
        assert "valid_formats" in result
        assert "pptx" not in result["valid_formats"]

    def test_download_slide_nonexistent_id(self):
        """Test that requesting a non-existent slide returns 404."""
        client = make_client()

        # Try to download from non-existent slide
        response = client.get("/api/saved_slide/nonexistent-id/download/yaml")
        assert response.status_code == 404
        result = response.get_json()
        assert "error" in result
        assert "not found" in result["error"].lower()

    def test_download_slide_filename_without_artist(self):
        """Test download filename when artist is not present."""
        client = make_client()

        # Save a slide without artist
        song_data = make_song_data()
        song_data["artist"] = None
        song_data["formats"] = ["yaml"]
        response = client.post("/api/save_slide", json=song_data)
        slide_id = response.get_json()["id"]

        # Download
        response = client.get(f"/api/saved_slide/{slide_id}/download/yaml")
        assert response.status_code == 200
        # Should not have artist in filename
        assert "Amazing Grace.yaml" in response.headers.get("Content-Disposition", "")
        assert " - " not in response.headers.get("Content-Disposition", "")

    def test_download_all_supported_non_legacy_formats(self):
        """Test downloading all supported non-legacy formats (html, marp, yaml)."""
        client = make_client()

        # Save a slide with all formats
        song_data = make_song_data()
        song_data["formats"] = ["html", "marp", "yaml"]
        response = client.post("/api/save_slide", json=song_data)
        slide_id = response.get_json()["id"]

        # Test each format
        formats_to_test = ["html", "marp", "yaml"]
        for fmt in formats_to_test:
            response = client.get(f"/api/saved_slide/{slide_id}/download/{fmt}")
            assert response.status_code == 200, f"Failed to download format: {fmt}"

    def test_legacy_unversioned_download_endpoint_removed(self):
        """The unversioned ``/api/saved_slide/<id>`` GET endpoint is gone now
        that PPTX is no longer the implicit default format. Callers must use
        the explicit ``/api/saved_slide/<id>/download/<format>`` endpoint."""
        client = make_client()

        song_data = make_song_data()
        song_data["formats"] = ["yaml", "html"]
        response = client.post("/api/save_slide", json=song_data)
        slide_id = response.get_json()["id"]

        response = client.get(f"/api/saved_slide/{slide_id}")
        assert response.status_code == 404

    def test_download_format_case_sensitivity(self):
        """Test that format parameter is case-sensitive (lowercase required)."""
        client = make_client()

        # Save a slide
        song_data = make_song_data()
        song_data["formats"] = ["yaml"]
        response = client.post("/api/save_slide", json=song_data)
        slide_id = response.get_json()["id"]

        # Try uppercase format
        response = client.get(f"/api/saved_slide/{slide_id}/download/YAML")
        assert response.status_code == 400  # Should reject uppercase

    def test_pdf_format_recognised_but_never_generated(self):
        """PDF is recognised as a valid format token but not generated by the
        server-side pipeline; requesting it falls back to ``404 not available``
        rather than ``400 invalid format``."""
        client = make_client()

        # Save a slide
        song_data = make_song_data()
        song_data["formats"] = ["yaml"]
        response = client.post("/api/save_slide", json=song_data)
        slide_id = response.get_json()["id"]

        # Try to download PDF (should be valid format but not available)
        response = client.get(f"/api/saved_slide/{slide_id}/download/pdf")
        # Should return 404 (not available) not 400 (invalid format)
        assert response.status_code == 404
        result = response.get_json()
        assert "not available" in result["error"]
        assert "available_formats" in result
