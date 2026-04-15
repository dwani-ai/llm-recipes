# Gemini TTFT Benchmark Report

Generated at: `2026-04-15T08:18:03.425599+00:00`

## Fastest Scenarios By TTFT (P50)

| Rank | Scenario | TTFT P50 (s) | E2E P50 (s) | Tokens/s Avg | Notes |
| --- | --- | ---: | ---: | ---: | --- |
| 1 | google_genai|gemini-2.5-flash|streaming|thinking_False|cache_implicit_reuse|short_prompt | 1.434 | 1.434 | 2.02 | ok |
| 2 | google_genai|gemini-2.5-flash|streaming|thinking_False|cache_none|short_prompt | 1.487 | 1.488 | 1.94 | ok |
| 3 | google_genai|gemini-2.5-flash|streaming|thinking_True|cache_none|short_prompt | 1.536 | 1.536 | 1.99 | ok |
| 4 | google_genai|gemini-2.5-flash|streaming|thinking_True|cache_implicit_reuse|short_prompt | 1.536 | 1.536 | 1.92 | ok |
| 5 | google_genai|gemini-2.5-flash|streaming|thinking_True|cache_implicit_reuse|long_context | 1.536 | 1.536 | 2.49 | ok |
| 6 | openai_compat|gemini-2.5-flash|streaming|thinking_False|cache_implicit_reuse|short_prompt | 1.791 | 1.791 | 1.74 | ok |
| 7 | openai_compat|gemini-2.5-flash|streaming|thinking_False|cache_none|short_prompt | 1.805 | 1.805 | 1.57 | ok |
| 8 | openai_compat|gemini-2.5-flash|streaming|thinking_True|cache_implicit_reuse|long_context | 1.843 | 1.843 | 1.82 | ok |
| 9 | openai_compat|gemini-2.5-flash|streaming|thinking_False|cache_implicit_reuse|long_context | 1.844 | 1.844 | 1.78 | ok |
| 10 | openai_compat|gemini-2.5-flash|streaming|thinking_True|cache_implicit_reuse|short_prompt | 1.848 | 1.849 | 1.50 | ok |

## Alternatives To Improve Response Speed

- Use Flash models for latency-critical paths and route to Pro only on difficult prompts.
- Prefer streaming so users see output as soon as the first chunk arrives.
- Keep thinking disabled by default; enable it only when reasoning depth is needed.
- Reuse long shared prefixes with implicit cache-like prompting or explicit cache APIs.
- Pre-warm clients and avoid creating new SDK clients per request.
- Reduce max output tokens and apply stop sequences for bounded completions.
- Parallelize retrieval/tool calls before generation to reduce critical-path latency.
- Keep prompts concise and move stable instructions into reusable templates.
