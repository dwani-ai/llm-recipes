from fastapi.testclient import TestClient

from app.main import app


def _base_payload() -> dict:
    return {
        "stacks": ["unknown_stack"],
        "models": ["gemini-2.5-flash"],
        "trials": 1,
        "warmup_trials": 0,
        "mode_selection": {
            "streaming": True,
            "thinking": False,
            "implicit_cache": False,
            "explicit_cache": False,
        },
        "prompt_template": "Analyze {{dataset_name}} for {{goal}}",
        "prompt_variables": {"dataset_name": "tickets", "goal": "latency"},
        "include_long_context": False,
    }


def test_schedule_requires_start_time() -> None:
    client = TestClient(app)
    payload = _base_payload()
    payload.update({"schedule_enabled": True})
    response = client.post("/api/benchmark/run", json=payload)
    assert response.status_code == 400
    assert "schedule_start_at is required" in response.text


def test_schedule_supports_only_15_minute_window() -> None:
    client = TestClient(app)
    payload = _base_payload()
    payload.update(
        {
            "schedule_enabled": True,
            "schedule_start_at": "2030-01-01T10:00:00Z",
            "schedule_window_minutes": 20,
        }
    )
    response = client.post("/api/benchmark/run", json=payload)
    assert response.status_code == 400
    assert "15-minute scheduling window" in response.text
