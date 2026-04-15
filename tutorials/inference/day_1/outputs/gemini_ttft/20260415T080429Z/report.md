# Gemini TTFT Benchmark Report

Generated at: `2026-04-15T08:04:29.938976+00:00`

## Fastest Scenarios By TTFT (P50)

| Rank | Scenario | TTFT P50 (s) | E2E P50 (s) | Tokens/s Avg | Notes |
| --- | --- | ---: | ---: | ---: | --- |

## Alternatives To Improve Response Speed

- Use Flash models for latency-critical paths and route to Pro only on difficult prompts.
- Prefer streaming so users see output as soon as the first chunk arrives.
- Keep thinking disabled by default; enable it only when reasoning depth is needed.
- Reuse long shared prefixes with implicit cache-like prompting or explicit cache APIs.
- Pre-warm clients and avoid creating new SDK clients per request.
- Reduce max output tokens and apply stop sequences for bounded completions.
- Parallelize retrieval/tool calls before generation to reduce critical-path latency.
- Keep prompts concise and move stable instructions into reusable templates.
