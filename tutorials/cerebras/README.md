Cerebras - 

- https://www.cerebras.ai/


- export CEREBRAS_API_KEY=""


- export BASE_URL = https://api.cerebras.ai/v1


- pip install -r requirements.txt

- python main.py

- https://inference-docs.cerebras.ai/introduction

- Inference code 
    - https://github.com/Cerebras/inference-examples/blob/main/getting-started/README.md


- Pruned models / REAP
    - https://huggingface.co/collections/cerebras/cerebras-reap


- tool_use- https://inference-docs.cerebras.ai/capabilities/tool-use


- Cursor Integration


## Option 1: Simple custom model (recommended)

1. Get a Cerebras API key  
   - Create an account and key at Cerebras Code / Cerebras API dashboard. [cerebras](https://www.cerebras.ai/blog/introducing-cerebras-code)

2. Add Cerebras as a custom model in Cursor  
   - Open **Cursor → Settings → Language Models → Custom Models**. [datacamp](https://www.datacamp.com/tutorial/cursor-ai-code-editor)
   - Add a new model with something like:  
     - **Base URL**: `https://api.cerebras.ai/v1` [forum.cursor](https://forum.cursor.com/t/when-will-incorporate-cerebras-inference/14716)
     - **API key**: your Cerebras key. [forum.cursor](https://forum.cursor.com/t/when-will-incorporate-cerebras-inference/14716)
     - **Model**: for example `qwen-3-coder-480b` or another Cerebras code model you want to use. [cerebras](https://www.cerebras.ai/blog/introducing-cerebras-code)

3. Use it inside Cursor  
   - In the model dropdown (chat, inline `Cmd+K` / `Ctrl+K`, and Composer), select the Cerebras model you just added. [datacamp](https://www.datacamp.com/tutorial/cursor-ai-code-editor)
   - Use Cursor as usual for chat, inline edits, and autocomplete; it will call Cerebras through the OpenAI‑compatible endpoint. [datacamp](https://www.datacamp.com/tutorial/cursor-ai-code-editor)

## Option 2: Cerebras Code MCP server (advanced)

If you want a “planner + executor” setup (e.g., plan with Claude/Cursor, apply code edits with Cerebras), use the Cerebras Code MCP server. [github](https://github.com/Cerebras/cerebras-code-mcp)

1. Install MCP server  
   - Clone `Cerebras/cerebras-code-mcp` from GitHub and follow the README to install dependencies and configure environment variables (including the Cerebras API key). [github](https://github.com/Cerebras/cerebras-code-mcp)

2. Configure MCP in Cursor  
   - In Cursor’s MCP settings (Tools / MCP section), register the Cerebras Code MCP server following the repo instructions (command to start server and JSON config). [github](https://github.com/Cerebras/cerebras-code-mcp)
   - This gives Cursor a tool that can send code‑change requests to Cerebras while still using your primary model for planning. [github](https://github.com/Cerebras/cerebras-code-mcp)

3. Workflow pattern  
   - Let Cursor/Claude reason about the change.  
   - The MCP server calls Cerebras (e.g., Qwen 3 Coder) to generate and apply edits, giving you fast, large‑context code modifications. [cerebras](https://www.cerebras.ai/blog/introducing-cerebras-code)

## Quick checklist

- [ ] Cerebras account + API key created. [cerebras](https://www.cerebras.ai/blog/introducing-cerebras-code)
- [ ] Custom model in Cursor: base URL `https://api.cerebras.ai/v1`, model name set, key added. [forum.cursor](https://forum.cursor.com/t/when-will-incorporate-cerebras-inference/14716)
- [ ] (Optional) Cerebras Code MCP server installed and registered in Cursor for planner/executor workflows. [github](https://github.com/Cerebras/cerebras-code-mcp)

If you tell what OS you’re on (macOS/Windows/Linux) and whether you want simple or MCP setup, a concrete step‑by‑step with exact commands can be outlined.