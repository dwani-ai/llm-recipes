Prime RL

https://github.com/PrimeIntellect-ai/prime-rl

curl -LsSf https://astral.sh/uv/install.sh | sh

 uv venv venv

source venv/bin/activate

uv sync && uv sync --all-extras


Test Environment

```bash
uv run python -V

uv run python -c "import flash_attn"

uv run sft @ configs/debug/sft/train.toml

uv run trainer @ configs/debug/rl/train.toml

uv run inference @ configs/debug/infer.toml

uv run orchestrator @ configs/debug/orch.toml


uv run eval @ configs/debug/eval.toml
```


---

Trials

python3.10 -m venv venv
source venv/bin/activate

pip install vllm
vllm serve PrimeIntellect/Qwen3-0.6B --gpu-memory-utilization 0.7 --max-model-len 4096

uv sync && uv sync --all-extras

export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

uv run sft @ configs/debug/sft/train.toml

uv run trainer @ configs/debug/rl/train.toml

uv run inference @ configs/debug/infer.toml


- Run orchestrator with inference
  - uv run orchestrator @ configs/debug/orch.toml

--


facebook/opt-125m

LiquidAI/LFM2-350M

facebook/MobileLLM-R1-140M  - does not support - flash-attn

HuggingFaceTB/SmolLM-135M


---
sudo apt install tmux

Running - reverse-text

uv run python -c "import reverse_text"


 uv run inference --model.name HuggingFaceTB/SmolLM2-135M-Instruct

uv run vf-eval reverse-text -m HuggingFaceTB/SmolLM2-135M-Instruct -b http://localhost:8000/v1 -n 20 --max-tokens 1024


uv run sft @ examples/reverse_text/sft/train.toml

---
Wordle

uv pip install prime
prime env install will/wordle

uv run inference --model.name HuggingFaceTB/SmolLM2-135M-Instruct

# Run this in the `Trainer` pane
uv run vf-eval wordle -m HuggingFaceTB/SmolLM2-135M-Instruct -b http://localhost:8000/v1 -n 20 --max-tokens 1024

-- 
sft 

uv run sft @ examples/wordle/sft/train.toml

# In the `Trainer` pane
uv run sft @ examples/wordle/sft/train.toml \
  --wandb.project ... \
  --wandb.name ... \
  --weights


uv run sft @ examples/wordle/sft/train.toml --wandb.project dwani.ai --wandb.name wordle-sft --weights

 uv run hf upload <user>/Qwen3-1.7B-Wordle-SFT outputs/weights/step_20

 uv run hf upload gaganyatri/SmolLM2-135M-Instruct-Wordle-SFT outputs/weights/step_20 

---

# Run this in the `Trainer` pane
uv run rl \
  --trainer @ examples/wordle/rl/train.toml \
  --orchestrator @ examples/wordle/rl/orch.toml \
  --inference @ examples/wordle/rl/infer.toml \
  --model.name gaganyatri/SmolLM2-135M-Instruct-Wordle-SFT \
  --wandb.project dwani.ai \
  --wandb.name wordle-rl