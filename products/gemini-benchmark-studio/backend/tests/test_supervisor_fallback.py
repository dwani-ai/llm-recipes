from app.schemas import BenchmarkRequest
from agent.supervisor_agent import SupervisorAgent


def test_supervisor_fallback_response() -> None:
    supervisor = SupervisorAgent()
    response = supervisor.fallback_response("synthetic failure")
    assert response.run_id == "failed"
    assert response.recommendation.best_scenario_id is None
    assert "synthetic failure" in response.recommendation.rationale


def test_supervisor_handles_missing_template_variables() -> None:
    supervisor = SupervisorAgent()
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

