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

