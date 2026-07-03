"""Tests for saved slide retrieval endpoints (Task 5.5)."""

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
        song_data["formats"] = ["yaml", "html", "pptx"]
        response = client.post("/api/save_slide", json=song_data)
        assert response.status_code == 200
        
        # List slides
        response = client.get("/api/saved_slides")
        assert response.status_code == 200
        
        slides = response.get_json()
        assert len(slides) == 1
        
        slide = slides[0]
        assert "filenames" in slide
        assert "yaml" in slide["filenames"]
        assert "html" in slide["filenames"]
        assert "pptx" in slide["filenames"]
        assert "marp" not in slide["filenames"]  # Not requested

    def test_list_slides_shows_different_format_availability_per_slide(self):
        """Test that different slides can have different available formats."""
        client = make_client()
        
        # Save first slide with YAML only
        song_data1 = make_song_data()
        song_data1["search_name"] = "Song 1"
        song_data1["formats"] = ["yaml"]
        response1 = client.post("/api/save_slide", json=song_data1)
        assert response1.status_code == 200
        
        # Save second slide with all formats
        song_data2 = make_song_data()
        song_data2["search_name"] = "Song 2"
        song_data2["formats"] = ["yaml", "marp", "html", "pptx"]
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
        assert len(slide1["filenames"]) == 1
        assert "yaml" in slide1["filenames"]
        
        assert len(slide2["filenames"]) == 4
        assert all(fmt in slide2["filenames"] for fmt in ["yaml", "marp", "html", "pptx"])

    def test_download_slide_format_pptx(self):
        """Test downloading a slide in PPTX format."""
        client = make_client()
        
        # Save a slide with PPTX format
        song_data = make_song_data()
        song_data["formats"] = ["pptx"]
        response = client.post("/api/save_slide", json=song_data)
        slide_id = response.get_json()["id"]
        
        # Download PPTX
        response = client.get(f"/api/saved_slide/{slide_id}/download/pptx")
        assert response.status_code == 200
        assert response.mimetype == "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        assert "Amazing Grace - John Newton.pptx" in response.headers.get("Content-Disposition", "")

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
        assert result["available_formats"] == ["yaml"]

    def test_download_slide_invalid_format(self):
        """Test that requesting an invalid format returns 400."""
        client = make_client()
        
        # Save a slide
        song_data = make_song_data()
        song_data["formats"] = ["pptx"]
        response = client.post("/api/save_slide", json=song_data)
        slide_id = response.get_json()["id"]
        
        # Try to download with invalid format
        response = client.get(f"/api/saved_slide/{slide_id}/download/invalid")
        assert response.status_code == 400
        result = response.get_json()
        assert "error" in result
        assert "Invalid format" in result["error"]
        assert "valid_formats" in result

    def test_download_slide_nonexistent_id(self):
        """Test that requesting a non-existent slide returns 404."""
        client = make_client()
        
        # Try to download from non-existent slide
        response = client.get("/api/saved_slide/nonexistent-id/download/pptx")
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
        song_data["formats"] = ["pptx"]
        response = client.post("/api/save_slide", json=song_data)
        slide_id = response.get_json()["id"]
        
        # Download
        response = client.get(f"/api/saved_slide/{slide_id}/download/pptx")
        assert response.status_code == 200
        # Should not have artist in filename
        assert "Amazing Grace.pptx" in response.headers.get("Content-Disposition", "")
        assert " - " not in response.headers.get("Content-Disposition", "")

    def test_download_all_supported_formats(self):
        """Test downloading all supported formats (html, marp, yaml, pptx)."""
        client = make_client()
        
        # Save a slide with all formats
        song_data = make_song_data()
        song_data["formats"] = ["html", "marp", "yaml", "pptx"]
        response = client.post("/api/save_slide", json=song_data)
        slide_id = response.get_json()["id"]
        
        # Test each format
        formats_to_test = ["html", "marp", "yaml", "pptx"]
        for fmt in formats_to_test:
            response = client.get(f"/api/saved_slide/{slide_id}/download/{fmt}")
            assert response.status_code == 200, f"Failed to download format: {fmt}"

    def test_backward_compatibility_old_download_endpoint(self):
        """Test that old /api/saved_slide/{id} GET endpoint still works for PPTX."""
        client = make_client()
        
        # Save a slide with PPTX
        song_data = make_song_data()
        song_data["formats"] = ["pptx"]
        response = client.post("/api/save_slide", json=song_data)
        slide_id = response.get_json()["id"]
        
        # Use old endpoint
        response = client.get(f"/api/saved_slide/{slide_id}")
        assert response.status_code == 200
        assert response.mimetype == "application/vnd.openxmlformats-officedocument.presentationml.presentation"

    def test_download_format_case_sensitivity(self):
        """Test that format parameter is case-sensitive (lowercase required)."""
        client = make_client()
        
        # Save a slide
        song_data = make_song_data()
        song_data["formats"] = ["pptx"]
        response = client.post("/api/save_slide", json=song_data)
        slide_id = response.get_json()["id"]
        
        # Try uppercase format
        response = client.get(f"/api/saved_slide/{slide_id}/download/PPTX")
        assert response.status_code == 400  # Should reject uppercase

    def test_pdf_format_support(self):
        """Test that PDF format is recognized as valid (even if not yet implemented)."""
        client = make_client()
        
        # Save a slide
        song_data = make_song_data()
        song_data["formats"] = ["pptx"]
        response = client.post("/api/save_slide", json=song_data)
        slide_id = response.get_json()["id"]
        
        # Try to download PDF (should be valid format but not available)
        response = client.get(f"/api/saved_slide/{slide_id}/download/pdf")
        # Should return 404 (not available) not 400 (invalid format)
        assert response.status_code == 404
        result = response.get_json()
        assert "not available" in result["error"]
        assert "available_formats" in result
