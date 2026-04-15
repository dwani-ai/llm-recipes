import time
def inference_latency(n_prompt, n_output=10):
    t0 = time.time()
    time.sleep(0.001 * n_prompt)  # prefill ~1ms/token
    ttft = time.time() - t0
    for _ in range(n_output):
        time.sleep(0.02)  # decode ~20ms/token
    total = time.time() - t0
    return ttft, total - ttft

ttft, itl_total = inference_latency(100)
print(f"TTFT: {ttft:.3f}s, ITL total: {itl_total:.3f}s")


ttft, itl_total = inference_latency(1000)


print(f"TTFT: {ttft:.3f}s, ITL total: {itl_total:.3f}s")


ttft, itl_total = inference_latency(3000)
print(f"TTFT: {ttft:.3f}s, ITL total: {itl_total:.3f}s")