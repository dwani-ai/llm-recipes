from openai import OpenAI
import os


#os.environ["GEMINI_API_KEY"] = "YOUR_GEMINI_API_KEY"

client = OpenAI(
    api_key=os.environ["GEMINI_API_KEY"],
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)


response = client.chat.completions.create(
    model="gemini-2.0-flash",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Explain how large language models work in simple terms."},
    ],
)

print(response.choices[0].message.content)
