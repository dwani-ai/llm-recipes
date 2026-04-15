# Gemini TTFT Benchmark Report

Generated at: `2026-04-15T09:08:03.525865+00:00`

## Fastest Scenarios By TTFT (P50)

| Rank | Scenario | TTFT P50 (s) | E2E P50 (s) | Tokens/s Avg | Notes |
| --- | --- | ---: | ---: | ---: | --- |
| 1 | google_genai|gemini-2.5-flash|streaming|thinking_False|cache_implicit_reuse|short_prompt | 1.536 | 1.536 | 1.96 | ok |
| 2 | google_genai|gemini-2.5-flash|streaming|thinking_True|cache_none|short_prompt | 1.536 | 1.537 | 1.91 | ok |
| 3 | google_genai|gemini-2.5-flash|streaming|thinking_False|cache_none|short_prompt | 1.543 | 1.543 | 1.89 | ok |
| 4 | google_genai|gemini-2.5-flash|streaming|thinking_False|cache_implicit_reuse|long_context | 1.638 | 1.638 | 2.58 | ok |
| 5 | google_genai|gemini-2.5-flash|streaming|thinking_True|cache_implicit_reuse|long_context | 1.643 | 1.644 | 2.47 | ok |
| 6 | google_genai|gemini-2.5-flash|streaming|thinking_True|cache_implicit_reuse|short_prompt | 1.645 | 1.645 | 1.80 | ok |
| 7 | google_genai|gemini-2.5-flash|streaming|thinking_True|cache_none|long_context | 2.048 | 2.048 | 1.62 | ok |
| 8 | google_genai|gemini-2.5-flash|streaming|thinking_False|cache_none|long_context | 2.113 | 2.114 | 1.80 | ok |
| 9 | google_genai|gemini-2.5-flash|streaming|thinking_False|cache_explicit_cache|short_prompt | n/a | n/a | n/a | unsupported=50 |
| 10 | google_genai|gemini-2.5-flash|streaming|thinking_False|cache_explicit_cache|long_context | n/a | n/a | n/a | unsupported=50 |

## Alternatives To Improve Response Speed

- Use Flash models for latency-critical paths and route to Pro only on difficult prompts.
- Prefer streaming so users see output as soon as the first chunk arrives.
- Keep thinking disabled by default; enable it only when reasoning depth is needed.
- Reuse long shared prefixes with implicit cache-like prompting or explicit cache APIs.
- Pre-warm clients and avoid creating new SDK clients per request.
- Reduce max output tokens and apply stop sequences for bounded completions.
- Parallelize retrieval/tool calls before generation to reduce critical-path latency.
- Keep prompts concise and move stable instructions into reusable templates.
