# Gemini TTFT Benchmark Report

Generated at: `2026-04-15T08:01:11.852282+00:00`

## Fastest Scenarios By TTFT (P50)

| Rank | Scenario | TTFT P50 (s) | E2E P50 (s) | Tokens/s Avg | Notes |
| --- | --- | ---: | ---: | ---: | --- |
| 1 | google_genai|gemini-2.5-flash|streaming|thinking_True|cache_implicit_reuse|short_prompt | 1.731 | 1.732 | 1.73 | ok |
| 2 | google_genai|gemini-2.5-flash|streaming|thinking_True|cache_implicit_reuse|long_context | 1.790 | 1.790 | 2.23 | ok |
| 3 | openai_compat|gemini-2.5-flash|streaming|thinking_True|cache_implicit_reuse|short_prompt | 1.842 | 1.842 | 1.63 | ok |
| 4 | google_genai|gemini-2.5-flash|streaming|thinking_True|cache_none|long_context | 1.850 | 1.850 | 2.16 | ok |
| 5 | google_genai|gemini-2.5-flash|streaming|thinking_False|cache_implicit_reuse|long_context | 1.940 | 1.940 | 2.06 | ok |
| 6 | google_genai|gemini-2.5-flash|streaming|thinking_False|cache_none|long_context | 1.980 | 1.980 | 2.02 | ok |
| 7 | openai_compat|gemini-2.5-flash|streaming|thinking_False|cache_none|short_prompt | 1.980 | 1.981 | 1.51 | ok |
| 8 | openai_compat|gemini-2.5-flash|streaming|thinking_False|cache_implicit_reuse|short_prompt | 1.995 | 1.996 | 1.50 | ok |
| 9 | google_genai|gemini-2.5-flash|streaming|thinking_True|cache_none|short_prompt | 2.041 | 2.042 | 1.47 | ok |
| 10 | openai_compat|gemini-2.5-flash|streaming|thinking_True|cache_none|short_prompt | 2.125 | 2.125 | 1.41 | ok |

## Alternatives To Improve Response Speed

- Use Flash models for latency-critical paths and route to Pro only on difficult prompts.
- Prefer streaming so users see output as soon as the first chunk arrives.
- Keep thinking disabled by default; enable it only when reasoning depth is needed.
- Reuse long shared prefixes with implicit cache-like prompting or explicit cache APIs.
- Pre-warm clients and avoid creating new SDK clients per request.
- Reduce max output tokens and apply stop sequences for bounded completions.
- Parallelize retrieval/tool calls before generation to reduce critical-path latency.
- Keep prompts concise and move stable instructions into reusable templates.
