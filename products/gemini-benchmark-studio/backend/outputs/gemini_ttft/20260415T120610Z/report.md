# Gemini TTFT Benchmark Report

Generated at: `2026-04-15T12:07:03.491415+00:00`

## Fastest Scenarios By TTFT (P50)

| Rank | Scenario | TTFT P50 (s) | E2E P50 (s) | Tokens/s Avg | Notes |
| --- | --- | ---: | ---: | ---: | --- |
| 1 | google_genai|gemini-2.5-flash|streaming|thinking_False|cache_none|long_context | 1.284 | 1.795 | 49.27 | ok |
| 2 | google_genai|gemini-2.5-flash|streaming|thinking_False|cache_none|short_prompt | 1.338 | 1.844 | 45.12 | ok |
| 3 | google_genai|gemini-2.5-flash|streaming|thinking_False|cache_explicit_cache|short_prompt | n/a | n/a | n/a | unsupported=10 |
| 4 | google_genai|gemini-2.5-flash|streaming|thinking_False|cache_explicit_cache|long_context | n/a | n/a | n/a | unsupported=10 |
