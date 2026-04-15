from dataclasses import dataclass
from typing import Dict, List

from agent.analyzer_agent import AnalyzerAgent
from agent.benchmark_worker_agent import BenchmarkWorkerAgent
from agent.optimizer_agent import OptimizerAgent
from agent.planner_agent import PlannerAgent
from agent.reporter_agent import ReporterAgent
from app.schemas import BenchmarkRecommendation, BenchmarkRequest, BenchmarkResponse, ScenarioSummary
from app.services.benchmark_runner import BenchmarkRunner
from app.services.prompt_template import render_prompt_template


@dataclass
class SupervisorResult:
    response: BenchmarkResponse
    trace: List[str]


class SupervisorAgent:
    def __init__(self) -> None:
        self.runner = BenchmarkRunner()
        self.planner = PlannerAgent(self.runner)
        self.worker = BenchmarkWorkerAgent(self.runner)
        self.analyzer = AnalyzerAgent()
        self.optimizer = OptimizerAgent()
        self.reporter = ReporterAgent()

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
        analyzer = self.analyzer.analyze(summaries_raw)
        trace.extend(analyzer.trace)

        optimizer = self.optimizer.suggest(analyzer.best_row)
        trace.extend(optimizer.trace)

        reporter = self.reporter.report(analyzer.best_row, summaries_raw)
        trace.extend(reporter.trace)

        recommendation = BenchmarkRecommendation(
            best_scenario_id=analyzer.best_scenario_id,
            rationale=reporter.rationale,
            alternatives=optimizer.alternatives,
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
            ),
            reasoning_trace=["SupervisorAgent: fallback response returned after workflow failure."],
            artifacts={},
        )

