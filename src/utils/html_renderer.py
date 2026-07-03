"""Render Marp markdown into standalone HTML using the Marp CLI."""

from __future__ import annotations

import logging
import os
import re
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_RENDER_TIMEOUT_SECONDS = 30
DEFAULT_HEALTHCHECK_TIMEOUT_SECONDS = 5
MAX_MARKDOWN_BYTES = 2 * 1024 * 1024

UNSAFE_MARKDOWN_PATTERNS = (
    re.compile(r"<\s*/?\s*script\b", re.IGNORECASE),
    re.compile(r"<\s*/?\s*(?:iframe|object|embed)\b", re.IGNORECASE),
    re.compile(r"\s+on[a-z]+\s*=", re.IGNORECASE),
    re.compile(r"javascript\s*:", re.IGNORECASE),
)


class RenderError(RuntimeError):
    """Raised when Marp CLI rendering fails."""


def _validate_markdown(marp_markdown: str) -> None:
    """Reject empty or unsafe markdown before invoking Marp."""
    if not isinstance(marp_markdown, str):
        raise TypeError("marp_markdown must be a string")

    if not marp_markdown.strip():
        raise ValueError("Marp markdown must not be empty")

    if len(marp_markdown.encode("utf-8")) > MAX_MARKDOWN_BYTES:
        raise ValueError("Marp markdown is too large to render safely")

    for pattern in UNSAFE_MARKDOWN_PATTERNS:
        if pattern.search(marp_markdown):
            raise ValueError("Marp markdown contains unsafe HTML or JavaScript")


def verify_marp_cli(
    *,
    marp_command: str = "marp",
    timeout: int = DEFAULT_HEALTHCHECK_TIMEOUT_SECONDS,
) -> bool:
    """Return whether the Marp CLI is installed and executable."""
    try:
        result = subprocess.run(
            [marp_command, "--version"],
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            timeout=timeout,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired) as exc:
        logger.warning("Marp CLI health check failed: %s", exc)
        return False

    return result.returncode == 0


def render_html(
    marp_markdown: str,
    output_path: str | os.PathLike[str] | None = None,
    *,
    timeout: int = DEFAULT_RENDER_TIMEOUT_SECONDS,
    marp_command: str = "marp",
) -> str:
    """Render Marp markdown to a standalone HTML file and return its path."""
    _validate_markdown(marp_markdown)

    if timeout <= 0:
        raise ValueError("timeout must be greater than zero")

    if output_path is None:
        output_fd, resolved_output_path = tempfile.mkstemp(suffix=".html")
        os.close(output_fd)
    else:
        resolved_output_path = str(Path(output_path))
        Path(resolved_output_path).parent.mkdir(parents=True, exist_ok=True)

    input_fd, input_path = tempfile.mkstemp(suffix=".md")
    try:
        with os.fdopen(input_fd, "w", encoding="utf-8") as markdown_file:
            markdown_file.write(marp_markdown)

        cmd = [
            marp_command,
            input_path,
            "--html",
            "--no-config-file",
            "-o",
            resolved_output_path,
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise RenderError(f"Marp CLI timed out after {timeout} seconds") from exc
    except OSError as exc:
        raise RenderError(f"Marp CLI could not be executed: {exc}") from exc
    finally:
        try:
            os.unlink(input_path)
        except FileNotFoundError:
            pass

    if result.returncode != 0:
        error_output = (result.stderr or result.stdout or "unknown error").strip()
        raise RenderError(f"Marp CLI failed: {error_output}")

    if not Path(resolved_output_path).exists():
        raise RenderError("Marp CLI completed without creating an HTML file")

    return resolved_output_path
