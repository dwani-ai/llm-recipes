from app.schemas import BenchmarkRequest
from agent.benchmark_worker_agent import BenchmarkWorkerOutput
from agent.supervisor_agent import SupervisorAgent


def test_supervisor_fallback_response() -> None:
    supervisor = SupervisorAgent()
    response = supervisor.fallback_response("synthetic failure")
    assert response.run_id == "failed"
    assert response.status == "failed"
    assert response.error_message == "synthetic failure"
    assert response.recommendation.best_scenario_id is None
    assert response.recommendation.confidence == "low"
    assert response.recommendation.ranked_scenarios == []
    assert "synthetic failure" in response.recommendation.rationale


def test_supervisor_handles_missing_template_variables(monkeypatch) -> None:
    supervisor = SupervisorAgent()

    def fake_worker_run(request: BenchmarkRequest, rendered_prompt: str) -> BenchmarkWorkerOutput:
        payload = {
            "run_id": "synthetic-run",
            "summaries": [
                {
                    "scenario_id": "unknown_stack|gemini-2.5-flash|streaming|thinking_False|cache_none|short_prompt",
                    "stack": "unknown_stack",
                    "model": "gemini-2.5-flash",
                    "mode": "streaming",
                    "thinking": False,
                    "thinking_token_budget": 1024,
                    "cache_strategy": "none",
                    "prompt_type": "short_prompt",
                    "samples": 1,
                    "ok_count": 1,
                    "unsupported_count": 0,
                    "error_count": 0,
                    "ttft_p50_s": 0.25,
                    "ttft_p95_s": 0.25,
                    "e2e_p50_s": 0.9,
                    "tokens_per_s_avg": 21.0,
                    "ttft_definition": "first_final_output_token",
                    "note": None,
                }
            ],
            "artifacts": {"report_md": "synthetic.md"},
        }
        return BenchmarkWorkerOutput(run_payload=payload, trace=["BenchmarkWorkerAgent: synthetic output."])

    monkeypatch.setattr(supervisor.worker, "run", fake_worker_run)

    request = BenchmarkRequest(
        api_key="dummy_api_key_123456789",
        stacks=["unknown_stack"],
        models=["gemini-2.5-flash"],
        trials=1,
        warmup_trials=0,
        prompt_template="Analyze {{dataset_name}} for {{goal}}",
        prompt_variables={"dataset_name": "user_data"},
    )
    response = supervisor.run(request).response
    assert response.run_id != ""
    assert response.rendered_prompt != ""
    assert len(response.reasoning_trace) > 0
    assert response.recommendation.objective == "lowest_latency"

