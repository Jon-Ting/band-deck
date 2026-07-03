"""Tests for rendering Marp markdown to standalone HTML."""

import subprocess
from pathlib import Path

import pytest

from src.utils.html_renderer import RenderError, render_html, verify_marp_cli


def test_render_html_writes_markdown_file_and_invokes_marp(tmp_path, monkeypatch):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        output_path = Path(cmd[cmd.index("-o") + 1])
        output_path.write_text("<html><style>.chord{}</style><body>Deck</body></html>", encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    output_path = tmp_path / "deck.html"
    result = render_html(
        "---\nmarp: true\n---\n<style>.chord{}</style>\n# Song",
        output_path=output_path,
        timeout=12,
    )

    assert result == str(output_path)
    assert output_path.read_text(encoding="utf-8").startswith("<html>")
    assert len(calls) == 1

    cmd, kwargs = calls[0]
    assert cmd[0] == "marp"
    assert cmd[1].endswith(".md")
    assert "--html" in cmd
    assert "--no-config-file" in cmd
    assert "--allow-local-files" not in cmd
    assert cmd[cmd.index("-o") + 1] == str(output_path)
    assert kwargs["timeout"] == 12
    assert kwargs["stdin"] == subprocess.DEVNULL
    assert kwargs["capture_output"] is True
    assert kwargs["text"] is True


def test_render_html_creates_output_file_when_path_not_supplied(monkeypatch):
    def fake_run(cmd, **kwargs):
        output_path = Path(cmd[cmd.index("-o") + 1])
        output_path.write_text("<html>generated</html>", encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = render_html("---\nmarp: true\n---\n# Song")

    assert result.endswith(".html")
    assert Path(result).read_text(encoding="utf-8") == "<html>generated</html>"
    Path(result).unlink()


@pytest.mark.parametrize(
    "markdown",
    [
        "",
        "   ",
        "# Song\n<script>alert('x')</script>",
        "# Song\n<a href=\"javascript:alert('x')\">bad</a>",
        "# Song\n<div onclick=\"alert('x')\">bad</div>",
    ],
)
def test_render_html_rejects_unsafe_or_empty_markdown(markdown):
    with pytest.raises(ValueError):
        render_html(markdown)


def test_render_html_raises_render_error_on_marp_failure(tmp_path, monkeypatch):
    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="parse failed")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(RenderError, match="parse failed"):
        render_html("# Song", output_path=tmp_path / "deck.html")


def test_render_html_raises_render_error_on_timeout(tmp_path, monkeypatch):
    def fake_run(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=kwargs["timeout"])

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(RenderError, match="timed out"):
        render_html("# Song", output_path=tmp_path / "deck.html", timeout=1)


def test_verify_marp_cli_returns_true_when_command_succeeds(monkeypatch):
    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 0, stdout="1.0.0", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    assert verify_marp_cli(timeout=2) is True


def test_verify_marp_cli_returns_false_when_command_fails(monkeypatch):
    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="not found")

    monkeypatch.setattr(subprocess, "run", fake_run)

    assert verify_marp_cli(timeout=2) is False


def test_verify_marp_cli_returns_false_when_command_missing(monkeypatch):
    def fake_run(cmd, **kwargs):
        raise FileNotFoundError("marp")

    monkeypatch.setattr(subprocess, "run", fake_run)

    assert verify_marp_cli(timeout=2) is False
