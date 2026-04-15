from transformers import pipeline
import time
import numpy as np
generator = pipeline("text-generation", model="distilgpt2")
prompts = ["Short: Hi"] * 20 + ["Long: Explain LLM inference in detail including TTFT optimization."] * 20
ttfts = []
for p in prompts:
    t0 = time.time()
    out = generator(p, max_new_tokens=5)
    ttfts.append(time.time() - t0)
print(f"P50 TTFT: {np.percentile(ttfts, 50):.3f}s, P95: {np.percentile(ttfts, 95):.3f}s")