Setup environment

python -m venv venv
source venv/bin/activate

pip install vllm flashinfer-python xformers

vllm serve --gpu-memory-utilization 0.5 --max-model-len 2048


vllm serve Qwen3-4B-Instruct-2507

vllm serve Qwen/Qwen3-4B-Thinking-2507-FP8


https://qwen.readthedocs.io/en/latest/deployment/vllm.html


ASR ? - https://docs.vllm.ai/en/latest/models/supported_models.html#transcription

https://modal.com/notebooks/modal-labs/_/nb-x2wXrLH7aqi7HGVQ8Fosh2


https://pytorch.org/blog/disaggregated-inference-at-scale-with-pytorch-vllm/

https://www.aleksagordic.com/blog/vllm


https://github.com/vllm-project/production-stack


https://docs.vllm.ai/projects/production-stack/en/latest/