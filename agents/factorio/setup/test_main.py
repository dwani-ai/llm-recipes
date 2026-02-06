from openai import OpenAI


import os 
client = OpenAI(
    api_key=os.environ["QWEN_API_KEY"],
    base_url=os.environ["QWEN_BASE_URL"],
)


def ask_llm(prompt: str, max_tokens: int = 200):
    try:
        response = client.chat.completions.create(
            model="qwen3-coder",  # or whatever alias/model name your server uses
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.7,      # optional - adjust as needed
            top_p=0.9,
            # stream=False,       # set to True later if you want streaming
        )

        # Extract the generated text
        content = response.choices[0].message.content.strip()

        print("Response from model:")
        print("-" * 70)
        print(content)
        print("-" * 70)

        # Optional: show usage stats
        print("\nUsage:", response.usage)

        return content

    except Exception as e:
        print(f"Error calling LLM: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print("Response details:", e.response.text)
        return None


if __name__ == "__main__":
    prompt = "Write a Python function to reverse a string"
    result = ask_llm(prompt, max_tokens=200)