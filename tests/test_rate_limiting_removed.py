"""Regression tests for the app-wide API request handling."""

from __future__ import annotations

import src.main as main_module


def test_api_requests_are_not_rate_limited(monkeypatch):
    monkeypatch.setattr(
        "src.utils.html_renderer.verify_marp_cli",
        lambda: True,
    )

    client = main_module.app.test_client()

    responses = [client.get("/api/health") for _ in range(12)]

    assert all(response.status_code == 200 for response in responses)
    assert 429 not in [response.status_code for response in responses]
