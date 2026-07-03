"""API-facing helpers for generating and validating song YAML data."""

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from src.utils.yaml_converter import convert_to_yaml
from src.utils.yaml_models import SongYAML

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schema" / "song.schema.json"


def _first_present(*values: Any) -> Any:
    """Return the first value that is not None or an empty string."""
    for value in values:
        if value is not None and value != "":
            return value
    return None


def _normalize_source_urls(metadata: dict[str, Any], chart: dict[str, Any], song_data: dict[str, Any]) -> list[str]:
    """Collect source URLs from supported request shapes without duplicates."""
    source_urls: list[str] = []

    for value in (
        metadata.get("source_urls"),
        chart.get("source_urls"),
        song_data.get("source_urls"),
    ):
        if isinstance(value, list):
            source_urls.extend(str(url) for url in value if url)

    for value in (
        metadata.get("source_url"),
        chart.get("source_url"),
        song_data.get("source_url"),
    ):
        if value:
            source_urls.append(str(value))

    return list(dict.fromkeys(source_urls))


def _normalize_authors(metadata: dict[str, Any], song_data: dict[str, Any]) -> list[str] | None:
    """Return authors from metadata, falling back to the legacy artist field."""
    authors = metadata.get("authors") or song_data.get("authors")
    if isinstance(authors, list):
        cleaned_authors = [str(author).strip() for author in authors if str(author).strip()]
        return cleaned_authors or None

    artist = _first_present(metadata.get("artist"), song_data.get("artist"))
    if artist:
        return [str(artist).strip()]

    return None


def _song_data_from_request(payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Build the current converter input from planned and legacy request shapes."""
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    chart = payload.get("chart") if isinstance(payload.get("chart"), dict) else {}

    song_data = dict(payload.get("song_data") or {})
    if not song_data:
        song_data = dict(payload)

    song_data.update(
        {
            "title": _first_present(metadata.get("title"), song_data.get("title")),
            "search_name": _first_present(
                metadata.get("search_name"),
                metadata.get("title"),
                song_data.get("search_name"),
            ),
            "artist": _first_present(
                metadata.get("artist"),
                ", ".join(metadata.get("authors", [])) if isinstance(metadata.get("authors"), list) else None,
                song_data.get("artist"),
            ),
            "content": _first_present(
                chart.get("content"),
                chart.get("raw_text"),
                chart.get("chart_text"),
                song_data.get("content"),
            )
            or "",
            "original_key": _first_present(
                metadata.get("original_key"),
                chart.get("source_key"),
                chart.get("original_key"),
                song_data.get("original_key"),
            ),
            "key": _first_present(chart.get("key"), song_data.get("key")),
            "target_key": _first_present(
                payload.get("target_key"),
                chart.get("target_key"),
                song_data.get("target_key"),
                payload.get("key"),
                chart.get("key"),
                song_data.get("key"),
                payload.get("original_key"),
                chart.get("source_key"),
                chart.get("original_key"),
                song_data.get("original_key"),
            ),
        }
    )

    source_urls = _normalize_source_urls(metadata, chart, song_data)
    if source_urls:
        song_data["source_url"] = source_urls[0]

    return song_data, metadata, chart


def song_yaml_to_dict(song: SongYAML) -> dict[str, Any]:
    """Convert nested song YAML dataclasses into JSON-serializable dictionaries."""
    return asdict(song)


def validate_song_yaml_dict(song_yaml: dict[str, Any]) -> dict[str, Any]:
    """Validate serialized song YAML against the project JSON schema."""
    with SCHEMA_PATH.open(encoding="utf-8") as schema_file:
        schema = json.load(schema_file)

    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(song_yaml), key=lambda error: list(error.path))

    return {
        "valid": not errors,
        "errors": [
            {
                "message": error.message,
                "path": "$" + "".join(f".{part}" for part in error.path),
                "schema_path": "#/" + "/".join(str(part) for part in error.schema_path),
            }
            for error in errors
        ],
    }


def generate_yaml_response(payload: dict[str, Any]) -> dict[str, Any]:
    """Convert API request data into serialized YAML data plus validation details."""
    song_data, metadata, chart = _song_data_from_request(payload)
    target_key = _first_present(
        payload.get("target_key"),
        song_data.get("target_key"),
        payload.get("key"),
        song_data.get("key"),
        song_data.get("original_key"),
    )
    song = convert_to_yaml(song_data, target_key=target_key)

    authors = _normalize_authors(metadata, song_data)
    source_urls = _normalize_source_urls(metadata, chart, song_data)

    if authors:
        song.authors = authors
    if source_urls:
        song.source_urls = source_urls

    for field_name in (
        "ccli_number",
        "copyright",
        "original_key",
        "bpm",
        "time_signature",
        "capo",
    ):
        value = _first_present(metadata.get(field_name), song_data.get(field_name))
        if value is not None:
            setattr(song, field_name, value)

    song_yaml = song_yaml_to_dict(song)
    return {
        "yaml": song_yaml,
        "validation": validate_song_yaml_dict(song_yaml),
    }
