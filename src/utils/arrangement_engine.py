"""Arrangement engine for creating and managing song maps.

Provides functions to propose default arrangements based on section types,
validate arrangement integrity, and update arrangements with reorder/repeat/insert operations.
Validates: Requirements 6.1, 6.2, 6.7
"""

import logging
import re
from dataclasses import dataclass

from src.utils.yaml_models import SongSection

logger = logging.getLogger(__name__)


@dataclass
class ArrangementEdit:
    """Represents a single edit operation on an arrangement."""

    operation: str  # "reorder", "repeat", "insert", "delete"
    section_name: str
    target_position: int | None = None
    repeat_count: int | None = None


def propose_arrangement(sections: dict[str, SongSection]) -> list[str]:
    """Generate default arrangement based on section types.

    Creates a standard song arrangement following common worship song structure:
    - Instrumental intro sections first
    - Verses in numerical order
    - Chorus after each verse (if present)
    - Bridge sections after verses
    - Final chorus repetition (if chorus exists)
    - Outro/ending sections last

    Args:
        sections: Dictionary mapping section names to SongSection objects

    Returns:
        Ordered list of section names representing the proposed arrangement
    """
    logger.debug(f"Proposing arrangement for {len(sections)} sections")

    # Categorize sections by type
    intros: list[str] = []
    verses: list[str] = []
    choruses: list[str] = []
    bridges: list[str] = []
    outros: list[str] = []
    interludes: list[str] = []
    other: list[str] = []

    for name, section in sections.items():
        section_type = section.type.lower()

        if section_type in ("intro", "instrumental"):
            intros.append(name)
        elif section_type == "verse":
            verses.append(name)
        elif section_type == "chorus":
            choruses.append(name)
        elif section_type == "bridge":
            bridges.append(name)
        elif section_type in ("outro", "ending"):
            outros.append(name)
        elif section_type == "interlude":
            interludes.append(name)
        else:
            other.append(name)

    # Sort verses numerically if possible
    verses.sort(key=_extract_verse_number)

    # Build arrangement
    arrangement: list[str] = []

    # Start with intro sections
    arrangement.extend(intros)

    # Add verses with chorus after each (if chorus exists)
    has_chorus = len(choruses) > 0
    for verse in verses:
        arrangement.append(verse)
        if has_chorus:
            arrangement.append(choruses[0])

    # Add bridges with chorus after each
    for bridge in bridges:
        arrangement.append(bridge)
        if has_chorus:
            arrangement.append(choruses[0])

    # If we have a chorus, repeat it at the end (common pattern)
    if has_chorus and len(arrangement) > 0:
        arrangement.append(choruses[0])

    # Add any interludes
    arrangement.extend(interludes)

    # Add outros
    arrangement.extend(outros)

    # Add any other sections we couldn't categorize
    arrangement.extend(other)

    logger.debug(f"Proposed arrangement with {len(arrangement)} items: {arrangement}")
    return arrangement


def _extract_verse_number(section_name: str) -> int:
    """Extract numeric portion from section name for sorting.

    Args:
        section_name: Section name like "Verse 1", "Verse 2", "V3", etc.

    Returns:
        Numeric value for sorting (defaults to 999 if no number found)
    """
    match = re.search(r"\d+", section_name)
    return int(match.group()) if match else 999


def validate_arrangement(
    arrangement: list[str], sections: dict[str, SongSection]
) -> tuple[bool, list[str]]:
    """Verify all arrangement items reference existing sections.

    Checks that every section name in the arrangement exists in the sections dictionary.
    Returns validation status and list of error messages for any invalid references.

    Args:
        arrangement: Ordered list of section names
        sections: Dictionary of available sections

    Returns:
        Tuple of (is_valid, error_messages) where is_valid is True if all
        arrangement items reference existing sections, and error_messages
        contains descriptions of any invalid references
    """
    logger.debug(f"Validating arrangement with {len(arrangement)} items")

    errors: list[str] = []
    section_names = set(sections.keys())

    for idx, section_name in enumerate(arrangement):
        if section_name not in section_names:
            error_msg = (
                f"Arrangement item at position {idx} references non-existent "
                f"section '{section_name}'"
            )
            errors.append(error_msg)
            logger.warning(error_msg)

    is_valid = len(errors) == 0

    if is_valid:
        logger.info("Arrangement validation passed")
    else:
        logger.error(f"Arrangement validation failed with {len(errors)} errors")

    return is_valid, errors


def update_arrangement(
    current: list[str], modification: ArrangementEdit
) -> list[str]:
    """Apply reorder/repeat/insert/delete operations to arrangement.

    Modifies the arrangement based on the specified operation:
    - reorder: Move section to target_position
    - repeat: Duplicate section at target_position (or after current position)
    - insert: Add section at target_position
    - delete: Remove first occurrence of section

    Args:
        current: Current arrangement list
        modification: ArrangementEdit specifying the operation

    Returns:
        New arrangement list with modification applied

    Raises:
        ValueError: If operation is invalid or required parameters are missing
    """
    logger.debug(
        f"Updating arrangement with operation '{modification.operation}' "
        f"on section '{modification.section_name}'"
    )

    # Create a copy to avoid mutating the input
    updated = current.copy()

    operation = modification.operation.lower()
    section_name = modification.section_name

    if operation == "reorder":
        if modification.target_position is None:
            raise ValueError("reorder operation requires target_position")

        # Remove section from current position (first occurrence)
        if section_name not in updated:
            raise ValueError(f"Section '{section_name}' not found in arrangement")

        current_idx = updated.index(section_name)
        updated.pop(current_idx)

        # Insert at target position
        target_pos = modification.target_position
        # Clamp to valid range
        target_pos = max(0, min(target_pos, len(updated)))
        updated.insert(target_pos, section_name)

        logger.info(
            f"Reordered '{section_name}' from position {current_idx} to {target_pos}"
        )

    elif operation == "repeat":
        # Find the section to repeat
        if section_name not in updated:
            raise ValueError(f"Section '{section_name}' not found in arrangement")

        current_idx = updated.index(section_name)

        # Determine insertion position
        if modification.target_position is not None:
            insert_pos = modification.target_position
        else:
            # Default: insert after the current position
            insert_pos = current_idx + 1

        # Clamp to valid range
        insert_pos = max(0, min(insert_pos, len(updated)))

        # Determine repeat count: None defaults to 1, otherwise must be a positive integer
        repeat_count = (
            1 if modification.repeat_count is None else modification.repeat_count
        )
        if repeat_count < 1:
            raise ValueError(
                f"repeat_count must be a positive integer, got {repeat_count}"
            )

        # Insert repeats
        for i in range(repeat_count):
            updated.insert(insert_pos + i, section_name)

        logger.info(
            f"Repeated '{section_name}' {repeat_count} time(s) at position {insert_pos}"
        )

    elif operation == "insert":
        if modification.target_position is None:
            raise ValueError("insert operation requires target_position")

        target_pos = modification.target_position
        # Clamp to valid range
        target_pos = max(0, min(target_pos, len(updated)))

        updated.insert(target_pos, section_name)
        logger.info(f"Inserted '{section_name}' at position {target_pos}")

    elif operation == "delete":
        if section_name not in updated:
            raise ValueError(f"Section '{section_name}' not found in arrangement")

        # Remove first occurrence
        updated.remove(section_name)
        logger.info(f"Deleted first occurrence of '{section_name}'")

    else:
        raise ValueError(
            f"Unknown operation '{operation}'. "
            "Valid operations: reorder, repeat, insert, delete"
        )

    logger.debug(f"Updated arrangement: {updated}")
    return updated
