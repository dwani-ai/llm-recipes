# 1. Fix: The function must accept the parameter name defined in the schema
def square_the_number(input_num: float) -> dict:
    return {"result": input_num ** 2}


# 2. Better / more standard tool definition (OpenAI-compatible)
tools = [
    {
        "type": "function",
        "function": {
            "name": "square_the_number",
            "description": "Returns the square of the given number.",
            "parameters": {
                "type": "object",
                "properties": {
                    "input_num": {
                        "type": "number",
                        "description": "The number to square"
                    }
                },
                "required": ["input_num"],
                "additionalProperties": False
            }
        }
    }
]


# 3. Correct client initialization for Qwen (OpenAI-compatible endpoint)
from openai import OpenAI
import os

# Replace with your actual endpoint
QWEN_API_BASE = os.getenv("QWEN_API_BASE", "https://your-qwen-endpoint.example.com/v1")

client = OpenAI(
    base_url=QWEN_API_BASE,
    api_key="EMPTY",           # most local / open-source servers accept empty or dummy key
)


messages = [
    {"role": "system",    "content": "You are a helpful math assistant. Use the provided tool when asked to square a number."},
    {"role": "user",      "content": "square the number 1024"}
]


completion = client.chat.completions.create(
    model="qwen3-coder",           # or "qwen2.5-coder-32b", "qwen-max", etc — depending on what your server has
    messages=messages,
    tools=tools,
    tool_choice="auto",            # or "required" if you want to force tool use
    temperature=0.1,
    max_tokens=1024,
)


# ────────────────────────────────────────────────
# How to handle the response (most important part)
# ────────────────────────────────────────────────

choice = completion.choices[0]
message = choice.message

print("Role:", message.role)
print("Content:", message.content)

if message.tool_calls:
    print("\nTool calls found:")
    for tc in message.tool_calls:
        print("  Function name:", tc.function.name)
        print("  Arguments   :", tc.function.arguments)
        print("  Tool call id :", tc.id)
else:
    print("\nNo tool call → model answered directly")