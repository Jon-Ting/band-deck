"""Fixture integrity checks for curated song input YAML files."""

from pathlib import Path

import yaml

from src.utils.preview import _song_from_payload
from src.utils.song_validator import validate_song


def test_song_input_yaml_arrangements_reference_existing_sections() -> None:
    fixture_paths = sorted(Path("data/songs").glob("*/*.input.yaml"))
    assert fixture_paths, "Expected curated song input YAML fixtures under data/songs/"

    failures: list[str] = []
    for fixture_path in fixture_paths:
        payload = yaml.safe_load(fixture_path.read_text(encoding="utf-8"))
        song = _song_from_payload(payload)
        validation = validate_song(song)
        integrity_errors = [
            error for error in validation.errors if "non-existent section" in error
        ]
        if integrity_errors:
            failures.append(f"{fixture_path}: {integrity_errors}")

    assert failures == [], "\n".join(failures)
