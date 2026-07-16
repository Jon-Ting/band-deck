"""HTTP-level tests for the /api/validate and /api/health endpoints."""

import json

from flask import Flask

from src.routes.api import api_bp


def make_client() -> Flask:
    app = Flask(__name__)
    app.register_blueprint(api_bp, url_prefix="/api")
    return app


def _complete_song_payload() -> dict:
    return {
        "title": "Test Song",
        "authors": ["Test Writer"],
        "target_key": "G",
        "sections": {
            "Verse 1": {
                "name": "Verse 1",
                "type": "verse",
                "lines": [
                    {
                        "text": "Hello world",
                        "chords": [
                            {
                                "chord": "G",
                                "position": 0,
                            }
                        ],
                    }
                ],
            }
        },
        "arrangement": ["Verse 1"],
        "license_number": "1234567",
        "copyright": "© 2024",
    }


class TestValidateEndpoint:
    """Focused tests for /api/validate"""

    def test_validate_happy_path_returns_structured_result(self):
        client = make_client().test_client()

        response = client.post(
            "/api/validate",
            json={"song": _complete_song_payload(), "style": "practice"},
        )

        assert response.status_code == 200
        payload = response.get_json()
        assert payload is not None
        assert payload["style"] == "practice"
        assert isinstance(payload["errors"], list)
        assert isinstance(payload["warnings"], list)
        assert isinstance(payload["overflow"], list)
        assert isinstance(payload["licensing_warnings"], list)
        # The complete song has no errors and at most overflow entries.
        assert payload["errors"] == [], (
            f"Expected complete song to pass validation; got {payload['errors']}"
        )
        # The license permission reminder is always emitted.
        assert any("permission" in w for w in payload["licensing_warnings"])

    def test_validate_reports_invalid_chord(self):
        client = make_client().test_client()
        payload = _complete_song_payload()
        payload["sections"]["Verse 1"]["lines"][0]["chords"][0]["chord"] = "Bx"

        response = client.post(
            "/api/validate",
            json={"song": payload},
        )

        assert response.status_code == 200
        body = response.get_json()
        assert any("Bx" in err for err in body["errors"]), body["errors"]

    def test_validate_reports_missing_arrangement_section(self):
        client = make_client().test_client()
        payload = _complete_song_payload()
        payload["arrangement"] = ["Verse 1", "Phantom"]

        response = client.post(
            "/api/validate",
            json={"song": payload},
        )

        assert response.status_code == 200
        body = response.get_json()
        assert any("Phantom" in err for err in body["errors"]), body["errors"]

    def test_validate_reports_overflow_warning_for_long_section(self):
        client = make_client().test_client()
        payload = _complete_song_payload()
        # 18 lines overflows the practice cap of 12.
        payload["sections"]["Verse 1"]["lines"] = [
            {"text": f"Line {idx}", "chords": [{"chord": "G", "position": 0}]}
            for idx in range(18)
        ]

        response = client.post(
            "/api/validate",
            json={"song": payload, "style": "practice"},
        )

        assert response.status_code == 200
        body = response.get_json()
        assert any(
            entry["section_name"] == "Verse 1" for entry in body["overflow"]
        ), body["overflow"]

    def test_validate_rejects_non_object_body(self):
        response = make_client().test_client().post(
            "/api/validate",
            data=json.dumps(["not", "a", "dict"]),
            content_type="application/json",
        )

        assert response.status_code == 400
        assert "JSON object" in response.get_json()["error"]

    def test_validate_rejects_missing_song_payload(self):
        response = make_client().test_client().post(
            "/api/validate",
            json={"style": "practice"},
        )

        assert response.status_code == 400
        assert "song" in response.get_json()["error"].lower()

    def test_validate_with_check_placeholders_flags_todo(self):
        client = make_client().test_client()
        payload = _complete_song_payload()
        payload["title"] = "TODO Test"

        response = client.post(
            "/api/validate",
            json={"song": payload, "check_placeholders": True},
        )

        assert response.status_code == 200
        body = response.get_json()
        assert any("placeholder" in err.lower() for err in body["errors"]), body["errors"]


class TestHealthEndpoint:
    """Focused tests for /api/health"""

    def test_health_returns_status_and_storage_payload(self, monkeypatch):
        # Force Marp to look "available" so the endpoint says ok.
        monkeypatch.setattr(
            "src.utils.html_renderer.verify_marp_cli", lambda: True
        )

        response = make_client().test_client().get("/api/health")

        assert response.status_code == 200
        body = response.get_json()
        assert body["status"] == "ok"
        assert body["marp_cli"]["available"] is True
        assert "path" in body["storage"]
        assert isinstance(body["storage"]["files"], int)
        assert isinstance(body["storage"]["bytes"], int)

    def test_health_reports_degraded_when_marp_missing(self, monkeypatch):
        monkeypatch.setattr(
            "src.utils.html_renderer.verify_marp_cli", lambda: False
        )

        response = make_client().test_client().get("/api/health")

        assert response.status_code == 200
        body = response.get_json()
        assert body["status"] == "degraded"
        assert body["marp_cli"]["available"] is False
        assert "Marp CLI" in body["marp_cli"]["note"]
