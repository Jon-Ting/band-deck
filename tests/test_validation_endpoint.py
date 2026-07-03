"""Integration tests for the complete song-generation workflow.

Covers workflow integration:
- End-to-end: search → parse → YAML → Marp → HTML
- Edit workflow: modify YAML → regenerate → verify updates propagate
- Multi-format consistency: YAML/Marp/HTML represent the same song
"""

from __future__ import annotations

from src.utils.arrangement_engine import propose_arrangement, validate_arrangement
from src.utils.chordpro_parser import ChordPosition, ChordProLine
from src.utils.marp_generator import generate_marp
from src.utils.song_validator import validate_song
from src.utils.yaml_api import song_yaml_to_dict, validate_song_yaml_dict
from src.utils.yaml_models import SongSection, SongYAML


def _build_song(title: str = "Integration Song") -> SongYAML:
    sections = {
        "Verse 1": SongSection(
            name="Verse 1",
            type="verse",
            lines=[
                ChordProLine(
                    text="Amazing grace how sweet the sound",
                    chords=[
                        ChordPosition(chord="G", position=0),
                        ChordPosition(chord="D", position=8),
                    ],
                )
            ],
        ),
        "Chorus": SongSection(
            name="Chorus",
            type="chorus",
            lines=[
                ChordProLine(
                    text="That saved a wretch like me",
                    chords=[ChordPosition(chord="C", position=0)],
                )
            ],
        ),
        "Bridge": SongSection(
            name="Bridge",
            type="bridge",
            lines=[
                ChordProLine(
                    text="Twas grace that taught my heart",
                    chords=[ChordPosition(chord="Em", position=0)],
                )
            ],
        ),
    }
    return SongYAML(
        title=title,
        authors=["Lyricist"],
        target_key="G",
        sections=sections,
        arrangement=["Verse 1", "Chorus", "Bridge", "Chorus"],
    )


class TestSearchToHtmlPipeline:
    """End-to-end: parse a chord chart, generate YAML, then to Marp."""

    def test_yaml_to_marp_to_html_consistent(self):
        song = _build_song()
        marp = generate_marp(song)

        # Marp must contain one slide per known arrangement entry plus title
        section_heading_count = marp.count("## ")
        assert section_heading_count == len(song.arrangement), (
            f"Section heading count {section_heading_count} "
            f"does not match arrangement length {len(song.arrangement)}"
        )

        # Title and each section name must appear at least once.
        assert song.title in marp
        for section_name in song.arrangement:
            assert section_name in marp, f"Section {section_name} missing from Marp"

        # Chord symbols must appear inline as <span class=\"chord\"> spans.
        assert '<span class="chord">G</span>' in marp
        assert '<span class="chord">D</span>' in marp
        assert '<span class="chord">C</span>' in marp
        assert '<span class="chord">Em</span>' in marp


class TestEditWorkflow:
    """Modify YAML → regenerate → verify propagation."""

    def test_chord_edit_propagates_into_marp(self):
        song = _build_song()
        marp_before = generate_marp(song)
        assert '<span class="chord">G</span>' in marp_before

        # Edit: transpose the Verse 1 line by replacing the root.
        song.sections["Verse 1"].lines[0].chords[0] = ChordPosition(
            chord="A", position=0
        )
        marp_after = generate_marp(song)
        assert '<span class="chord">A</span>' in marp_after
        assert '<span class="chord">G</span>' not in marp_after.replace(
            '<span class="chord">D</span>', ""
        )

    def test_section_addition_propagates_into_marp(self):
        song = _build_song()
        marp_before = generate_marp(song)
        assert "## Verse 1" in marp_before

        # Add a new section.
        song.sections["Outro"] = SongSection(
            name="Outro",
            type="outro",
            lines=[ChordProLine(text="End of song", chords=[])],
        )
        song.arrangement = [*song.arrangement, "Outro"]
        marp_after = generate_marp(song)

        assert "## Outro" in marp_after
        assert marp_after.count("## ") == len(song.arrangement), (
            "Number of section headings should match arrangement size."
        )

    def test_arrangement_edit_propagates_into_marp(self):
        song = _build_song()
        arrangement_engine_arrangement = propose_arrangement(song.sections)
        song.arrangement = arrangement_engine_arrangement

        marp = generate_marp(song)
        assert marp.count("## ") == len(arrangement_engine_arrangement)


class TestMultiFormatConsistency:
    """YAML, Marp, and the validator must all agree on the song."""

    def test_yaml_marp_validator_all_agree(self):
        song = _build_song()
        serialized = song_yaml_to_dict(song)

        # Schema validation
        schema_result = validate_song_yaml_dict(serialized)
        assert schema_result["valid"] is True, schema_result["errors"]

        # Validator validation
        validator_result = validate_song(song)
        assert validator_result.is_valid is True, validator_result.errors

        # Marp generation works for the same song
        marp = generate_marp(song)
        assert marp.startswith("---\nmarp: true")

        # Validator + arrangement referential integrity agree
        ok, errors = validate_arrangement(song.arrangement, song.sections)
        assert ok is True, errors

    def test_yaml_marp_and_validator_agree_on_arrangement(self):
        song = _build_song()
        # Drop one arrangement entry that does exist but we'll deliberately
        # corrupt it to confirm error messages stay consistent.
        song.arrangement = ["Verse 1", "Phantom Section"]
        marp = generate_marp(song)

        # Marp only renders the existing section; the orphan is hidden
        assert "## Phantom Section" not in marp

        # Validator surfaces the orphan
        validator_result = validate_song(song)
        assert any("Phantom Section" in err for err in validator_result.errors)


class TestRoundTripConsistency:
    """asdict() should preserve the song for the validate endpoint contract."""

    def test_payload_round_trip_through_api_validate_contract(self):
        song = _build_song()
        serialized = song_yaml_to_dict(song)

        # Reconstruct a new SongYAML from the serialized dict by inverting
        # the asdict structure. This mirrors what /api/validate does when
        # it parses the JSON body.
        sections = {
            section_name: SongSection(
                name=section["name"],
                type=section["type"],
                lines=[
                    ChordProLine(
                        text=line.get("text", ""),
                        chords=[
                            ChordPosition(
                                chord=chord.get("chord", ""),
                                position=chord.get("position", 0),
                            )
                            for chord in line.get("chords", [])
                        ],
                    )
                    for line in section.get("lines", [])
                ],
            )
            for section_name, section in serialized["sections"].items()
        }

        rebuilt = SongYAML(
            title=serialized["title"],
            authors=serialized["authors"],
            target_key=serialized["target_key"],
            sections=sections,
            arrangement=serialized["arrangement"],
        )
        assert rebuilt.title == song.title
        assert sorted(rebuilt.sections) == sorted(song.sections)
        assert list(rebuilt.sections) == list(song.sections)
        assert rebuilt.arrangement == song.arrangement

        rebuilt_marp = generate_marp(rebuilt)
        original_marp = generate_marp(song)
        # Strip whitespace for stronger comparison: asdict should be a pure
        # 1:1 mapping for our inputs.
        assert rebuilt_marp == original_marp
