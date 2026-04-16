# Gemini Benchmark Studio

Standalone product for benchmarking Gemini response modes with:

- React UX
- FastAPI backend
- Supervisor-worker multi-agent orchestration
- Prompt templates for user data
- Upload-to-context for user data files
- Persistent benchmark run history (without API key storage)
- Docker Compose integrated build and run

## Features

- API key input from UI for each run (not persisted)
- Checkbox mode selection
- Stack selection: `google_genai`, `openai_compat`, `vertex_api`
- Best known mode defaults preselected:
  - stack: `google_genai`
  - model: `gemini-2.5-flash`
  - mode: `streaming`
  - thinking: `off`
  - cache: `implicit_reuse`
- Prompt template + variable editor and preview
- Agent-assisted prompt optimization (objective-based variants + winner selection)
- One-click optimize + benchmark flow (kept separate from standalone optimize and benchmark actions)
- Data file upload into `data_context` prompt variable
- Vertex API credentials form (project, location, endpoint, optional access token)
- Benchmark run artifacts and recommendation report
- Run history endpoint and UI table for recent runs

## Stack and Mode Decision Cheat-Sheet

Use this as your default starting point before running the full benchmark matrix.

- **Need fastest perceived TTFT for interactive UX**
  - Start with `streaming=true`, `thinking=false`, `cache=none`.
  - If prompts repeat a large stable prefix, retest with `cache=implicit_reuse` and `cache=explicit_cache`.
- **Need highest quality/reasoning depth**
  - Start with `streaming=false`, `thinking=true`, `cache=implicit_reuse` for repeated context.
- **Need balanced latency + reliability**
  - Start with objective `balanced`, `streaming=true`, `thinking=false`, `cache=implicit_reuse`.
- **Need reliability first (production defaults)**
  - Use objective `reliability_first` and prioritize scenarios with high `ok_count/samples` and low errors.

Stack selection:

- `google_genai`: best feature coverage for thinking + explicit cache.
- `openai_compat`: easiest OpenAI-style integration, but limited explicit cache/thinking control.
- `vertex_api`: best for Vertex endpoint integration and enterprise routing; feature support depends on endpoint path/capability.

## Prompt and Data Cookbook by Use Case

Use this section to quickly choose a mode profile and copy sample `prompt_template` + variables into the UI.

- `prompt_template` maps to the prompt editor.
- `dataset_name`, `goal`, `data_context` map to variable rows.
- All examples are multi-domain and realistic.
- The 12 entries below cover all combinations of:
  - mode: streaming / non-streaming
  - thinking: on / off
  - cache: none / implicit_reuse / explicit_cache

### 1) streaming + thinking_off + cache_none

- **When to use:** Live chat/support where fast first token matters more than deep reasoning.
- **Sample prompt_template:**
```text
Analyze {{dataset_name}} and provide a concise action plan for {{goal}} in 4 bullets.
```
- **Sample variables:**
```json
{
  "dataset_name": "customer_support_tickets_q2",
  "goal": "reduce repeat escalation rate",
  "data_context": "Ticket logs include category, sentiment score, and resolution status for 45,000 interactions."
}
```
- **Expected behavior:** Lowest perceived latency, lower answer depth.
- **Stack compatibility notes:** Works across `google_genai`, `openai_compat`, `vertex_api`.

### 2) streaming + thinking_on + cache_none

- **When to use:** Interactive analyst workflows needing better reasoning with still-streamed UX.
- **Sample prompt_template:**
```text
For {{dataset_name}}, reason step-by-step and propose a prioritized strategy for {{goal}} with assumptions and risks.
```
- **Sample variables:**
```json
{
  "dataset_name": "fraud_detection_alerts_weekly",
  "goal": "cut false positives while preserving recall",
  "data_context": "Alert data includes score bands, investigator outcomes, and merchant risk cohorts."
}
```
- **Expected behavior:** Better answer quality than thinking off, TTFT usually higher.
- **Stack compatibility notes:** Thinking toggle is best supported on `google_genai`.

### 3) streaming + thinking_off + cache_implicit_reuse

- **When to use:** Ongoing chat sessions with repeated context that can be prefixed each request.
- **Sample prompt_template:**
```text
Using the context for {{dataset_name}}, provide the top 5 operational fixes for {{goal}}.
```
- **Sample variables:**
```json
{
  "dataset_name": "incident_postmortems_platform_ops",
  "goal": "reduce mean time to recovery",
  "data_context": "Postmortems cover incident timeline, blast radius, root cause class, and mitigation actions."
}
```
- **Expected behavior:** Faster than cache_none for repeated long prefixes.
- **Stack compatibility notes:** Works across all stacks as prompt-prefix reuse.

### 4) streaming + thinking_on + cache_implicit_reuse

- **When to use:** Interactive expert assistant with repeated domain context and deeper reasoning.
- **Sample prompt_template:**
```text
Given {{dataset_name}}, reason deeply and propose a staged roadmap for {{goal}} with quick wins and long-term changes.
```
- **Sample variables:**
```json
{
  "dataset_name": "legal_case_digest_repository",
  "goal": "improve precedent retrieval accuracy",
  "data_context": "Case digest includes jurisdiction, issue tags, citation graph snippets, and summary quality labels."
}
```
- **Expected behavior:** High quality with moderate latency; cache reuse reduces repeated context overhead.
- **Stack compatibility notes:** Thinking best on `google_genai`; implicit reuse works everywhere.

### 5) streaming + thinking_off + cache_explicit_cache

- **When to use:** Real-time UX with a large, stable context corpus reused frequently.
- **Sample prompt_template:**
```text
From {{dataset_name}}, return concise recommendations for {{goal}} with one metric per recommendation.
```
- **Sample variables:**
```json
{
  "dataset_name": "product_docs_and_runbooks",
  "goal": "improve support deflection rate",
  "data_context": "Extensive static corpus: product docs, onboarding guides, troubleshooting runbooks, and changelog notes."
}
```
- **Expected behavior:** Strong TTFT reduction for repeated long context workloads.
- **Stack compatibility notes:** Explicit cache controls are primarily available on `google_genai`.

### 6) streaming + thinking_on + cache_explicit_cache

- **When to use:** Expert-level interactive workflows with large static context + reasoning.
- **Sample prompt_template:**
```text
Using {{dataset_name}}, provide a reasoned architecture decision memo for {{goal}} including trade-offs and risks.
```
- **Sample variables:**
```json
{
  "dataset_name": "engineering_design_archive",
  "goal": "standardize service-to-service auth migration",
  "data_context": "Design archive includes ADRs, service contracts, compliance constraints, and migration incident notes."
}
```
- **Expected behavior:** Better reasoning quality with reduced repeated-context overhead.
- **Stack compatibility notes:** Best on `google_genai`; explicit cache may be unsupported in other stacks.

### 7) non_streaming + thinking_off + cache_none

- **When to use:** Batch generation where users do not need token-by-token output.
- **Sample prompt_template:**
```text
Summarize {{dataset_name}} and produce a compact action checklist for {{goal}}.
```
- **Sample variables:**
```json
{
  "dataset_name": "weekly_marketing_performance",
  "goal": "improve paid channel efficiency",
  "data_context": "Campaign data contains spend, conversion funnel metrics, and region-level attribution reports."
}
```
- **Expected behavior:** Simpler execution path, no progressive output.
- **Stack compatibility notes:** Works across all stacks.

### 8) non_streaming + thinking_on + cache_none

- **When to use:** Offline analysis jobs where reasoning depth matters more than TTFT.
- **Sample prompt_template:**
```text
For {{dataset_name}}, provide a reasoned diagnosis and remediation plan for {{goal}}, including assumptions.
```
- **Sample variables:**
```json
{
  "dataset_name": "finance_close_cycle_exceptions",
  "goal": "reduce month-end reconciliation delays",
  "data_context": "Exception logs include ledger mismatches, owner teams, aging buckets, and resolution patterns."
}
```
- **Expected behavior:** Higher latency, higher analytic quality.
- **Stack compatibility notes:** Thinking support strongest on `google_genai`.

### 9) non_streaming + thinking_off + cache_implicit_reuse

- **When to use:** Batch jobs with repeated shared context but low-reasoning requirements.
- **Sample prompt_template:**
```text
Using {{dataset_name}}, generate a deterministic summary and recommendations for {{goal}}.
```
- **Sample variables:**
```json
{
  "dataset_name": "knowledge_base_quality_audit",
  "goal": "identify stale articles and ownership gaps",
  "data_context": "Audit snapshot includes article freshness, broken links, unresolved feedback, and owner metadata."
}
```
- **Expected behavior:** Better throughput for repeated requests than cache_none.
- **Stack compatibility notes:** Compatible across all stacks.

### 10) non_streaming + thinking_on + cache_implicit_reuse

- **When to use:** Deep offline analysis across repeated legal/technical context.
- **Sample prompt_template:**
```text
Based on {{dataset_name}}, provide a structured legal risk review for {{goal}} with mitigation options.
```
- **Sample variables:**
```json
{
  "dataset_name": "vendor_contract_clause_library",
  "goal": "reduce indemnity and data residency risk exposure",
  "data_context": "Clause library includes fallback language, jurisdiction exceptions, and prior negotiation outcomes."
}
```
- **Expected behavior:** Strong analytical output, moderate latency improvements from context reuse.
- **Stack compatibility notes:** Thinking best on `google_genai`.

### 11) non_streaming + thinking_off + cache_explicit_cache

- **When to use:** High-volume backend processing with stable large context and strict throughput goals.
- **Sample prompt_template:**
```text
For {{dataset_name}}, generate a normalized issue list and owner-ready actions for {{goal}}.
```
- **Sample variables:**
```json
{
  "dataset_name": "codebase_static_analysis_reports",
  "goal": "prioritize reliability fixes for next sprint",
  "data_context": "Static analysis output includes rule IDs, file paths, severity, and historical suppression records."
}
```
- **Expected behavior:** Good throughput gains when cache can be reused over many requests.
- **Stack compatibility notes:** Explicit cache is mainly `google_genai` focused.

### 12) non_streaming + thinking_on + cache_explicit_cache

- **When to use:** Heavy expert reports (e.g., compliance or architecture) over very large stable corpora.
- **Sample prompt_template:**
```text
Use {{dataset_name}} to produce a detailed compliance readiness assessment for {{goal}} with phased remediation.
```
- **Sample variables:**
```json
{
  "dataset_name": "security_control_evidence_repository",
  "goal": "prepare SOC2 gap-closure plan",
  "data_context": "Evidence repository contains policy docs, control test logs, auditor notes, and system ownership maps."
}
```
- **Expected behavior:** Best depth and consistency for large-context, repeat-heavy report generation.
- **Stack compatibility notes:** Best with `google_genai` explicit cache support; verify alternatives per stack.

### Quick Compatibility Summary

- `google_genai`: best coverage for streaming/non-streaming, thinking control, and explicit cache.
- `openai_compat`: good for baseline chat-style calls; explicit cache and thinking controls may be limited.
- `vertex_api`: supports production endpoint integration; explicit cache and thinking controls depend on endpoint capability and API path.

## How Recommendation Is Computed

For every benchmark run, the backend:

1. Computes scenario metrics (`ttft_p50_s`, `ttft_p95_s`, `e2e_p50_s`, success/error counts).
2. Applies an eligibility gate (minimum success quality, required TTFT metric).
3. Scores eligible scenarios with objective-aware weights:
   - `lowest_latency`: mostly TTFT-focused.
   - `balanced`: TTFT + tail latency + E2E + reliability.
   - `reliability_first`: reliability-heavy with latency as secondary.
4. Returns:
   - `best_scenario_id`
   - `ranked_scenarios`
   - `disqualified_scenarios` with reasons
   - `reliability_score` and confidence label

Interpretation guide:

- Prefer rows labeled `eligible`.
- Treat `unstable`/`disqualified` rows as non-default candidates until failure causes are fixed.
- Compare winner vs runner-up before rollout to avoid overfitting to one run.

## Project Layout

- `frontend/` - React + Vite app
- `backend/` - FastAPI API + benchmark engine + multi-agent layer

## Run Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Run Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend expects backend at `http://localhost:8000`.

## API Endpoints

- `GET /api/health`
- `GET /api/benchmark/default-modes`
- `POST /api/prompt/preview`
- `POST /api/prompt/token-count` (exact provider token count)
- `POST /api/prompt/optimize`
- `POST /api/prompt/optimize-and-benchmark`
- `POST /api/prompt/upload-context`
- `POST /api/benchmark/run`
- `GET /api/benchmark/history`

For `vertex_api`, send `vertex_config` with:

- `project_id`
- `location` (e.g. `us-central1`)
- `endpoint_id` (use `openapi` for Gemini OpenAPI endpoint on Vertex)
- `access_token` (optional; if omitted, backend uses ADC via `google-auth`)

## Run with Docker Compose

```bash
cd products/gemini-benchmark-studio
docker compose up --build
```

Services:

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`

Stop services:

```bash
docker compose down
```

## Validation Playbook

Run this sequence after setup:

1. `GET /api/health` should return `{"status":"ok"}`.
2. `GET /api/benchmark/default-modes` should return defaults.
3. `POST /api/prompt/preview` with your template/variables.
4. `POST /api/prompt/token-count` for mode-aware token economics.
5. `POST /api/benchmark/run` with `trials=3` for a quick smoke benchmark.
6. Open UI results and confirm:
   - ranked scenarios are present
   - disqualified reasons are understandable
   - best scenario can be applied to form controls.

## Run Tests

Backend:

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pytest tests
```

Frontend build check:

```bash
cd frontend
npm install
npm run build
```

## Notes

- This app is independent from tutorial benchmark code.
- API keys are used in-memory per request and never written to output files.
- Run history persists benchmark metadata only; request snapshots exclude `api_key`.
