"""YAML data models for song representation in band-deck.

Defines structured dataclasses for representing songs in YAML/JSON format,
including metadata, sections with ChordPro-formatted lyrics, and arrangement.
"""

import logging
from dataclasses import dataclass, field

from src.utils.chordpro_parser import ChordProLine

logger = logging.getLogger(__name__)


@dataclass
class SongMetadata:
    """Metadata about a song (searchable, displayable properties)."""

    title: str
    authors: list[str]
    ccli_number: str | None = None
    copyright: str | None = None
    original_key: str | None = None
    bpm: int | None = None
    time_signature: str | None = None
    source_urls: list[str] = field(default_factory=list)


@dataclass
class SongSection:
    """A named section of a song (verse, chorus, bridge, etc.)."""

    name: str
    type: str  # "verse", "chorus", "bridge", "instrumental", "intro", "outro", "interlude"
    lines: list[ChordProLine]
    repeat: int = 1
    notes: list[str] | None = None


@dataclass
class SongYAML:
    """Complete structured representation of a song in YAML/JSON format.

    Serves as the single source of truth for song data throughout the pipeline.
    Contains metadata, sections with ChordPro formatting, and arrangement sequence.
    """

    title: str
    authors: list[str]
    ccli_number: str | None = None
    copyright: str | None = None
    original_key: str | None = None
    target_key: str = "C"
    bpm: int | None = None
    time_signature: str | None = None
    capo: str | None = None
    sections: dict[str, SongSection] = field(default_factory=dict)
    arrangement: list[str] = field(default_factory=list)
    practice_notes: dict[str, list[str]] | None = None
    source_urls: list[str] = field(default_factory=list)
