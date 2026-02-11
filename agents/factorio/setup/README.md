Setup AI - Inference


mkdir models 

python3.10 -m venv venv
 
source venv/bin/activate
pip install huggingface_hub


hf download unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF   Qwen3-Coder-30B-A3B-Inst
ruct-IQ4_XS.gguf  --local-dir models/


docker run --rm --gpus all -p 8080:8080 -v $(pwd)/models:/models \
  ghcr.io/ggml-org/llama.cpp:server-cuda \
  --model /models/Qwen3-Coder-30B-A3B-Instruct-IQ4_XS.gguf \
  --host 0.0.0.0 --ctx-size 32768 --n-gpu-layers 99 --jinja



--
--


# Start the service
docker compose up -d

# Check logs
docker compose logs -f

# Test the endpoint
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3-coder",
    "messages": [{"role": "user", "content": "Write a Python function to reverse a string"}],
    "max_tokens": 200
  }'

# Stop
docker compose down
