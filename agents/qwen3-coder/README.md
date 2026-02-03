Qwen 3 Coder

- Model Name  : qwen3-coder 
- GPU : A100 with 80GB


- pip install -r requirements.txt

curl -X POST "https://YOUR_BASE_URL/v1/chat/completions" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3-coder",
    "messages": [
      {
        "role": "user",
        "content": "Say hello"
      }
    ],
    "max_tokens": 128,
    "temperature": 0.2
  }'
