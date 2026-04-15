from fastapi.testclient import TestClient

from app.main import app


def test_prompt_optimize_endpoint_returns_winner() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/prompt/optimize",
        json={
            "template": "Analyze {{dataset_name}} for {{goal}}",
            "variables": {"dataset_name": "tickets", "goal": "latency"},
            "objective": "balanced",
            "variant_count": 3,
            "locked_phrases": ["tickets"],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["winner_variant_id"]
    assert len(payload["variants"]) == 3
    assert payload["winner_template"]

