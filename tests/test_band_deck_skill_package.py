"""Checks for the portable band-deck skill package."""

import os
import subprocess
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "band-deck-slide-generator"


REQUIRED_ARCHITECTURE_FILES = [
    "schema/song-deck.schema.yaml",
    "docs/source-and-copyright.md",
    "docs/workflow.md",
    "docs/validation-checklist.md",
    "docs/arrangement-rules.md",
    "docs/chordpro-normalisation.md",
    "docs/marp-style-guide.md",
    "scripts/band_deck_helpers.py",
    "scripts/yaml_to_marp.py",
    "scripts/validate_deck.py",
    "scripts/regenerate_outputs.py",
    "scripts/render_marp.sh",
    "templates/practice-deck.marp.md",
]


def test_skill_package_exposes_requested_architecture_files() -> None:
    missing = [
        relative_path
        for relative_path in REQUIRED_ARCHITECTURE_FILES
        if not (SKILL_DIR / relative_path).is_file()
    ]

    assert missing == []


def test_song_deck_schema_documents_canonical_pipeline_modules() -> None:
    schema = yaml.safe_load((SKILL_DIR / "schema/song-deck.schema.yaml").read_text())

    properties = set(schema["properties"])
    assert {
        "request",
        "metadata",
        "sources",
        "normalised_chordpro",
        "arrangement",
        "deck",
        "validation",
    }.issubset(properties)


def test_skill_requires_exact_lyric_text_preservation() -> None:
    skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    docs = (SKILL_DIR / "docs/source-and-copyright.md").read_text(encoding="utf-8")

    assert "Render lyric text exactly as supplied" in skill or (
        "Render lyric text exactly as supplied" in docs
    )


def test_skill_documents_chord_and_repetition_superscripts() -> None:
    skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    chordpro_docs = (
        SKILL_DIR / "docs/chordpro-normalisation.md"
    ).read_text(encoding="utf-8")

    assert "superscript" in skill.lower()
    assert "1st" in chordpro_docs
    assert "1ˢᵗ" in chordpro_docs


def test_validate_deck_accepts_minimal_canonical_yaml(tmp_path: Path) -> None:
    deck_yaml = tmp_path / "deck.yaml"
    deck_yaml.write_text(
        """
request:
  title: Example Song
metadata:
  title: Example Song
  authors:
    - Example Writer
  target_key: G
  bpm: unknown
  time_signature: 4/4
sources:
  metadata:
    - label: user supplied
      url: null
  lyrics_chords:
    - label: user supplied
      url: null
normalised_chordpro:
  sections:
    Verse 1:
      type: verse
      lines:
        - chordpro: "[G]<licensed lyric line>"
arrangement:
  sequence:
    - section: Verse 1
deck:
  output_formats:
    - marp
  slides:
    include_overview: true
validation:
  human_review_required:
    - verify licensed lyrics before use
""".lstrip(),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SKILL_DIR / "scripts/validate_deck.py"),
            str(deck_yaml),
            "--schema",
            str(SKILL_DIR / "schema/song-deck.schema.yaml"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "valid" in result.stdout.lower()


def test_yaml_to_marp_generates_practice_deck(tmp_path: Path) -> None:
    deck_yaml = tmp_path / "deck.yaml"
    marp_path = tmp_path / "deck.marp.md"
    deck_yaml.write_text(
        """
request:
  title: Example Song
metadata:
  title: Example Song
  authors:
    - Example Writer
  target_key: G
  bpm: 72
  time_signature: 4/4
  capo: none
sources:
  metadata:
    - label: user supplied
      url: null
  lyrics_chords:
    - label: user supplied
      url: null
normalised_chordpro:
  sections:
    Verse 1:
      type: verse
      lines:
        - chordpro: "[G]<licensed lyric line>"
arrangement:
  sequence:
    - section: Verse 1
deck:
  output_formats:
    - marp
  slides:
    include_overview: true
validation:
  human_review_required:
    - verify licensed lyrics before use
""".lstrip(),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SKILL_DIR / "scripts/yaml_to_marp.py"),
            str(deck_yaml),
            "--output",
            str(marp_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    marp = marp_path.read_text(encoding="utf-8")
    assert marp.startswith("---\nmarp: true")
    assert "# Example Song" in marp
    assert "## Verse 1" in marp
    assert '<div class="chord-line">G</div>' in marp


def test_yaml_to_marp_defaults_to_neighboring_marp_file(tmp_path: Path) -> None:
    deck_yaml = tmp_path / "deck.yaml"
    marp_path = tmp_path / "deck.marp.md"
    deck_yaml.write_text(
        """
request:
  title: Example Song
metadata:
  title: Example Song
  authors:
    - Example Writer
  target_key: G
  bpm: 72
  time_signature: 4/4
  capo: none
sources:
  metadata:
    - label: user supplied
      url: null
  lyrics_chords:
    - label: user supplied
      url: null
normalised_chordpro:
  sections:
    Verse 1:
      type: verse
      lines:
        - chordpro: "[G]<licensed lyric line>"
arrangement:
  sequence:
    - section: Verse 1
deck:
  output_formats:
    - marp
validation:
  human_review_required:
    - verify licensed lyrics before use
""".lstrip(),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SKILL_DIR / "scripts/yaml_to_marp.py"),
            str(deck_yaml),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == f"wrote: {marp_path}\n"
    marp = marp_path.read_text(encoding="utf-8")
    assert marp.startswith("---\nmarp: true")
    assert "# Example Song" in marp


def test_yaml_to_marp_dry_run_without_output_does_not_write_files(
    tmp_path: Path,
) -> None:
    deck_yaml = tmp_path / "deck.yaml"
    marp_path = tmp_path / "deck.marp.md"
    deck_yaml.write_text(
        """
request:
  title: Example Song
metadata:
  title: Example Song
  authors:
    - Example Writer
  target_key: G
  bpm: 72
  time_signature: 4/4
  capo: none
sources:
  metadata:
    - label: user supplied
      url: null
  lyrics_chords:
    - label: user supplied
      url: null
normalised_chordpro:
  sections:
    Verse 1:
      type: verse
      lines:
        - chordpro: "[G]<licensed lyric line>"
arrangement:
  sequence:
    - section: Verse 1
deck:
  output_formats:
    - marp
validation:
  human_review_required:
    - verify licensed lyrics before use
""".lstrip(),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SKILL_DIR / "scripts/yaml_to_marp.py"),
            str(deck_yaml),
            "--to-key",
            "A",
            "--dry-run",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert not marp_path.exists()
    assert "# Example Song" in result.stdout
    assert "--- transposed yaml (dry run) ---" in result.stdout


def test_regenerate_outputs_renders_marp_and_html(tmp_path: Path) -> None:
    deck_yaml = tmp_path / "deck.yaml"
    marp_path = tmp_path / "deck.marp.md"
    html_path = tmp_path / "deck.html"
    calls_path = tmp_path / "marp-calls.txt"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_marp = fake_bin / "marp"
    fake_marp.write_text(
        """#!/usr/bin/env python3
import pathlib
import sys

pathlib.Path(sys.argv[-1]).write_text("<html>Rendered</html>", encoding="utf-8")
calls = pathlib.Path(__file__).parents[1] / "marp-calls.txt"
calls.write_text(" ".join(sys.argv[1:]), encoding="utf-8")
""",
        encoding="utf-8",
    )
    fake_marp.chmod(0o755)
    deck_yaml.write_text(
        """
request:
  title: Example Song
metadata:
  title: Example Song
  authors:
    - Example Writer
  target_key: G
  bpm: 72
  time_signature: 4/4
  capo: none
sources:
  metadata:
    - label: user supplied
      url: null
  lyrics_chords:
    - label: user supplied
      url: null
normalised_chordpro:
  sections:
    Verse 1:
      type: verse
      lines:
        - chordpro: "[G]<licensed lyric line>"
arrangement:
  sequence:
    - section: Verse 1
deck:
  output_formats:
    - marp
    - html
validation:
  human_review_required:
    - verify licensed lyrics before use
""".lstrip(),
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    result = subprocess.run(
        [
            sys.executable,
            str(SKILL_DIR / "scripts/regenerate_outputs.py"),
            str(deck_yaml),
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert marp_path.exists()
    assert html_path.read_text(encoding="utf-8") == "<html>Rendered</html>"
    marp_call = calls_path.read_text(encoding="utf-8")
    assert "--html" in marp_call
    assert str(marp_path) in marp_call
    assert str(html_path) in marp_call
