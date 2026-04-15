# Gemini TTFT Benchmark (Flash 2.5+)

This benchmark measures Gemini response latency for:

- Streaming vs non-streaming
- Thinking mode off vs on
- Cache strategy: none, implicit reuse, explicit cache
- Model families: Flash 2.5+ and Pro
- API stacks: `google-genai` and OpenAI-compatible Gemini endpoint

## What is measured

- `ttft_s`: time-to-first-token/chunk
  - Streaming: measured when first chunk arrives.
  - Non-streaming: proxy value measured when full payload arrives.
- `e2e_s`: full request latency
- `tokens_per_s`: completion throughput estimate
- P50/P95/P99 summaries per scenario
- Error and unsupported-feature counts

## Setup

From repository root:

```bash
pip install -r tutorials/inference/requirements.txt
export GEMINI_API_KEY="your_key"
```

## Run

Default matrix (both stacks):

```bash
python tutorials/inference/day_1/gemini_ttft_benchmark.py
```

Run only Google GenAI stack:

```bash
python tutorials/inference/day_1/gemini_ttft_benchmark.py --stack google_genai
```

Run only selected models:

```bash
python tutorials/inference/day_1/gemini_ttft_benchmark.py --models gemini-2.5-flash,gemini-2.5-pro
```

Run streaming-only quick pass:

```bash
python tutorials/inference/day_1/gemini_ttft_benchmark.py --streaming-only --trials 4
```

Use custom config:

```bash
python tutorials/inference/day_1/gemini_ttft_benchmark.py --config tutorials/inference/day_1/benchmark_config.yaml
```

## Output files

Each run writes timestamped artifacts under `outputs/gemini_ttft/<run_id>/`:

- `raw_results.jsonl`: per-request raw records
- `summary.json`: aggregated scenario metrics
- `summary.csv`: table-friendly summary
- `report.md`: ranked scenarios + speed alternatives

## Notes on feature coverage

- `google_genai` adapter attempts thinking + explicit cache support.
- `openai_compat` adapter is a baseline path and marks unsupported combinations clearly (thinking toggle and explicit cache).
- For explicit cache runs, if the SDK cache API is unavailable, scenarios are logged as `unsupported`.

## Fast-response alternatives to test and apply

- Prefer Flash for latency-sensitive turns; route to Pro only for high-complexity prompts.
- Keep streaming on for interactive UX.
- Disable thinking by default and enable it selectively.
- Reuse stable long prefixes with implicit or explicit cache strategy.
- Reuse SDK clients and warm up model routes before measurements.
- Bound output with lower max tokens and stop conditions.
- Parallelize retrieval/tooling before generation where architecture allows.
