from fastapi.testclient import TestClient

from app.main import app


def test_token_count_requires_credentials_for_google_stack() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/prompt/token-count",
        json={
            "stack": "google_genai",
            "model": "gemini-2.5-flash",
            "template": "Analyze {{dataset_name}} for {{goal}}",
            "variables": {"dataset_name": "tickets", "goal": "latency"},
        },
    )
    assert response.status_code == 400
    assert "api_key is required" in response.text


def test_token_count_returns_mode_aware_breakdown(monkeypatch) -> None:
    captured = {}

    def fake_mode_aware_token_breakdown(**kwargs):
        captured.update(kwargs)
        return {
            "token_count": 321,
            "breakdown": [
                {
                    "prompt_type": "short_prompt",
                    "strategy": "none",
                    "baseline_request_tokens": 321,
                    "request_tokens": 321,
                    "cache_create_tokens": 0,
                    "first_call_total_tokens": 321,
                    "subsequent_call_tokens": 321,
                    "savings_vs_baseline_after_n_calls": 0,
                }
            ],
        }

    monkeypatch.setattr("app.main.mode_aware_token_breakdown", fake_mode_aware_token_breakdown)

    client = TestClient(app)
    response = client.post(
        "/api/prompt/token-count",
        json={
            "stack": "google_genai",
            "model": "gemini-2.5-flash",
            "api_key": "test-key",
            "template": "Analyze {{dataset_name}} for {{goal}}",
            "variables": {"dataset_name": "tickets", "goal": "latency", "data_context": "ctx"},
            "mode_selection": {
                "streaming": True,
                "thinking": False,
                "implicit_cache": True,
                "explicit_cache": True,
            },
            "include_long_context": True,
            "calls_for_savings": 8,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["token_count"] == 321
    assert payload["calls_for_savings"] == 8
    assert payload["breakdown"][0]["strategy"] == "none"
    assert captured["calls_for_savings"] == 8
    assert captured["mode_selection"].explicit_cache is True
