from fastapi.testclient import TestClient

from app.main import app


def test_default_modes_endpoint_has_best_defaults() -> None:
    client = TestClient(app)
    response = client.get("/api/benchmark/default-modes")
    assert response.status_code == 200
    payload = response.json()["defaults"]
    assert payload["stack"] == "google_genai"
    assert payload["streaming"] is True
    assert payload["thinking"] is False
    assert payload["implicit_cache"] is True

