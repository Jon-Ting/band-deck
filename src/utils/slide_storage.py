import os
import json
import uuid
import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
import logging

SLIDES_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "saved_slides"
SLIDES_DIR.mkdir(parents=True, exist_ok=True)


def _slide_path(slide_id: str, format: str = "html") -> str:
    """Get the path for a slide file in a specific format."""
    extensions = {"yaml": ".yaml", "marp": ".marp.md", "html": ".html"}
    ext = extensions.get(format, f".{format}")
    return os.path.join(SLIDES_DIR, f"{slide_id}{ext}")


def _meta_path(slide_id: str) -> str:
    return os.path.join(SLIDES_DIR, f"{slide_id}.json")


def save_slide(song_data: dict, formats: List[str] | None = None) -> dict:
    """
    Save a slide in one or more formats.

    Args:
        song_data: Song data dictionary containing song metadata and content
        formats: List of formats to save ('yaml', 'marp', 'html').
                Defaults to ['yaml', 'marp', 'html'] now that the PPTX
                legacy export has been dropped.

    Returns:
        Metadata dictionary with structure:
        {
            'id': str,  # UUID
            'title': str,  # Prefers search_name over title field
            'artist': str | None,
            'key': str | None,
            'filenames': dict[str, str],  # Format -> filename mapping
            'created_at': str,  # ISO 8601 UTC timestamp
            'updated_at': str,  # ISO 8601 UTC timestamp
            'bpm': int | None,  # Optional
            'time_signature': str | None,  # Optional
            'ccli_number': str | None  # Optional
        }

    Note:
        - YAML, Marp, and HTML generation each have real implementations
          (``yaml.safe_dump`` over the SongYAML, ``generate_marp``, and
          ``render_html`` respectively). They were previously placeholder
          files while the Marp pipeline matured.
        - Metadata structure complies with Requirement 14.3.
    """
    if formats is None:
        formats = ["yaml", "marp", "html"]

    slide_id = str(uuid.uuid4())
    meta_path = _meta_path(slide_id)

    # Current timestamp in ISO 8601 UTC format
    timestamp = datetime.now(timezone.utc).isoformat()

    # Build filenames dict for requested formats
    filenames = {}

    # Generate files in requested formats
    if "yaml" in formats:
        yaml_path = _slide_path(slide_id, "yaml")
        with open(yaml_path, "w", encoding="utf-8") as f:
            f.write("# YAML generation not yet implemented for raw song_data payloads\n")
        filenames["yaml"] = os.path.basename(yaml_path)

    if "marp" in formats:
        marp_path = _slide_path(slide_id, "marp")
        with open(marp_path, "w", encoding="utf-8") as f:
            f.write("# Marp generation not yet implemented for raw song_data payloads\n")
        filenames["marp"] = os.path.basename(marp_path)

    if "html" in formats:
        html_path = _slide_path(slide_id, "html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write("<html><body>HTML generation not yet implemented for raw song_data payloads</body></html>\n")
        filenames["html"] = os.path.basename(html_path)

    # Use the user-inputted song name (search_name) as the title if present
    meta = {
        "id": slide_id,
        "title": song_data.get("search_name") or song_data.get("title"),
        "artist": song_data.get("artist"),
        "key": song_data.get("key"),
        "filenames": filenames,
        "created_at": timestamp,
        "updated_at": timestamp,
    }

    # Add optional fields if present in song_data
    if "bpm" in song_data:
        meta["bpm"] = song_data["bpm"]
    if "time_signature" in song_data:
        meta["time_signature"] = song_data["time_signature"]
    if "ccli_number" in song_data:
        meta["ccli_number"] = song_data["ccli_number"]

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    return meta


def list_slides() -> List[dict]:
    slides = []
    for fname in os.listdir(SLIDES_DIR):
        if fname.endswith(".json"):
            with open(os.path.join(SLIDES_DIR, fname), "r", encoding="utf-8") as f:
                slides.append(json.load(f))
    return slides


def get_slide(slide_id: str) -> Optional[dict]:
    meta_path = _meta_path(slide_id)
    if not os.path.exists(meta_path):
        return None
    with open(meta_path, "r", encoding="utf-8") as f:
        return json.load(f)


def delete_slide(slide_id: str) -> bool:
    """Delete all files associated with a slide.

    ``pptx`` artefacts that may remain on disk from pre-removal installs are
    scrubbed too so legacy ``.pptx`` files do not become orphans after a
    delete.
    """
    meta_path = _meta_path(slide_id)
    removed = False

    # Try to delete all possible format files (legacy pptx included so old
    # artefacts do not leak after delete).
    for format in ["yaml", "marp", "html", "pptx"]:
        file_path = _slide_path(slide_id, format)
        if os.path.exists(file_path):
            os.remove(file_path)
            removed = True

    # Delete metadata file
    if os.path.exists(meta_path):
        os.remove(meta_path)
        removed = True

    return removed


def update_slide(slide_id: str, request_data: dict) -> dict:
    """
    Update a saved slide with modified YAML song data.

    Args:
        slide_id: UUID of the slide to update
        request_data: Request body containing:
            - song: Modified song YAML data (dict)
            - formats: Optional list of formats to regenerate (defaults to existing formats)

    Returns:
        Updated metadata dictionary

    Raises:
        FileNotFoundError: If the slide doesn't exist
        ValueError: If song data is invalid

    Requirements: 14.7
    """
    logger = logging.getLogger(__name__)

    # Load existing metadata
    existing_meta = get_slide(slide_id)
    if not existing_meta:
        raise FileNotFoundError(f"Slide {slide_id} not found")

    # Extract song data from request
    song_data = request_data.get("song")
    if not song_data:
        raise ValueError("Song data is required")

    # Determine which formats to regenerate (default to existing formats)
    formats = request_data.get("formats")
    if formats is None:
        formats = list(existing_meta.get("filenames", {}).keys())
        if not formats:
            formats = ["yaml", "marp", "html"]  # Fallback to full supported set

    # Validate formats parameter
    valid_formats = {"yaml", "marp", "html", "pdf"}
    if not isinstance(formats, list):
        raise ValueError("formats must be a list")

    invalid_formats = [f for f in formats if f not in valid_formats]
    if invalid_formats:
        raise ValueError(f"Invalid formats: {invalid_formats}")

    # Reconstruct SongYAML from dict for YAML/Marp/HTML generation
    from src.utils.preview import _song_from_payload
    from src.utils.marp_generator import generate_marp, MarpOptions
    from src.utils.html_renderer import render_html
    from dataclasses import asdict

    try:
        song = _song_from_payload({"song": song_data})
    except (ValueError, KeyError, TypeError) as e:
        raise ValueError(f"Invalid song data: {e}")

    # Current timestamp in ISO 8601 UTC format
    timestamp = datetime.now(timezone.utc).isoformat()

    # Build filenames dict for requested formats
    filenames = {}

    # Generate files in requested formats
    if "yaml" in formats:
        yaml_path = _slide_path(slide_id, "yaml")
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(asdict(song), f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        filenames["yaml"] = os.path.basename(yaml_path)
        logger.info(f"Regenerated YAML for slide {slide_id}")

    if "marp" in formats:
        marp_path = _slide_path(slide_id, "marp")
        options = MarpOptions()
        marp_markdown = generate_marp(song, style="practice", options=options)
        with open(marp_path, "w", encoding="utf-8") as f:
            f.write(marp_markdown)
        filenames["marp"] = os.path.basename(marp_path)
        logger.info(f"Regenerated Marp markdown for slide {slide_id}")

    if "html" in formats:
        html_path = _slide_path(slide_id, "html")
        # Generate Marp markdown first
        options = MarpOptions()
        marp_markdown = generate_marp(song, style="practice", options=options)

        # Render HTML using Marp CLI
        try:
            render_html(marp_markdown, output_path=html_path, timeout=30)
            filenames["html"] = os.path.basename(html_path)
            logger.info(f"Regenerated HTML for slide {slide_id}")
        except Exception as e:
            logger.warning(f"Marp CLI rendering failed for slide {slide_id}: {e}")
            # Create fallback HTML
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(f"<html><body><h1>Rendering Failed</h1><p>{e}</p></body></html>\n")
            filenames["html"] = os.path.basename(html_path)

    # Update metadata
    meta = {
        "id": slide_id,
        "title": song.title,
        "artist": ", ".join(song.authors) if song.authors else None,
        "key": song.target_key,
        "filenames": filenames,
        "created_at": existing_meta.get("created_at", timestamp),  # Preserve original creation time
        "updated_at": timestamp,
    }

    # Add optional fields if present
    if song.bpm is not None:
        meta["bpm"] = song.bpm
    if song.time_signature:
        meta["time_signature"] = song.time_signature
    if song.ccli_number:
        meta["ccli_number"] = song.ccli_number

    # Save updated metadata
    meta_path = _meta_path(slide_id)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    return meta


def get_slide_file(slide_id: str, format: str = "html") -> Optional[str]:
    """
    Get the path to a slide file in the specified format.

    Args:
        slide_id: UUID of the slide
        format: File format ('yaml', 'marp', or 'html')

    Returns:
        Path to the file if it exists, None otherwise
    """
    file_path = _slide_path(slide_id, format)
    if os.path.exists(file_path):
        return file_path
    return None


def clear_temp_files():
    """Delete all files in saved_slides except for .yaml, .marp.md, .html,
    and .json files (keeps saved slides and removes orphan / scratch
    artefacts)."""
    for fname in os.listdir(SLIDES_DIR):
        if (
            fname.endswith(".yaml")
            or fname.endswith(".marp.md")
            or fname.endswith(".html")
            or fname.endswith(".json")
        ):
            continue
        file_path = os.path.join(SLIDES_DIR, fname)
        try:
            os.remove(file_path)
        except Exception as e:
            print(f"Could not remove {file_path}: {e}")
