from fastapi.testclient import TestClient

from app.main import app


def test_default_modes_endpoint_has_best_defaults() -> None:
    client = TestClient(app)
    response = client.get("/api/benchmark/default-modes")
    assert response.status_code == 200
    payload = response.json()["defaults"]
    assert payload["stack"] == "google_genai"
    assert payload["streaming"] is False
    assert payload["thinking"] is True
    assert payload["thinking_token_budget"] == 256
    assert payload["thinking_mode"] == "budget"
    assert payload["thinking_level"] == "medium"
    assert payload["implicit_cache"] is False
    assert payload["explicit_cache"] is True

