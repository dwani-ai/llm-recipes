# Gemini TTFT Benchmark Report

Generated at: `2026-04-15T07:47:33.416025+00:00`

## Fastest Scenarios By TTFT (P50)

| Rank | Scenario | TTFT P50 (s) | E2E P50 (s) | Tokens/s Avg | Notes |
| --- | --- | ---: | ---: | ---: | --- |
| 1 | google_genai|gemini-2.5-flash|streaming|thinking_False|cache_none|short_prompt | n/a | n/a | n/a | errors=1 |
| 2 | google_genai|gemini-2.5-flash|streaming|thinking_False|cache_none|long_context | n/a | n/a | n/a | errors=1 |
| 3 | google_genai|gemini-2.5-flash|streaming|thinking_False|cache_implicit_reuse|short_prompt | n/a | n/a | n/a | errors=1 |
| 4 | google_genai|gemini-2.5-flash|streaming|thinking_False|cache_implicit_reuse|long_context | n/a | n/a | n/a | errors=1 |
| 5 | google_genai|gemini-2.5-flash|streaming|thinking_False|cache_explicit_cache|short_prompt | n/a | n/a | n/a | errors=1 |
| 6 | google_genai|gemini-2.5-flash|streaming|thinking_False|cache_explicit_cache|long_context | n/a | n/a | n/a | errors=1 |
| 7 | google_genai|gemini-2.5-flash|streaming|thinking_True|cache_none|short_prompt | n/a | n/a | n/a | errors=1 |
| 8 | google_genai|gemini-2.5-flash|streaming|thinking_True|cache_none|long_context | n/a | n/a | n/a | errors=1 |
| 9 | google_genai|gemini-2.5-flash|streaming|thinking_True|cache_implicit_reuse|short_prompt | n/a | n/a | n/a | errors=1 |
| 10 | google_genai|gemini-2.5-flash|streaming|thinking_True|cache_implicit_reuse|long_context | n/a | n/a | n/a | errors=1 |

## Alternatives To Improve Response Speed

- Use Flash models for latency-critical paths and route to Pro only on difficult prompts.
- Prefer streaming so users see output as soon as the first chunk arrives.
- Keep thinking disabled by default; enable it only when reasoning depth is needed.
- Reuse long shared prefixes with implicit cache-like prompting or explicit cache APIs.
- Pre-warm clients and avoid creating new SDK clients per request.
- Reduce max output tokens and apply stop sequences for bounded completions.
- Parallelize retrieval/tool calls before generation to reduce critical-path latency.
- Keep prompts concise and move stable instructions into reusable templates.
