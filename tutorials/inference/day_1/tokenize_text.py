import tiktoken
enc = tiktoken.get_encoding("cl100k_base")
prompt = "Explain how inference reduces TTFT in production."
tokens = enc.encode(prompt)
print(f"Prompt: {len(tokens)} tokens")


prompt_readme = """
## LLM Recipes

### Overview

**LLM Recipes** is a collection of end‑to‑end projects, tutorials, and reference implementations for working with modern large language models and multimodal systems.  
It is designed as a practical playground: start from a clean Ubuntu install, bring up local or cloud models, and build real applications across text, speech, vision, agents, and robots.

The repo is organised as a set of **recipes**:

- **Application projects** (e.g. self‑hosted audiobooks, shopping assistants, autonomous warehouse dispatcher)
- **Tutorials** that walk from “hello world” REST APIs to function calling, RAG, vision, speech, and deployment
- **Infrastructure and deployment** guides for GPUs, Docker, vLLM, llama.cpp, GH200, etc.

If you want to learn by building, this repo is meant to be your lab notebook.

---

### Main topics explored

- **RAG & retrieval**
  - Dense embeddings and vector search (e.g. Pinecone, pgvector)
  - Hybrid retrieval (BM25 + dense), re‑rankers, and DSPy‑style RAG graphs
  - Case studies like the **AI Tutor** RAG system (see `case-studies/ai-tutor`)

- **Agents**
  - Code‑focused agents such as **Qwen3 Coder** (`agents/qwen3-coder`)
  - Multi‑agent and decision agents (Factorio, Aquila, Mars‑style patterns)

- **Speech & audio**
  - Whisper‑based **speech‑to‑text** and **speech‑to‑speech** assistants (`python/assistant`)
  - **NotebookLM‑style audiobooks**: parsing scripts and generating TTS for books/long‑form content (`python/notebooklm`)
  - Indic/low‑resource TTS (Sarvam, ai4bharat) and Kimi‑style audio experiments

- **Vision & multimodal**
  - Image/scene understanding and VLMs (e.g. LLaVA, Moondream, Pixtral, Meta Llama vision)
  - VideoBook‑style pipelines such as **Divya Drishti** (`python/divya-drishti`)
  - Drone + VLM reconnaissance for battlefield mapping (`python/reconaissance`)

- **Quantisation, inference, and deployment**
  - `tutorials/llama-cpp`: quantisation and GGUF workflows with `llama.cpp`
  - `tutorials/vllm`, `tutorials/gh200`: high‑performance inference and GPU setup
  - Docker‑based deployment, Nvidia Container Toolkit, Ollama and Open WebUI integration

- **Reinforcement learning & robotics**
  - RL environments and frameworks (`reinforcement_learning/`)
  - **Bhoomi** and related robots (`robots/`) for embodied AI and trajectory planning

- **Regional and Indic AI**
  - Kannada language experiments (`kannada/`)
  - Indic translation and TTS (`tutorials/sarvam`, `tutorials/indic`)

---

### Project highlights

- **Bhoomi & robots**
  - Robotics experiments, trajectory planners, and platform notes
  - See `robots/README.md` for the Bhoomi and biryani Bot documentation

- **Notebook LLaMA (self‑hosted NotebookLM)**
  - Path: `python/notebooklm`
  - Self‑hosted platform for turning manuscripts and documents into improved audiobooks using TTS

- **Assistant & speech‑to‑speech**
  - Path: `python/assistant`
  - REST API layer over local/remote LLMs, text+vision querying, Whisper‑based speech APIs, and speech‑to‑speech inference

- **Quantisation tutorials**
  - Path: `tutorials/llama-cpp`
  - Recipes for quantising models to GGUF and running them with `llama.cpp`

- **Shopping Bot**
  - Path: `python/shopping-bot`
  - Food ordering assistant combining Pinecone + LlamaIndex with BM25 and vector retrieval

- **Divya Drishti (VideoBook)**
  - Path: `python/divya-drishti`
  - Generates visual stories (e.g. Ramayana) with Stable Diffusion and Indic TTS, orchestrated by LLM prompts

- **Reconnaissance (Drishti)**
  - Path: `python/reconaissance`
  - Drone + VLM system for mapping and describing environments using open‑weight models

For a broader index of experiments and small projects, browse `python/`, `tutorials/`, and `case-studies/`.

---

### Repository layout (high level)

- **`python/`**: main Python projects (assistant, notebooklm, shopping‑bot, divya‑drishti, reconaissance, aquila, etc.)
- **`tutorials/`**: topic‑oriented tutorials (REST APIs, function calling, RAG, vision, whisper, vLLM, GH200, llama‑cpp, Android, Indic AI, etc.)
- **`docs/`**: written docs (setup guides, deployment, quantisation, hackathons, dspy, vllm, interview prep)
- **`agents/`**: agent deployments (e.g. Qwen3 Coder, Factorio)
- **`case-studies/`**: design docs and RAG case studies (AI Tutor, insurance agent)
- **`reinforcement_learning/`**: RL experiments and notes
- **`robots/`**: Bhoomi and related robots, hardware notes
- **`kannada/`**: Kannada‑focused language experiments
- **`ui/`**: autonomous warehouse UI and voice dispatcher

---

### Getting started

#### 1. System and GPU setup (recommended)

- Follow **`docs/clean-ubuntu-setup.md`** to:
  - Install Ubuntu tooling and VS Code
  - Install Docker and Nvidia Container Toolkit
  - Install CUDA (where applicable) and GPU drivers

#### 2. Clone the repo

```bash
git clone https://github.com/<your-org-or-user>/llm-recipes.git
cd llm-recipes
```

#### 3. Choose a starting recipe

- **New to LLMs?**  
  Start with the tutorial progression in **`docs/tutorials.md`** (from simple REST APIs and local models up to speech, vision, and GUIs).

- **Want a full application?**
  - `python/notebooklm` – self‑hosted audiobooks platform
  - `python/assistant` – multi‑modal assistant with text, vision, and speech
  - `python/shopping-bot` – retrieval‑augmented shopping assistant

- **Interested in deployment/perf?**
  - `tutorials/llama-cpp` – quantisation and running models with `llama.cpp`
  - `tutorials/vllm` and `tutorials/gh200` – vLLM and GPU deployment recipes

Each project directory typically includes its own README or notebook explaining local setup and usage.

---

### Tutorials

- **Tutorial index**: see **`docs/tutorials.md`** for the progression from v0 (REST API + local LLM) through v9 (quantisation, YOLO, etc.).
- Many tutorials live under `tutorials/` and are grouped by topic or provider (e.g. `tutorials/mistral`, `tutorials/vision`, `tutorials/whisper`, `tutorials/dspy`).

---

### Extra resources

- **Ubuntu + Docker + Nvidia setup**: `docs/clean-ubuntu-setup.md`
- **Deployment, quantisation, DSPy, vLLM, etc.**: various docs under `docs/`
- **Hackathons and challenges**: `docs/hackathons.md`

---
<!-- 
### Suggestions and next steps for improvement

Some directions that would make this project even more useful:

- **Unify environment management**
  - Provide a small set of canonical environment files (e.g. `environment.yml` / `pyproject.toml` / `requirements.txt`) per major project or for the whole repo.
  - Add example `.env.example` files where secrets or API keys are required.

- **Standardise project templates**
  - Adopt a common scaffolding for new recipes (folder layout, `README`, `Makefile`/`tasks.py`).
  - Add minimal CLI entrypoints (e.g. `python -m project_name`) for each major app.

- **Improve documentation navigation**
  - Turn `docs/` into a more navigable index (or a simple static site) pointing clearly to “Start here”, “Applications”, “Tutorials”, and “Deployment”.
  - Add short summaries and tags (e.g. `#RAG`, `#vision`, `#speech`) to each project and tutorial.

- **Testing and evaluation**
  - Introduce basic smoke tests for key APIs (assistant, notebooklm, shopping‑bot).
  - Add simple evaluation harnesses for RAG (retrieval quality, latency) and agents (task success rate).

- **Examples and presets**
  - Ship ready‑to‑run Docker Compose presets for a few flagship stacks (e.g. “RAG + vLLM”, “Whisper + Assistant”, “NotebookLM full stack”).
  - Provide small sample datasets and example prompts for each major recipe.

Contributions that help in any of these areas are very welcome.
-->
---

### Acknowledgments

- Thanks to the contributors and maintainers of the third‑party libraries, models, and tools used in this project.

---

### License

This project is licensed under the MIT License – see the `LICENSE` file for details.
"""

tokens = enc.encode(prompt_readme)
print(f"Prompt: {len(tokens)} tokens")
