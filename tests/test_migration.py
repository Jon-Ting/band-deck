"""Tests for the batch migration utility that backfills YAML/Marp/HTML
files for legacy PPTX-only saved slides."""

from __future__ import annotations

import json
import os
import shutil
import tempfile

import yaml as pyyaml

import src.utils.slide_storage as storage_module
from src.utils import migration as migration_module
from src.utils.html_renderer import RenderError
from src.utils.slide_storage import (
    SLIDES_DIR,
    _meta_path,
    _slide_path,
)


def _write_meta(slide_id: str, payload: dict) -> str:
    """Persist a metadata JSON file under the (patched) SLIDES_DIR."""
    meta_path = os.path.join(storage_module.SLIDES_DIR, f"{slide_id}.json")
    with open(meta_path, "w", encoding="utf-8") as meta_file:
        json.dump(payload, meta_file)
    return meta_path


class TestMigrationUtility:
    """Isolated tests for ``migration.migrate_existing_slides()``."""

    def setup_method(self):
        """Redirect slide storage into a temporary directory for the test."""
        self._original_slides_dir = SLIDES_DIR
        self.test_dir = tempfile.mkdtemp()
        storage_module.SLIDES_DIR = self.test_dir

    def teardown_method(self):
        """Restore SLIDES_DIR and delete the temporary directory."""
        storage_module.SLIDES_DIR = self._original_slides_dir
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _seed_legacy_slide(self, slide_id: str, **overrides) -> dict:
        """Create a metadata JSON that mimics a legacy PPTX-only slide."""
        meta = {
            "id": slide_id,
            "title": "Amazing Grace",
            "artist": "John Newton",
            "key": "G",
            "filenames": {"pptx": f"{slide_id}.pptx"},
            "created_at": "2024-01-01T00:00:00+00:00",
            "updated_at": "2024-01-01T00:00:00+00:00",
            "bpm": 80,
            "time_signature": "3/4",
            "ccli_number": "1234567",
        }
        meta.update(overrides)
        # Pretend the legacy PPTX file exists so deletion-style guardrails pass.
        pptx_path = _slide_path(slide_id, "pptx")
        os.makedirs(os.path.dirname(pptx_path), exist_ok=True)
        with open(pptx_path, "wb") as pptx_file:
            pptx_file.write(b"stub pptx bytes")
        _write_meta(slide_id, meta)
        return meta

    def test_migrates_pptx_only_slide_to_all_formats(self):
        slide_id = "legacy-1"
        self._seed_legacy_slide(slide_id)

        stats = migration_module.migrate_existing_slides()

        assert stats == {"migrated": 1, "skipped": 0, "errors": 0}

        # YAML/Marp/HTML files should now exist alongside the original PPTX
        assert os.path.exists(_slide_path(slide_id, "yaml"))
        assert os.path.exists(_slide_path(slide_id, "marp"))
        assert os.path.exists(_slide_path(slide_id, "html"))
        assert os.path.exists(_slide_path(slide_id, "pptx"))

        # Metadata must reflect every format and the migration flag
        updated = json.loads(open(_meta_path(slide_id)).read())
        assert updated["filenames"]["pptx"].endswith(".pptx")
        assert updated["filenames"]["yaml"].endswith(".yaml")
        assert updated["filenames"]["marp"].endswith(".marp.md")
        assert updated["filenames"]["html"].endswith(".html")
        assert migration_module.MIGRATED_AT_KEY in updated

        # Generated artifacts must be non-empty
        assert os.path.getsize(_slide_path(slide_id, "yaml")) > 0
        assert os.path.getsize(_slide_path(slide_id, "marp")) > 0
        assert os.path.getsize(_slide_path(slide_id, "html")) > 0

    def test_migration_is_idempotent_and_skips_already_migrated(self):
        slide_id = "legacy-2"
        self._seed_legacy_slide(slide_id)

        first = migration_module.migrate_existing_slides()
        assert first == {"migrated": 1, "skipped": 0, "errors": 0}

        second = migration_module.migrate_existing_slides()
        assert second == {"migrated": 0, "skipped": 1, "errors": 0}

    def test_force_overwrites_existing_yaml_marp_html(self):
        slide_id = "legacy-3"
        self._seed_legacy_slide(slide_id)
        migration_module.migrate_existing_slides()

        sentinel_path = _slide_path(slide_id, "yaml")
        with open(sentinel_path, "w", encoding="utf-8") as yaml_file:
            yaml_file.write("sentinel: should-be-overwritten\n")

        stats = migration_module.migrate_existing_slides(force=True)
        assert stats == {"migrated": 1, "skipped": 0, "errors": 0}

        # YAML body is overwritten
        rewritten = open(sentinel_path, encoding="utf-8").read()
        assert "sentinel" not in rewritten
        assert migration_module.PLACEHOLDER_NOTE.split(".")[0] in rewritten

        # Filenames still cover every format and migrated_at is recorded
        updated = json.loads(open(_meta_path(slide_id)).read())
        for fmt in ("yaml", "marp", "html", "pptx"):
            assert fmt in updated["filenames"]
        assert migration_module.MIGRATED_AT_KEY in updated

    def test_writes_fallback_html_when_marp_render_fails(self, monkeypatch):
        slide_id = "legacy-4"
        self._seed_legacy_slide(slide_id)

        def boom(_markdown, output_path=None, **_kwargs):
            raise RenderError("mimic Marp CLI unavailable")

        monkeypatch.setattr(migration_module, "render_html", boom)

        stats = migration_module.migrate_existing_slides()

        assert stats["migrated"] == 1
        assert os.path.exists(_slide_path(slide_id, "html"))

        html = open(_slide_path(slide_id, "html"), encoding="utf-8").read()
        assert "Amazing Grace" in html
        assert migration_module.PLACEHOLDER_NOTE in html

    def test_per_slide_failure_does_not_halt_batch(self):
        good_id = "legacy-good"
        self._seed_legacy_slide(good_id)

        # A slide whose metadata is missing ``id`` will fail inside _migrate_one;
        # the batch must keep going rather than abort.
        bad_path = os.path.join(storage_module.SLIDES_DIR, "legacy-bad.json")
        with open(bad_path, "w", encoding="utf-8") as meta_file:
            json.dump({"title": "Broken Slide"}, meta_file)

        stats = migration_module.migrate_existing_slides()

        assert stats["migrated"] == 1
        assert stats["errors"] == 1
        assert stats["skipped"] == 0
        assert os.path.exists(_slide_path(good_id, "yaml"))

    def test_legacy_pptx_path_is_preserved_after_migration(self):
        slide_id = "legacy-pptx"
        self._seed_legacy_slide(slide_id)
        original_pptx_bytes = open(_slide_path(slide_id, "pptx"), "rb").read()

        migration_module.migrate_existing_slides()

        # The legacy PPTX file must remain unchanged so existing readers work.
        assert open(_slide_path(slide_id, "pptx"), "rb").read() == original_pptx_bytes

    def test_yaml_output_includes_placeholder_note(self):
        slide_id = "legacy-yaml"
        self._seed_legacy_slide(slide_id)
        migration_module.migrate_existing_slides()

        parsed = pyyaml.safe_load(
            open(_slide_path(slide_id, "yaml"), encoding="utf-8").read()
        )
        assert parsed["title"] == "Amazing Grace"
        assert parsed["target_key"] == "G"
        assert "Note" in parsed["sections"]
        assert migration_module.PLACEHOLDER_NOTE in parsed["practice_notes"]["general"]


    def test_marp_markdown_contains_song_title_metadata(self):
        slide_id = "legacy-marp"
        self._seed_legacy_slide(slide_id)
        migration_module.migrate_existing_slides()

        marp = open(_slide_path(slide_id, "marp"), encoding="utf-8").read()
        assert "# Amazing Grace" in marp
        assert "John Newton" in marp
        assert "Key: G" in marp

    def test_partial_format_set_is_not_skipped(self):
        """Slides with one or two (but not all three) formats are still migrated."""
        slide_id = "legacy-partial"
        meta = self._seed_legacy_slide(slide_id)
        meta["filenames"] = {
            "pptx": f"{slide_id}.pptx",
            "yaml": f"{slide_id}.yaml",  # Only YAML exists
        }
        _write_meta(slide_id, meta)

        stats = migration_module.migrate_existing_slides()
        assert stats == {"migrated": 1, "skipped": 0, "errors": 0}

        updated = json.loads(open(_meta_path(slide_id)).read())
        for fmt in ("yaml", "marp", "html", "pptx"):
            assert fmt in updated["filenames"]
