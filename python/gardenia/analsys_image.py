# main.py
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
import httpx
import base64
import os
from pydantic import BaseModel
from typing import List, Dict, Any
import asyncio

app = FastAPI(title="Lawn Care Advisor API",
              description="Upload a lawn photo → get detailed JSON maintenance plan",
              version="1.0")

# === CONFIGURATION ===
# Set your OpenAI API key (or use Anthropic/Gemini by changing the client)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("Please set OPENAI_API_KEY environment variable")

headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
client = httpx.AsyncClient(timeout=60.0)

# === STEP 1: Image Description Prompt ===
DESCRIPTION_PROMPT = """
You are an expert in visual analysis of gardens and landscapes.  
Look very carefully at the attached photograph and write a short, precise, factual description (2–4 sentences only) of exactly what is visible.  

Include these details:
- Overall size and shape of the lawn area чет
- Grass condition (patchy, thin, healthy, dormant, etc.)
- Any bare soil, dug-up strips, or dead patches and their size/location
- Weeds, moss, leaves, or debris present
- Slopes, uneven ground, fencing, structures, or hardscaping
- Apparent season and any seasonal clues
- Any other notable objects or problems

Do NOT give advice or opinions — just describe what you actually see.
"""

# === STEP 2: Full Lawn Care Plan Prompt (System + User) ===
SYSTEM_PROMPT = """
You are an expert horticulturist and lawn-care specialist.  
The user will provide a photograph and an accurate description of a residential lawn/garden. 
Your task is to provide a complete, practical, step-by-step lawn restoration and maintenance plan tailored exactly to the photo and description.
"""

USER_PROMPT_TEMPLATE = """
Please analyse the attached photograph of my backyard lawn in detail and give me a complete step-by-step plan to restore and maintain it.

The photo shows: {description}

Current season appears to be late autumn/early winter (November) unless contradicted. Assume a temperate climate (cool-season grasses) unless the image clearly suggests otherwise.

Provide your final response as valid JSON only (no markdown, no explanations outside JSON) using this exact structure:

{
  "overall_assessment": "One-paragraph summary of current lawn condition",
  "recommended_actions": [
    {
      "step_number": 1,
      "title": "Short action title",
      "why": "Why this step is needed",
      "how_to_do_it": "Detailed instructions",
      "tools_and_materials": ["item 1", "item 2", "..."],
      "best_timing": "When to do it (e.g., immediately, next spring, etc.)",
      "notes": "Optional extra tips or warnings"
    }
    // ... more steps
  ],
  "ongoing_maintenance": "Brief monthly/seasonal care summary"
}
"""

class Step(BaseModel):
    step_number: int
    title: str
    why: str
    how_to_do_it: str
    tools_and_materials: List[str]
    best_timing: str
    notes: str | None = None

class LawnPlanResponse(BaseModel):
    overall_assessment: str
    recommended_actions: List[Step]
    ongoing_maintenance: str

def encode_image(file_content: bytes) -> str:
    return base64.b64encode(file_content).decode('utf-8')

async def call_openai_vision(messages: List[Dict]) -> str:
    payload = {
        "model": "gpt-4o-mini",  # or "gpt-4o" for maximum quality
        "messages": messages,
        "max_tokens": 1500
    }
    response = await client.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail=f"OpenAI error: {response.text}")
    return response.json()["choices"][0]["message"]["content"]

@app.post("/analyze-lawn")
async def analyze_lawn(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    image_bytes = await file.read()
    base64_image = encode_image(image_bytes)
    image_url = f"data:{file.content_type};base64,{base64_image}"

    # === STEP 1: Get accurate description ===
    desc_messages = [
        {"role": "system", "content": DESCRIPTION_PROMPT},
        {"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": image_url}},
            {"type": "text", "text": "Describe only what you see."}
        ]}
    ]
    description = await call_openai_vision(desc_messages)
    description = description.strip().strip('"')

    # === STEP 2: Get full structured plan ===
    user_prompt = USER_PROMPT_TEMPLATE.format(description=description)

    plan_messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": image_url}},
            {"type": "text", "text": user_prompt}
        ]}
    ]

    raw_json = await call_openai_vision(plan_messages)

    # Clean and parse JSON
    import json, re
    json_match = re.search(r"\{.*\}", raw_json, re.DOTALL)
    if not json_match:
        raise HTTPException(status_code=500, detail="Failed to extract JSON from model response")
    
    try:
        plan_data = json.loads(json_match.group(0))
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Invalid JSON from model: {e}")

    return JSONResponse(content=plan_data)

@app.get("/")
async def root():
    return {"message": "Lawn Care Vision API ready. POST image to /analyze-lawn"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)