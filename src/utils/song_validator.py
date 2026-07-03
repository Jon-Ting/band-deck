"""Song validation module for completeness and correctness checks.

Validates song data including arrangement references, chord symbols, section labels,
metadata completeness, licensing information, and slide overflow estimation.
"""

import logging
import re
from dataclasses import dataclass

from src.utils.yaml_models import SongYAML

logger = logging.getLogger(__name__)

# Chord symbol pattern matching valid chord notation
CHORD_PATTERN = re.compile(
    r"^[A-G][b#]?"
    r"(?:(?:m(?![a-z])|maj|min|dim|aug|sus[24]?|add[0-9]+|[0-9]+|b[0-9]+|#[0-9]+))*"
    r"(?:/[A-G][b#]?)?$"
)

# Placeholder patterns to detect incomplete content
PLACEHOLDER_PATTERNS = [
    re.compile(r"\[.*placeholder.*\]", re.IGNORECASE),
    re.compile(r"\{.*\}", re.IGNORECASE),
    re.compile(r"TODO", re.IGNORECASE),
    re.compile(r"TBD", re.IGNORECASE),
    re.compile(r"XXX", re.IGNORECASE),
]


@dataclass
class ValidationResult:
    """Result of song validation containing errors and warnings."""

    is_valid: bool
    errors: list[str]
    warnings: list[str]


@dataclass
class OverflowWarning:
    """Warning about potential slide content overflow."""

    section_name: str
    estimated_lines: int
    max_lines: int
    suggestion: str


def validate_song(song: SongYAML, check_placeholders: bool = False) -> ValidationResult:
    """Validate song data completeness, chord symbols, arrangement references.

    Checks:
    - All arrangement items reference existing sections
    - All chord symbols are valid
    - All sections have clear labels
    - Metadata fields are complete
    - Optional placeholder text detection

    Args:
        song: The SongYAML to validate
        check_placeholders: Whether to check for unresolved placeholder text

    Returns:
        ValidationResult with is_valid flag, errors list, and warnings list
    """
    errors: list[str] = []
    warnings: list[str] = []

    logger.debug(f"Validating song: {song.title}")

    # Verify all arrangement items reference existing sections
    for arrangement_item in song.arrangement:
        if arrangement_item not in song.sections:
            errors.append(
                f"Arrangement references non-existent section: '{arrangement_item}'"
            )
            logger.warning(f"Invalid arrangement reference: {arrangement_item}")

    # Verify all chord symbols are valid
    for section_name, section in song.sections.items():
        for line_idx, line in enumerate(section.lines):
            for chord_pos in line.chords:
                if not is_valid_chord(chord_pos.chord):
                    errors.append(
                        f"Invalid chord symbol '{chord_pos.chord}' in section '{section_name}', line {line_idx + 1}"
                    )
                    logger.warning(
                        f"Invalid chord: {chord_pos.chord} in {section_name}"
                    )

    # Verify all sections have clear labels
    for section_name, section in song.sections.items():
        if not section_name or not section_name.strip():
            errors.append(f"Section has empty or missing label: {section}")
            logger.warning("Found section with empty label")

        if not section.name or not section.name.strip():
            errors.append(
                f"Section '{section_name}' has empty name property: {section.name}"
            )
            logger.warning(f"Section {section_name} has empty name property")

    # Verify metadata fields are complete
    if not song.title or not song.title.strip():
        errors.append("Song title is missing or empty")
        logger.warning("Missing song title")

    if not song.authors or all(not author.strip() for author in song.authors):
        warnings.append("Song authors list is missing or empty")
        logger.info("Missing song authors")

    if not song.target_key or not song.target_key.strip():
        warnings.append("Target key is missing or empty")
        logger.info("Missing target key")

    # Optional placeholder text checking
    if check_placeholders:
        placeholder_issues = check_for_placeholders(song)
        if placeholder_issues:
            errors.extend(placeholder_issues)
            logger.warning(f"Found {len(placeholder_issues)} placeholder issues")

    is_valid = len(errors) == 0
    logger.debug(
        f"Validation complete: is_valid={is_valid}, errors={len(errors)}, warnings={len(warnings)}"
    )

    return ValidationResult(is_valid=is_valid, errors=errors, warnings=warnings)


def is_valid_chord(chord: str) -> bool:
    """Check if a chord symbol is valid.

    Valid chords match pattern: [A-G][b#]?[modifiers]*[/bass]?
    Examples: G, Bm, C/G, Dmaj7, Asus4, Cadd9

    Args:
        chord: The chord symbol to validate

    Returns:
        True if the chord is valid, False otherwise
    """
    if not chord or not chord.strip():
        return False

    return CHORD_PATTERN.match(chord.strip()) is not None


def check_for_placeholders(song: SongYAML) -> list[str]:
    """Check for unresolved placeholder text in song data.

    Detects patterns like [placeholder], {value}, TODO, TBD, XXX.

    Args:
        song: The SongYAML to check

    Returns:
        List of error messages for each placeholder found
    """
    issues: list[str] = []

    # Check title
    if contains_placeholder(song.title):
        issues.append(f"Placeholder detected in title: '{song.title}'")

    # Check authors
    for author in song.authors:
        if contains_placeholder(author):
            issues.append(f"Placeholder detected in author: '{author}'")

    # Check copyright
    if song.copyright and contains_placeholder(song.copyright):
        issues.append(f"Placeholder detected in copyright: '{song.copyright}'")

    # Check sections
    for section_name, section in song.sections.items():
        if contains_placeholder(section_name):
            issues.append(f"Placeholder detected in section name: '{section_name}'")

        for line_idx, line in enumerate(section.lines):
            if contains_placeholder(line.text):
                issues.append(
                    f"Placeholder detected in section '{section_name}', line {line_idx + 1}: '{line.text}'"
                )

    return issues


def contains_placeholder(text: str) -> bool:
    """Check if text contains placeholder patterns.

    Args:
        text: The text to check

    Returns:
        True if any placeholder pattern is found
    """
    if not text:
        return False

    for pattern in PLACEHOLDER_PATTERNS:
        if pattern.search(text):
            return True

    return False


def estimate_slide_overflow(song: SongYAML, style: str) -> list[OverflowWarning]:
    """Estimate if any slides will overflow based on content length.

    Different styles have different capacity:
    - practice: ~12 lines (includes metadata and song map)
    - performance: ~16 lines (minimal metadata)
    - simple: ~18 lines (no extras)

    Args:
        song: The SongYAML to check
        style: The slide style ("practice", "performance", or "simple")

    Returns:
        List of OverflowWarning for sections that may overflow
    """
    warnings: list[OverflowWarning] = []

    # Define max lines per style
    max_lines_by_style = {
        "practice": 12,
        "performance": 16,
        "simple": 18,
    }

    max_lines = max_lines_by_style.get(style, 12)

    logger.debug(f"Estimating overflow for style '{style}' (max {max_lines} lines)")

    for section_name in song.arrangement:
        if section_name not in song.sections:
            # Skip invalid references (handled by validate_song)
            continue

        section = song.sections[section_name]
        line_count = len(section.lines)

        # Add extra lines for section notes if present
        if section.notes:
            line_count += len(section.notes)

        if line_count > max_lines:
            suggestion = _generate_overflow_suggestion(section_name, line_count, max_lines)
            warnings.append(
                OverflowWarning(
                    section_name=section_name,
                    estimated_lines=line_count,
                    max_lines=max_lines,
                    suggestion=suggestion,
                )
            )
            logger.info(
                f"Overflow warning: {section_name} has {line_count} lines (max {max_lines})"
            )

    return warnings


def _generate_overflow_suggestion(
    section_name: str, estimated_lines: int, max_lines: int
) -> str:
    """Generate a helpful suggestion for handling overflow.

    Args:
        section_name: Name of the overflowing section
        estimated_lines: Number of lines in the section
        max_lines: Maximum recommended lines

    Returns:
        Suggestion string
    """
    excess = estimated_lines - max_lines

    if excess <= 3:
        return "Consider slightly reducing font size or removing non-essential notes"
    elif excess <= 6:
        return f"Consider splitting '{section_name}' into two slides (e.g., '{section_name} (1)' and '{section_name} (2)')"
    else:
        return f"Strongly recommend splitting '{section_name}' into multiple slides or reducing content significantly"


def check_licensing(song: SongYAML) -> list[str]:
    """Return licensing warnings if information incomplete.

    Checks for:
    - Missing license number
    - Incomplete copyright information
    - License permission reminder

    Args:
        song: The SongYAML to check

    Returns:
        List of warning messages about licensing
    """
    warnings: list[str] = []

    logger.debug(f"Checking licensing for song: {song.title}")

    # Missing license number warning
    if not song.license_number or not song.license_number.strip():
        warnings.append(
            "License number is missing. Please verify licensing information before use."
        )
        logger.info("Missing license number")

    # Incomplete copyright warning
    if not song.copyright or not song.copyright.strip():
        warnings.append(
            "Copyright information is incomplete. Please add copyright details."
        )
        logger.info("Missing copyright information")

    # Permission reminder (always included)
    warnings.append(
        "Reminder: Please verify that you have permission to use this song before use."
    )

    return warnings
