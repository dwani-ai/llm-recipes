from dataclasses import dataclass
from typing import Dict, List

from agent.adk_runtime import ADKRuntime
from agent.analyzer_agent import AnalyzerAgent
from agent.benchmark_worker_agent import BenchmarkWorkerAgent
from agent.optimizer_agent import OptimizerAgent
from agent.planner_agent import PlannerAgent
from agent.reporter_agent import ReporterAgent
from agent.tool_worker_agent import ToolWorkerAgent
from app.schemas import BenchmarkRecommendation, BenchmarkRequest, BenchmarkResponse, ScenarioSummary
from app.services.benchmark_runner import BenchmarkRunner
from app.services.prompt_template import render_prompt_template


@dataclass
class SupervisorResult:
    response: BenchmarkResponse
    trace: List[str]


class SupervisorAgent:
    def __init__(self) -> None:
        self.runtime = ADKRuntime()
        self.runner = BenchmarkRunner()
        self.planner = PlannerAgent(self.runner)
        self.worker = BenchmarkWorkerAgent(self.runner)
        self.analyzer = AnalyzerAgent()
        self.optimizer = OptimizerAgent()
        self.reporter = ReporterAgent()
        self.tool_worker = ToolWorkerAgent(self.runtime)
        self._register_tools()

    def _register_tools(self) -> None:
        self.runtime.register_tool(
            "count_successful_scenarios",
            lambda summaries: len([item for item in summaries if item.get("ok_count", 0) > 0]),
        )
        self.runtime.register_tool(
            "estimate_reliability_score",
            lambda summaries: (
                0.0
                if not summaries
                else round(
                    len([item for item in summaries if item.get("error_count", 0) == 0]) / len(summaries),
                    3,
                )
            ),
        )

    def run(self, request: BenchmarkRequest) -> SupervisorResult:
        trace: List[str] = ["SupervisorAgent: starting workflow."]
        rendered_prompt, missing = render_prompt_template(request.prompt_template, request.prompt_variables)
        if not rendered_prompt:
            rendered_prompt = "Explain the best latency optimization approach for this dataset."
        if missing:
            trace.append(f"SupervisorAgent: missing variables were detected: {', '.join(missing)}.")

        plan = self.planner.plan(request)
        trace.extend(plan.trace)

        worker_output = self.worker.run(request, rendered_prompt)
        trace.extend(worker_output.trace)

        summaries_raw = worker_output.run_payload["summaries"]
        tool_output = self.tool_worker.run(
            [
                {
                    "tool": "count_successful_scenarios",
                    "kwargs": {"summaries": summaries_raw},
                    "output_key": "success_count",
                },
                {
                    "tool": "estimate_reliability_score",
                    "kwargs": {"summaries": summaries_raw},
                    "output_key": "reliability_score",
                },
            ]
        )
        trace.extend(tool_output.trace)
        trace.append(f"SupervisorAgent: tool outputs={tool_output.outputs}.")

        analyzer = self.analyzer.analyze(
            summaries_raw,
            objective=request.recommendation_objective,
            acceptance_tier=request.acceptance_tier,
            tier_thresholds={key: value.model_dump() for key, value in request.evaluation.tier_thresholds.items()},
            evaluation_enabled=request.evaluation_enabled,
        )
        trace.extend(analyzer.trace)

        optimizer = self.optimizer.suggest(
            best_row=analyzer.best_row,
            ranked_scenarios=analyzer.ranked_scenarios,
            disqualified_scenarios=analyzer.disqualified_scenarios,
        )
        trace.extend(optimizer.trace)

        reporter = self.reporter.report(
            best_row=analyzer.best_row,
            summaries=summaries_raw,
            ranked_scenarios=analyzer.ranked_scenarios,
            confidence=analyzer.confidence,
            reliability_score=analyzer.reliability_score,
            objective=request.recommendation_objective,
        )
        trace.extend(reporter.trace)

        recommendation = BenchmarkRecommendation(
            best_scenario_id=analyzer.best_scenario_id,
            rationale=reporter.rationale,
            alternatives=optimizer.alternatives,
            ranked_scenarios=analyzer.ranked_scenarios,
            disqualified_scenarios=analyzer.disqualified_scenarios,
            reliability_score=analyzer.reliability_score,
            confidence=analyzer.confidence,
            objective=request.recommendation_objective,
            gate_pass_count=analyzer.gate_pass_count,
            gate_fail_count=analyzer.gate_fail_count,
            overall_acceptance_status=analyzer.overall_acceptance_status,
        )

        summaries = [ScenarioSummary(**row) for row in summaries_raw]
        response = BenchmarkResponse(
            run_id=worker_output.run_payload["run_id"],
            rendered_prompt=rendered_prompt,
            summaries=summaries,
            recommendation=recommendation,
            reasoning_trace=trace,
            artifacts=worker_output.run_payload["artifacts"],
        )
        return SupervisorResult(response=response, trace=trace)

    def fallback_response(self, error_message: str) -> BenchmarkResponse:
        return BenchmarkResponse(
            run_id="failed",
            status="failed",
            error_message=error_message,
            rendered_prompt="",
            summaries=[],
            recommendation=BenchmarkRecommendation(
                best_scenario_id=None,
                rationale=f"Benchmark failed: {error_message}",
                alternatives=[
                    "Verify API key validity.",
                    "Retry with fewer scenarios or trials.",
                    "Check network connectivity for model endpoints.",
                ],
                ranked_scenarios=[],
                disqualified_scenarios=[],
                reliability_score=0.0,
                confidence="low",
                objective="lowest_latency",
                gate_pass_count=0,
                gate_fail_count=0,
                overall_acceptance_status="unknown",
            ),
            reasoning_trace=["SupervisorAgent: fallback response returned after workflow failure."],
            artifacts={},
        )

