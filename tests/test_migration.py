"""Tests for the batch migration utility that backfills YAML/Marp/HTML
files for legacy saved slides.

PPTX was retired together with this migration; the helper is now exercised
against legacy metadata that may still carry an orphaned ``pptx`` filename
tombstone, but the on-disk file is not produced or preserved by the
migration itself."""

import json
import os
import shutil
import tempfile
from pathlib import Path

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
        """Create a metadata JSON that mimics a legacy slide.

        A tombstone ``pptx`` filename may be present to mirror metadata
        written before PPTX was deprecated, but no actual ``.pptx`` file is
        written — the migration utility never produces or reads one.
        """
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
            "license_number": "1234567",
        }
        meta.update(overrides)
        _write_meta(slide_id, meta)
        return meta

    def test_migrates_pptx_only_slide_to_all_formats(self):
        """Migration writes YAML/Marp/HTML for a legacy metadata-only slide.

        The migration utility no longer creates or preserves a ``.pptx``
        filesystem artefact (PowerPoint export was retired). The ``pptx``
        filename entry remains in metadata as a tombstone for backward
        compatibility.
        """
        slide_id = "legacy-1"
        self._seed_legacy_slide(slide_id)

        stats = migration_module.migrate_existing_slides()

        assert stats == {"migrated": 1, "skipped": 0, "errors": 0}

        # YAML/Marp/HTML files exist after migration
        assert os.path.exists(_slide_path(slide_id, "yaml"))
        assert os.path.exists(_slide_path(slide_id, "marp"))
        assert os.path.exists(_slide_path(slide_id, "html"))
        # No pptx artefact is produced; only the tombstone in metadata remains
        assert not os.path.exists(_slide_path(slide_id, "pptx"))

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

    def test_legacy_pptx_tombstone_in_filenames_is_preserved(self):
        """When legacy metadata still references a ``.pptx`` filename entry
        (because it predates the PPTX removal), the migration must leave that
        tombstone alone rather than stripping it. The new YAML/Marp/HTML
        files coexist with the historical entry."""
        slide_id = "legacy-pptx-tombstone"
        self._seed_legacy_slide(slide_id)

        migration_module.migrate_existing_slides()

        updated = json.loads(open(_meta_path(slide_id)).read())
        # Tombstone preserved
        assert updated["filenames"].get("pptx") == f"{slide_id}.pptx"
        # New formats emitted
        for fmt in ("yaml", "marp", "html"):
            assert fmt in updated["filenames"]
        assert os.path.exists(_slide_path(slide_id, "yaml"))
        assert os.path.exists(_slide_path(slide_id, "marp"))
        assert os.path.exists(_slide_path(slide_id, "html"))

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
        # YAML/Marp/HTML get populated; the legacy pptx tombstone stays.
        for fmt in ("yaml", "marp", "html", "pptx"):
            assert fmt in updated["filenames"]
        assert os.path.exists(_slide_path(slide_id, "marp"))
        assert os.path.exists(_slide_path(slide_id, "html"))


class TestChordYamlMigration:
    """Isolated tests for the chord-text normalisation helpers.

    These cover the bracket-aware migration utility that converts
    Unicode chord typography (``G\u2077``, ``D/F\u266f``, ``C\u1d50\u1d43\u02b2\u2077``)
    inside ``[...]`` spans of song YAML files into plain ASCII so that
    downstream rendering and grep/diff stay clean.
    """

    def setup_method(self):
        self.test_dir = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _path(self, name: str = "song.yaml") -> str:
        return os.path.join(self.test_dir, name)

    def test_normalize_chord_yaml_text_converts_brackets_only(self):
        # Bracketed chord text is rewritten in place; surrounding YAML
        # (including free-text Unicode like the French ``\u00e9`` accent
        # in lyrics) is preserved untouched.
        original = (
            "title: 'Amazing Grace'\n"
            "sections:\n"
            "  verse:\n"
            "    chordpro: \"[G\u2077]Amazing [D/F\u266f]grace so [C\u1d50\u1d43\u02b2\u2077]sweet\"\n"
            "    lyrics: 'caf\u00e9'\n"
        )
        rewritten = migration_module.normalize_chord_yaml_text(original)

        assert "[G7]" in rewritten
        assert "[D/F#]" in rewritten
        assert "[Cmaj7]" in rewritten
        # French accent and surrounding YAML structure preserved.
        assert "caf\u00e9" in rewritten
        assert "title: 'Amazing Grace'" in rewritten
        assert "sections:\n" in rewritten

    def test_normalize_chord_yaml_text_is_idempotent_on_canonical_text(self):
        original = (
            "chordpro: \"[G]Amazing [Bm]grace\"\n"
            "meta: 'unicode like caf\u00e9 stays'\n"
        )
        first = migration_module.normalize_chord_yaml_text(original)
        second = migration_module.normalize_chord_yaml_text(first)
        assert first == second

    def test_normalize_does_not_touch_non_chord_brackets(self):
        # ``[foo, bar]`` is an inline YAML list reference — we leave it
        # alone because it is not a chord bracket.
        original = (
            "tags: [foo, bar]\n"
            "chordpro: \"[G\u2077]lyric\"\n"
        )
        rewritten = migration_module.normalize_chord_yaml_text(original)
        assert "[foo, bar]" in rewritten
        assert "[G7]" in rewritten

    def test_migrate_chord_yaml_file_returns_true_on_change(self):
        path = self._path()
        with open(path, "w", encoding="utf-8") as f:
            f.write("chordpro: \"[G\u2077]song\"\n")
        assert migration_module.migrate_chord_yaml_file(_Path(path)) is True

        with open(path, encoding="utf-8") as f:
            assert "[G7]" in f.read()

    def test_migrate_is_idempotent_on_already_canonical_file(self):
        path = self._path()
        with open(path, "w", encoding="utf-8") as f:
            f.write("chordpro: \"[G]song\"\n")
        # First call no-ops because the file is already ASCII.
        assert migration_module.migrate_chord_yaml_file(_Path(path)) is False
        # Repeated calls remain no-ops.
        assert migration_module.migrate_chord_yaml_file(_Path(path)) is False

    def test_migrate_writes_backup_when_requested(self):
        path = self._path()
        original = "chordpro: \"[G\u2077]song\"\n"
        with open(path, "w", encoding="utf-8") as f:
            f.write(original)

        assert (
            migration_module.migrate_chord_yaml_file(_Path(path), backup=True)
            is True
        )
        # ``.bak`` sibling exists with the original Unicode intact.
        backup_path = path + ".bak"
        assert os.path.exists(backup_path)
        with open(backup_path, encoding="utf-8") as f:
            assert f.read() == original
        with open(path, encoding="utf-8") as f:
            assert "[G7]" in f.read()

    def test_migrate_chord_yaml_files_returns_counts(self):
        path_a = self._path("a.yaml")
        path_b = self._path("b.yaml")
        path_c = self._path("c.yaml")
        with open(path_a, "w", encoding="utf-8") as f:
            f.write("chordpro: \"[G\u2077]changeme\"\n")
        with open(path_b, "w", encoding="utf-8") as f:
            f.write("chordpro: \"[G]already\"\n")
        # ``c.yaml`` does not exist; should be counted as error.

        stats = migration_module.migrate_chord_yaml_files(
            [_Path(path_a), _Path(path_b), _Path(path_c)]
        )
        assert stats == {"migrated": 1, "skipped": 1, "errors": 1}

    def test_has_legacy_chord_unicode_detects_only_inside_brackets(self):
        path = self._path()
        # Free-text Unicode outside brackets is *not* considered legacy
        # chord typography — we only react to chord bracket contents.
        with open(path, "w", encoding="utf-8") as f:
            f.write("lyrics: 'caf\u00e9'\nchordpro: \"[G]amo\"\n")
        assert migration_module.has_legacy_chord_unicode(_Path(path)) is False

        with open(path, "w", encoding="utf-8") as f:
            f.write("chordpro: \"[G\u2077]amo\"\n")
        assert migration_module.has_legacy_chord_unicode(_Path(path)) is True

    def test_default_song_yaml_paths_walks_data_songs(self):
        # Build a fake ``data/songs/<song>/<song>.yaml`` layout under a
        # temporary project root and assert the helper finds every file.
        project_root = Path(self.test_dir)
        songs_root = project_root / "data" / "songs"
        for song in ("alpha", "beta"):
            song_dir = songs_root / song
            song_dir.mkdir(parents=True)
            (song_dir / f"{song}.yaml").write_text("title: song\n", encoding="utf-8")
        # Top-level yaml that should be ignored (``<song>`` is required).
        (songs_root / "orphan.yaml").write_text("ignored\n", encoding="utf-8")

        paths = migration_module.default_song_yaml_paths(project_root)
        assert sorted(p.name for p in paths) == ["alpha.yaml", "beta.yaml"]


# Local alias so the test method bodies below stay short; ``_Path`` is the
# same class as :class:`pathlib.Path`, just prefixed to mirror private
# helpers used elsewhere in the suite.
_Path = Path
