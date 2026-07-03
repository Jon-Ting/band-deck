import os
import json
import shutil
import tempfile
from datetime import datetime, timezone
from src.utils.slide_storage import (
    save_slide,
    list_slides,
    get_slide,
    delete_slide,
    get_slide_file,
    _slide_path,
    _meta_path,
    SLIDES_DIR,
)


def test_slides_dir_resolves_under_data_saved_slides():
    """Smoke test: ``SLIDES_DIR`` points at ``<project_root>/data/saved_slides``.

    Asserts the relocation correctness property end-to-end:

    - the path resolves to a ``data/saved_slides`` tail (not ``src/saved_slides``),
    - the directory exists on disk (auto-created at import time).
    """
    # Path parts comparison is robust to absolute-prefix variation across hosts.
    assert SLIDES_DIR.parts[-2:] == ("data", "saved_slides"), (
        f"SLIDES_DIR should end with data/saved_slides, got {SLIDES_DIR}"
    )
    assert "src/saved_slides" not in str(SLIDES_DIR)
    # Auto-created at module import time via SLIDES_DIR.mkdir(parents=True, exist_ok=True).
    assert SLIDES_DIR.exists(), f"SLIDES_DIR does not exist on disk: {SLIDES_DIR}"


class TestSlideStorage:
    """Tests for multi-format slide storage functionality."""

    def setup_method(self):
        """Create a temporary directory for test slides."""
        self.original_slides_dir = SLIDES_DIR
        self.test_slides_dir = tempfile.mkdtemp()
        # Monkey-patch SLIDES_DIR for tests
        import src.utils.slide_storage as storage_module

        storage_module.SLIDES_DIR = self.test_slides_dir

    def teardown_method(self):
        """Clean up temporary directory."""
        if os.path.exists(self.test_slides_dir):
            shutil.rmtree(self.test_slides_dir)
        # Restore original SLIDES_DIR
        import src.utils.slide_storage as storage_module

        storage_module.SLIDES_DIR = self.original_slides_dir

    def test_save_slide_yaml_only_backward_compatibility(self):
        """Backward compatibility: omitting formats gives YAML/Marp/HTML, no PPTX."""
        song_data = {
            "search_name": "Amazing Grace",
            "title": "Amazing Grace (Official)",
            "artist": "John Newton",
            "key": "G",
            "bpm": 80,
            "time_signature": "3/4",
            "ccli_number": "1234567",
        }

        meta = save_slide(song_data)

        # Verify metadata structure
        assert "id" in meta
        assert meta["title"] == "Amazing Grace"
        assert meta["artist"] == "John Newton"
        assert meta["key"] == "G"
        assert meta["bpm"] == 80
        assert meta["time_signature"] == "3/4"
        assert meta["license_number"] == "1234567"

        # Verify filenames dict now uses the supported formats and never
        # includes the legacy PPTX format.
        assert "filenames" in meta
        assert set(meta["filenames"].keys()) == {"yaml", "marp", "html"}
        assert "pptx" not in meta["filenames"]

        # Verify timestamps
        assert "created_at" in meta
        assert "updated_at" in meta
        assert meta["created_at"] == meta["updated_at"]

        # Verify timestamp is ISO 8601 UTC
        created = datetime.fromisoformat(meta["created_at"])
        assert created.tzinfo is not None

        # Verify expected files were created
        slide_id = meta["id"]
        assert os.path.exists(_slide_path(slide_id, "yaml"))
        assert os.path.exists(_slide_path(slide_id, "marp"))
        assert os.path.exists(_slide_path(slide_id, "html"))

    def test_save_slide_multi_format(self):
        """Test saving slide in multiple formats (YAML, Marp, HTML)."""
        song_data = {
            "search_name": "How Great Thou Art",
            "artist": "Carl Boberg",
            "key": "C",
        }

        meta = save_slide(song_data, formats=["yaml", "marp", "html"])

        # Verify all formats in filenames dict
        assert "filenames" in meta
        assert set(meta["filenames"].keys()) == {"yaml", "marp", "html"}
        assert "pptx" not in meta["filenames"]

        # Verify all files were created
        slide_id = meta["id"]
        assert os.path.exists(_slide_path(slide_id, "yaml"))
        assert os.path.exists(_slide_path(slide_id, "marp"))
        assert os.path.exists(_slide_path(slide_id, "html"))

        # Verify file extensions in filenames
        assert meta["filenames"]["yaml"].endswith(".yaml")
        assert meta["filenames"]["marp"].endswith(".marp.md")
        assert meta["filenames"]["html"].endswith(".html")

    def test_save_slide_yaml_and_html_only(self):
        """Test saving only YAML and HTML formats."""
        song_data = {"search_name": "Cornerstone", "artist": "Hillsong", "key": "E"}

        meta = save_slide(song_data, formats=["yaml", "html"])

        # Verify only requested formats in filenames dict
        assert "filenames" in meta
        assert set(meta["filenames"].keys()) == {"yaml", "html"}
        assert "pptx" not in meta["filenames"]
        assert "marp" not in meta["filenames"]

        # Verify only requested files were created
        slide_id = meta["id"]
        assert os.path.exists(_slide_path(slide_id, "yaml"))
        assert os.path.exists(_slide_path(slide_id, "html"))
        assert not os.path.exists(_slide_path(slide_id, "marp"))

    def test_save_slide_yaml_only(self):
        """Test saving only YAML format."""
        song_data = {"search_name": "Mighty God", "artist": "Bethel", "key": "G"}

        meta = save_slide(song_data, formats=["yaml"])

        # Verify only YAML in filenames
        assert set(meta["filenames"].keys()) == {"yaml"}
        assert "pptx" not in meta["filenames"]
        assert "marp" not in meta["filenames"]
        assert "html" not in meta["filenames"]

    def test_save_slide_defaults_to_yaml_marp_html(self):
        """Test that omitting formats parameter defaults to YAML/Marp/HTML."""
        song_data = {
            "search_name": "Blessed Be Your Name",
            "artist": "Matt Redman",
            "key": "A",
        }

        meta = save_slide(song_data)  # No formats parameter

        # Should default to YAML/Marp/HTML now that PPTX is gone
        assert "filenames" in meta
        assert set(meta["filenames"].keys()) == {"yaml", "marp", "html"}

        slide_id = meta["id"]
        assert os.path.exists(_slide_path(slide_id, "yaml"))
        assert os.path.exists(_slide_path(slide_id, "marp"))
        assert os.path.exists(_slide_path(slide_id, "html"))

    def test_metadata_persisted_to_json(self):
        """Test that metadata is correctly saved to JSON file."""
        song_data = {
            "search_name": "In Christ Alone",
            "artist": "Keith Getty",
            "key": "D",
            "bpm": 72,
        }

        meta = save_slide(song_data, formats=["yaml", "html"])
        slide_id = meta["id"]

        # Read metadata from disk
        meta_path = _meta_path(slide_id)
        assert os.path.exists(meta_path)

        with open(meta_path, "r", encoding="utf-8") as f:
            saved_meta = json.load(f)

        # Verify structure matches
        assert saved_meta["id"] == slide_id
        assert saved_meta["title"] == "In Christ Alone"
        assert saved_meta["artist"] == "Keith Getty"
        assert saved_meta["key"] == "D"
        assert saved_meta["bpm"] == 72
        assert "filenames" in saved_meta
        assert "created_at" in saved_meta
        assert "updated_at" in saved_meta

    def test_list_slides_returns_all_saved_slides(self):
        """Test listing all saved slides."""
        # Save multiple slides
        save_slide({"search_name": "Song 1", "artist": "Artist 1"}, formats=["yaml"])
        save_slide(
            {"search_name": "Song 2", "artist": "Artist 2"}, formats=["yaml", "html"]
        )
        save_slide(
            {"search_name": "Song 3", "artist": "Artist 3"}, formats=["marp", "html"]
        )

        slides = list_slides()

        assert len(slides) == 3
        titles = {s["title"] for s in slides}
        assert "Song 1" in titles
        assert "Song 2" in titles
        assert "Song 3" in titles

    def test_get_slide_retrieves_metadata(self):
        """Test retrieving a specific slide's metadata."""
        song_data = {"search_name": "Test Song", "artist": "Test Artist"}
        meta = save_slide(song_data, formats=["yaml"])

        retrieved = get_slide(meta["id"])

        assert retrieved is not None
        assert retrieved["id"] == meta["id"]
        assert retrieved["title"] == "Test Song"
        assert retrieved["filenames"] == meta["filenames"]

    def test_get_slide_returns_none_for_nonexistent_id(self):
        """Test that get_slide returns None for invalid ID."""
        result = get_slide("nonexistent-uuid")
        assert result is None

    def test_get_slide_file_returns_correct_paths(self):
        """Test retrieving file paths for different formats."""
        song_data = {"search_name": "Multi Format Song"}
        meta = save_slide(song_data, formats=["yaml", "marp", "html"])
        slide_id = meta["id"]

        # Verify each format returns correct path
        yaml_path = get_slide_file(slide_id, "yaml")
        assert yaml_path is not None
        assert yaml_path.endswith(".yaml")
        assert os.path.exists(yaml_path)

        marp_path = get_slide_file(slide_id, "marp")
        assert marp_path is not None
        assert marp_path.endswith(".marp.md")
        assert os.path.exists(marp_path)

        html_path = get_slide_file(slide_id, "html")
        assert html_path is not None
        assert html_path.endswith(".html")
        assert os.path.exists(html_path)

    def test_get_slide_file_returns_none_for_unsaved_format(self):
        """Test that get_slide_file returns None for formats not saved."""
        song_data = {"search_name": "YAML Only Song"}
        meta = save_slide(song_data, formats=["yaml"])
        slide_id = meta["id"]

        # HTML was not saved, should return None
        html_path = get_slide_file(slide_id, "html")
        assert html_path is None

    def test_get_slide_file_rejects_legacy_pptx_format(self):
        """Test that pptx is no longer a recognised format on retrieval."""
        song_data = {"search_name": "Legacy Format Song"}
        meta = save_slide(song_data, formats=["yaml"])
        slide_id = meta["id"]

        # The legacy PPTX format path helper would compute a non-existent file.
        # The filename does not exist on disk and the metadata does not list it.
        pptx_path = get_slide_file(slide_id, "pptx")
        assert pptx_path is None
        assert "pptx" not in meta["filenames"]

    def test_delete_slide_removes_all_formats(self):
        """Test that deleting a slide removes all associated files."""
        song_data = {"search_name": "Delete Me"}
        meta = save_slide(song_data, formats=["yaml", "marp", "html"])
        slide_id = meta["id"]

        # Verify files exist
        assert os.path.exists(_slide_path(slide_id, "yaml"))
        assert os.path.exists(_slide_path(slide_id, "marp"))
        assert os.path.exists(_slide_path(slide_id, "html"))
        assert os.path.exists(_meta_path(slide_id))

        # Delete slide
        result = delete_slide(slide_id)
        assert result is True

        # Verify all files removed
        assert not os.path.exists(_slide_path(slide_id, "yaml"))
        assert not os.path.exists(_slide_path(slide_id, "marp"))
        assert not os.path.exists(_slide_path(slide_id, "html"))
        assert not os.path.exists(_meta_path(slide_id))

    def test_delete_slide_removes_legacy_pptx_file_if_present(self):
        """Legacy PPTX artefacts left on disk after the migration are still
        scrubbed by ``delete_slide`` to avoid orphaned clutter."""
        song_data = {"search_name": "Old PPTX Slide"}
        meta = save_slide(song_data, formats=["yaml"])
        slide_id = meta["id"]

        # Simulate a leftover legacy .pptx file (e.g. from a pre-removal install)
        legacy_pptx = _slide_path(slide_id, "pptx")
        with open(legacy_pptx, "wb") as fp:
            fp.write(b"legacy pptx bytes")

        assert delete_slide(slide_id) is True
        assert not os.path.exists(legacy_pptx)

    def test_delete_slide_returns_false_for_nonexistent(self):
        """Test that deleting a nonexistent slide returns False."""
        result = delete_slide("nonexistent-uuid")
        assert result is False

    def test_search_name_preferred_over_title(self):
        """Test that search_name is used as title if present."""
        song_data = {
            "search_name": "User Input Name",
            "title": "Official Scraped Title",
            "artist": "Test Artist",
        }

        meta = save_slide(song_data, formats=["yaml"])

        # search_name should be used as the title
        assert meta["title"] == "User Input Name"

    def test_title_fallback_when_no_search_name(self):
        """Test that title is used when search_name is not present."""
        song_data = {"title": "Fallback Title", "artist": "Test Artist"}

        meta = save_slide(song_data, formats=["yaml"])

        assert meta["title"] == "Fallback Title"

    def test_optional_metadata_fields_included(self):
        """Test that optional metadata fields are included when present."""
        song_data = {
            "search_name": "Complete Metadata Song",
            "artist": "Test Artist",
            "key": "G",
            "bpm": 120,
            "time_signature": "4/4",
            "license_number": "9999999",
        }

        meta = save_slide(song_data, formats=["yaml"])

        assert meta["bpm"] == 120
        assert meta["time_signature"] == "4/4"
        assert meta["license_number"] == "9999999"

    def test_optional_metadata_fields_omitted_when_absent(self):
        """Test that optional fields are not included when absent from song_data."""
        song_data = {"search_name": "Minimal Song", "artist": "Minimal Artist"}

        meta = save_slide(song_data, formats=["yaml"])

        assert "bpm" not in meta
        assert "time_signature" not in meta
        assert "license_number" not in meta

    def test_timestamps_are_iso8601_utc_format(self):
        """Test that timestamps follow ISO 8601 UTC format."""
        song_data = {"search_name": "Timestamp Test"}
        meta = save_slide(song_data, formats=["yaml"])

        # Parse timestamps
        created_at = datetime.fromisoformat(meta["created_at"])
        updated_at = datetime.fromisoformat(meta["updated_at"])

        # Verify UTC timezone
        assert created_at.tzinfo == timezone.utc
        assert updated_at.tzinfo == timezone.utc

        # Verify format matches expected (should contain 'T' and timezone info)
        assert "T" in meta["created_at"]
        assert (
            "+" in meta["created_at"]
            or meta["created_at"].endswith("Z")
            or meta["created_at"].endswith("+00:00")
        )

    def test_slide_path_helper_generates_correct_extensions(self):
        """Test that _slide_path helper generates correct file extensions."""
        slide_id = "test-uuid-123"

        assert _slide_path(slide_id, "yaml").endswith(".yaml")
        assert _slide_path(slide_id, "marp").endswith(".marp.md")
        assert _slide_path(slide_id, "html").endswith(".html")

    def test_meta_path_helper_generates_json_path(self):
        """Test that _meta_path helper generates correct JSON path."""
        slide_id = "test-uuid-456"
        meta_path = _meta_path(slide_id)

        assert meta_path.endswith(".json")
        assert slide_id in meta_path
