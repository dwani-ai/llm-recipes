from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

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

    def _write_final_report(
        self,
        response: BenchmarkResponse,
        request: BenchmarkRequest,
        missing_template_vars: Optional[List[str]] = None,
    ) -> None:
        report_path_raw = response.artifacts.get("report_md")
        if not report_path_raw:
            return
        report_path = Path(report_path_raw)
        if not report_path.exists():
            return

        missing_template_vars = missing_template_vars or []

        def _fmt_num(value: object, digits: int = 3) -> str:
            if isinstance(value, (float, int)):
                return f"{float(value):.{digits}f}"
            return "n/a"

        lines: List[str] = [
            "# Gemini Benchmark Studio Report",
            "",
            f"Run ID: `{response.run_id}`",
            "",
            "## Recommendation",
            "",
            f"- Best scenario: `{response.recommendation.best_scenario_id or 'n/a'}`",
            f"- Objective: `{response.recommendation.objective}`",
            f"- Confidence: `{response.recommendation.confidence}`",
            f"- Reliability score: `{response.recommendation.reliability_score:.3f}`",
            f"- Acceptance status: `{response.recommendation.overall_acceptance_status}`",
            (
                "- Acceptance gate counts: "
                f"pass={response.recommendation.gate_pass_count}, "
                f"fail={response.recommendation.gate_fail_count}"
            ),
            f"- Rationale: {response.recommendation.rationale}",
            "",
            "## Ranked Eligible Scenarios",
            "",
            "| Rank | Scenario | Score | TTFT P50 (s) | E2E P50 (s) | Accuracy | Success Rate | Error Rate |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]

        for idx, row in enumerate(response.recommendation.ranked_scenarios, start=1):
            ttft = row.get("ttft_p50_s")
            e2e = row.get("e2e_p50_s")
            accuracy = row.get("accuracy_score")
            lines.append(
                "| "
                f"{idx} | {row.get('scenario_id', 'n/a')} | {row.get('score', 0.0):.4f} | "
                f"{_fmt_num(ttft)} | "
                f"{_fmt_num(e2e)} | "
                f"{_fmt_num(accuracy)} | "
                f"{(row.get('success_rate', 0.0) * 100):.1f}% | "
                f"{(row.get('error_rate', 0.0) * 100):.1f}% |"
            )

        if not response.recommendation.ranked_scenarios:
            lines.append("| - | n/a | n/a | n/a | n/a | n/a | n/a | n/a |")

        lines.extend(
            [
                "",
                "## Acceptance Testing Summary",
                "",
                "| Scenario | Tier | Acceptance | Accuracy Mean | Accuracy P50 | Accuracy P95 | TTFT P50 (s) | Reason |",
                "| --- | --- | --- | ---: | ---: | ---: | ---: | --- |",
            ]
        )

        for row in response.summaries:
            acceptance = "n/a"
            if row.acceptance_passed is True:
                acceptance = "pass"
            elif row.acceptance_passed is False:
                acceptance = "fail"
            lines.append(
                "| "
                f"{row.scenario_id} | {row.acceptance_tier} | {acceptance} | "
                f"{_fmt_num(row.accuracy_score)} | "
                f"{_fmt_num(row.accuracy_p50)} | "
                f"{_fmt_num(row.accuracy_p95)} | "
                f"{_fmt_num(row.ttft_p50_s)} | "
                f"{row.acceptance_reason or row.note or 'ok'} |"
            )

        if response.recommendation.disqualified_scenarios:
            lines.extend(["", "## Disqualified Scenarios", ""])
            for item in response.recommendation.disqualified_scenarios:
                lines.append(f"- `{item.get('scenario_id', 'n/a')}`: {item.get('reason', 'unknown')}")

        if response.recommendation.alternatives:
            lines.extend(["", "## Alternatives", ""])
            for alt in response.recommendation.alternatives:
                lines.append(f"- {alt}")

        response.artifacts["acceptance_report_md"] = str(report_path)

        lines.extend(["", "## Artifacts", ""])
        for key, value in sorted(response.artifacts.items()):
            lines.append(f"- {key}: `{value}`")

        def _file_status(artifact_key: str) -> tuple[str, str]:
            path_str = response.artifacts.get(artifact_key)
            if not path_str:
                return "MISSING", "not listed in artifacts"
            path_obj = Path(path_str)
            if path_obj.is_file():
                return "OK", f"`{path_str}`"
            return "MISSING", f"file not found: `{path_str}`"

        n_summaries = len(response.summaries)
        has_ok_trials = any(s.ok_count and s.ok_count > 0 for s in response.summaries)
        latency_ok = True
        if has_ok_trials:
            for s in response.summaries:
                if s.ok_count and s.ok_count > 0 and s.ttft_p50_s is None:
                    latency_ok = False
                    break

        eval_requested = request.evaluation_enabled
        eval_samples_any = any(
            (s.evaluation_samples or 0) > 0 or s.accuracy_score is not None for s in response.summaries
        )
        if eval_requested:
            if eval_samples_any:
                eval_status, eval_detail = _file_status("evaluation_summary_json")
                if eval_status == "OK":
                    acc_status = "OK" if any(s.accuracy_score is not None for s in response.summaries) else "WARN"
                    acc_detail = (
                        "at least one scenario has accuracy aggregate"
                        if acc_status == "OK"
                        else "no accuracy aggregates; check judge errors in raw JSONL"
                    )
                else:
                    acc_status, acc_detail = "MISSING", eval_detail
            else:
                acc_status = "WARN"
                acc_detail = "evaluation enabled but no evaluation samples recorded"
        else:
            acc_status, acc_detail = "N/A", "evaluation disabled for this run"

        sched_requested = request.schedule_enabled
        if sched_requested:
            has_sched = bool(
                response.artifacts.get("schedule_window_start")
                and response.artifacts.get("schedule_window_end")
            )
            sched_status, sched_detail = ("OK", "window start/end in artifacts") if has_sched else ("MISSING", "schedule enabled but window not in artifacts")
        else:
            sched_status, sched_detail = "N/A", "scheduling not used"

        if missing_template_vars:
            tmpl_status, tmpl_detail = "WARN", f"missing keys replaced with empty string: {', '.join(missing_template_vars)}"
        else:
            tmpl_status, tmpl_detail = "OK", "no missing template variables"

        rendered = response.rendered_prompt or ""
        prompt_status = "OK" if rendered.strip() else "WARN"
        prompt_detail = f"{len(rendered)} characters" if rendered.strip() else "empty; fallback may have been used"

        rec = response.recommendation
        if rec.ranked_scenarios or rec.best_scenario_id:
            rec_status, rec_detail = "OK", "best scenario and/or ranked rows present"
        elif n_summaries == 0:
            rec_status, rec_detail = "WARN", "no scenario summaries"
        else:
            rec_status, rec_detail = "WARN", "no eligible winner; see disqualified list"

        gate_detail = (
            f"pass={rec.gate_pass_count}, fail={rec.gate_fail_count}, status={rec.overall_acceptance_status}"
        )
        if eval_requested:
            gate_status = "OK"
        else:
            gate_status = "N/A"
            gate_detail = "acceptance gates apply only when evaluation is enabled"

        completeness_rows = [
            ("Run ID", "OK" if response.run_id else "MISSING", f"`{response.run_id}`" if response.run_id else "empty"),
            ("Scenario summaries", "OK" if n_summaries > 0 else "MISSING", f"{n_summaries} scenario(s)"),
            ("Raw results (JSONL)", *_file_status("raw_jsonl")),
            ("Aggregated summary (JSON)", *_file_status("summary_json")),
            ("Summary CSV", *_file_status("summary_csv")),
            ("Studio report (this file)", "OK", f"written to `{report_path}`"),
            ("Evaluation summary JSON", *_file_status("evaluation_summary_json")),
            ("Scheduled window metadata", sched_status, sched_detail),
            ("Rendered prompt captured", prompt_status, prompt_detail),
            ("Prompt template variables", tmpl_status, tmpl_detail),
            ("Latency metrics (TTFT P50 when trials OK)", "OK" if latency_ok else "WARN", "all OK scenarios have ttft_p50" if latency_ok else "some OK scenarios missing ttft_p50"),
            ("Accuracy aggregates (evaluation)", acc_status, acc_detail),
            ("Recommendation / ranking", rec_status, rec_detail),
            ("Acceptance gate counts", gate_status, gate_detail),
        ]

        lines.extend(
            [
                "",
                "## Report completeness (self-check)",
                "",
                "This section is generated automatically. Use it to verify exports and spot gaps before sign-off.",
                "",
                "| Check | Status | Detail |",
                "| --- | --- | --- |",
            ]
        )
        for label, status, detail in completeness_rows:
            lines.append(f"| {label} | {status} | {detail} |")

        report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

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
        self._write_final_report(response, request, missing)
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

