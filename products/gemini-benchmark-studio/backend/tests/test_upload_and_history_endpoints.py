from fastapi.testclient import TestClient

from app.main import app


def test_upload_context_endpoint() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/prompt/upload-context",
        files={"file": ("context.txt", b"sample dataset context for testing", "text/plain")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["variable_key"] == "data_context"
    assert payload["bytes_received"] > 0
    assert payload["chars_extracted"] > 0
    assert "sample dataset context" in payload["context_text"]


def test_history_endpoint_returns_runs_list() -> None:
    client = TestClient(app)
    response = client.get("/api/benchmark/history?limit=5")
    assert response.status_code == 200
    payload = response.json()
    assert "runs" in payload
    assert isinstance(payload["runs"], list)

