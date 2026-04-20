from fastapi.testclient import TestClient

from app.main import app, supervisor


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


def test_run_benchmark_returns_http_500_on_workflow_failure(monkeypatch) -> None:
    def _raise_failure(*_args, **_kwargs):
        raise RuntimeError("synthetic run failure")

    monkeypatch.setattr(supervisor, "run", _raise_failure)
    client = TestClient(app)
    response = client.post("/api/benchmark/run", json=_base_payload())
    assert response.status_code == 500
    body = response.json()
    assert "detail" in body
    assert body["detail"]["message"] == "Benchmark workflow failed."
    assert "synthetic run failure" in body["detail"]["error"]
    assert body["detail"]["fallback"]["status"] == "failed"
