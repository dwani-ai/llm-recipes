from fastapi.testclient import TestClient

from app.main import app


def test_optimize_and_benchmark_endpoint_runs_both_paths() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/prompt/optimize-and-benchmark",
        json={
            "benchmark": {
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
            },
            "optimization": {
                "template": "Analyze {{dataset_name}} for {{goal}}",
                "variables": {"dataset_name": "tickets", "goal": "latency"},
                "objective": "balanced",
                "variant_count": 3,
                "locked_phrases": [],
            },
            "use_winner_template": True,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert "optimization" in payload
    assert "benchmark" in payload
    assert payload["optimization"]["winner_variant_id"]
    assert payload["benchmark"]["run_id"]

