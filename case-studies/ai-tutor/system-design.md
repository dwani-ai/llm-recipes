You should prepare to design end-to-end AI/ML features for a mobile-first, student-facing learning app: think “AI study companion / SchoolGPT-style assistant for millions of students”. [knowunity](https://knowunity.de)

## 1. Understand KnowUnity’s context

- Mission: AI-powered learning companion for school students, with personalized tutoring, notes, and study plans. [knowunity](https://knowunity.ai)
- Product: Mobile app with student-generated notes, quizzes, flashcards, and an AI tutor built on top of ~3M+ peer-created materials, localized per curriculum. [vestbee](https://vestbee.com/insights/articles/knowunity-secures-27-m)
- Scale: >20M users across 15+ countries; one in three students in Germany, fast growth in LatAm; B2C subscription + partnerships. [eu-startups](https://www.eu-startups.com/2025/06/german-edtech-startup-knowunity-raises-e27-million-to-bring-ai-tutor-to-1-billion-students/)

For system design, assume: mobile-heavy traffic, student peak hours, noisy UGC content, curriculum alignment, strong latency expectations for AI replies.

## 2. Likely system design question themes

They will likely frame problems around AI studying and tutoring at scale. [blog.openreplay](https://blog.openreplay.com/5-tips-aiml-interview-2025/)

Typical prompts (adapt to KnowUnity):

- Design a personalized AI tutor that answers questions using student-contributed notes, aligned with local curricula, for 20M+ users. [systemdesignhandbook](https://www.systemdesignhandbook.com/guides/ml-system-design/)
- Design a recommendation system for study materials and revision plans for students in multiple countries and curricula. [systemdesignhandbook](https://www.systemdesignhandbook.com/guides/machine-learning-system-design-interview/)
- Design an LLM-based chat assistant (SchoolGPT-style) integrated into the app, with safety filters, caching, and cost control. [youtube](https://www.youtube.com/watch?v=xj5Nf0-S4_0)
- Design the data/ML pipeline that turns raw user-uploaded notes into structured, searchable, and model-usable content. [vestbee](https://vestbee.com/insights/articles/knowunity-secures-27-m)

Given your background, they may push you towards LLM + retrieval + recommendations + scale.

## 3. Answer structure for AI/ML system design

Use a consistent template that works for any of the above. [igotanoffer](https://igotanoffer.com/blogs/tech/system-design-interviews)

1) Clarify requirements and constraints  
- Who are the users: students 10–19, teachers? Which markets? [portfolion](https://www.portfolion.com/companies/knowunity)
- Functional: ask questions (Q&A), get explanations, notes, revision plans, multi-language support. [eu-startups](https://www.eu-startups.com/2025/06/german-edtech-startup-knowunity-raises-e27-million-to-bring-ai-tutor-to-1-billion-students/)
- Non-functional: latency (e.g., 200–500 ms target for most actions, maybe 1–2 s for complex LLM calls), daily active users, QPS, availability, mobile constraints. [blog.openreplay](https://blog.openreplay.com/5-tips-aiml-interview-2025/)
- Metrics: answer quality, time to first token, retention, study outcomes (e.g., completion of plans). [systemdesignhandbook](https://www.systemdesignhandbook.com/guides/ml-system-design/)

2) High-level architecture  
Sketch a layered view. [igotanoffer](https://igotanoffer.com/blogs/tech/system-design-interviews)

- Clients: iOS/Android/web app. [eu-startups](https://www.eu-startups.com/2025/06/german-edtech-startup-knowunity-raises-e27-million-to-bring-ai-tutor-to-1-billion-students/)
- API gateway + auth: exposes endpoints like /ask, /recommend, /notes/search, /plan. [igotanoffer](https://igotanoffer.com/blogs/tech/system-design-interviews)
- Core services:  
  - User profile + curriculum service (grade, country, subjects). [eu-startups](https://www.eu-startups.com/2025/06/german-edtech-startup-knowunity-raises-e27-million-to-bring-ai-tutor-to-1-billion-students/)
  - Content ingestion & processing (notes, flashcards, quizzes). [vestbee](https://vestbee.com/insights/articles/knowunity-secures-27-m)
  - Search/RAG service over student-generated content. [systemdesignhandbook](https://www.systemdesignhandbook.com/guides/ml-system-design/)
  - LLM orchestration service (prompting, tools, routing). [youtube](https://www.youtube.com/watch?v=xj5Nf0-S4_0)
  - Recommendation / personalization service. [blog.openreplay](https://blog.openreplay.com/5-tips-aiml-interview-2025/)
- Data stores:  
  - OLTP DB for users, subscriptions, metadata. [igotanoffer](https://igotanoffer.com/blogs/tech/system-design-interviews)
  - Object store for raw documents (PDF, images). [igotanoffer](https://igotanoffer.com/blogs/tech/system-design-interviews)
  - Feature store for ML features. [systemdesignhandbook](https://www.systemdesignhandbook.com/guides/machine-learning-system-design-interview/)
  - Vector DB / embedding index for notes and Q&A. [systemdesignhandbook](https://www.systemdesignhandbook.com/guides/machine-learning-system-design-interview/)
- Infra: load balancers, stateless app servers, queues for async jobs, monitoring and logging. [systemdesignhandbook](https://www.systemdesignhandbook.com/guides/ml-system-design/)

3) Data & ML pipelines  
Focus on how the 3M+ materials become reliable AI inputs. [vestbee](https://vestbee.com/insights/articles/knowunity-secures-27-m)

- Ingestion: upload notes via app, store in blob store, write metadata to DB, enqueue processing jobs. [vestbee](https://vestbee.com/insights/articles/knowunity-secures-27-m)
- Processing:  
  - OCR (if images), language detection, subject/grade classification. [systemdesignhandbook](https://www.systemdesignhandbook.com/guides/machine-learning-system-design-interview/)
  - Quality filters (spam, low-quality, policy-violating content). [systemdesignhandbook](https://www.systemdesignhandbook.com/guides/ml-system-design/)
  - Chunking, embedding computation, storage in vector DB with metadata (subject, curriculum, difficulty). [systemdesignhandbook](https://www.systemdesignhandbook.com/guides/machine-learning-system-design-interview/)
- Training:  
  - Train ranking models for “best notes” per query, user, and curriculum. [systemdesignhandbook](https://www.systemdesignhandbook.com/guides/ml-system-design/)
  - Recommendation models for next study item / plan. [blog.openreplay](https://blog.openreplay.com/5-tips-aiml-interview-2025/)
- Feedback loops: thumbs up/down, dwell time on answers, test results feed back into models. [blog.openreplay](https://blog.openreplay.com/5-tips-aiml-interview-2025/)

4) LLM/RAG design for the tutor  
This is likely the critical deep dive. [youtube](https://www.youtube.com/watch?v=xj5Nf0-S4_0)

- Retrieval:  
  - For each question, use semantic + keyword search over the vector DB, filter by language, grade, subject, curriculum. [eu-startups](https://www.eu-startups.com/2025/06/german-edtech-startup-knowunity-raises-e27-million-to-bring-ai-tutor-to-1-billion-students/)
  - Optionally re-rank retrieved chunks with a learned re-ranker. [systemdesignhandbook](https://www.systemdesignhandbook.com/guides/machine-learning-system-design-interview/)
- Orchestration:  
  - LLM gateway that supports multiple models (e.g., cheap/fast vs high-quality). [youtube](https://www.youtube.com/watch?v=xj5Nf0-S4_0)
  - Prompt templates including student profile, retrieved notes, and constraints (“explain like I’m 15, German curriculum”). [youtube](https://www.youtube.com/watch?v=xj5Nf0-S4_0)
  - Tools: calculator, unit converter, perhaps a “quiz generator” tool that hits internal services. [youtube](https://www.youtube.com/watch?v=xj5Nf0-S4_0)
- Caching and cost control:  
  - Response cache keyed by (normalized question, subject, grade, locale) with TTL. [igotanoffer](https://igotanoffer.com/blogs/tech/system-design-interviews)
  - Precompute explanations for high-volume topics; store them in DB and use LLM only to adapt tone/level. [systemdesignhandbook](https://www.systemdesignhandbook.com/guides/ml-system-design/)
- Safety & quality:  
  - Content filters (profanity, self-harm, etc.), curriculum-appropriate policy rules. [systemdesignhandbook](https://www.systemdesignhandbook.com/guides/machine-learning-system-design-interview/)
  - Guardrail prompts and output moderation models. [systemdesignhandbook](https://www.systemdesignhandbook.com/guides/ml-system-design/)

5) Recommendations & personalization  
Tie design back to their “personalized learning” narrative. [portfolion](https://www.portfolion.com/companies/knowunity)

- Input signals: user grade, subjects, exam dates, time left, previous interactions, success on quizzes. [eu-startups](https://www.eu-startups.com/2025/06/german-edtech-startup-knowunity-raises-e27-million-to-bring-ai-tutor-to-1-billion-students/)
- Models:  
  - Content-based + collaborative filtering for which notes/explainers to show. [systemdesignhandbook](https://www.systemdesignhandbook.com/guides/machine-learning-system-design-interview/)
  - Sequence models for revision plan generation and “what to learn next”. [systemdesignhandbook](https://www.systemdesignhandbook.com/guides/ml-system-design/)
- Serving: low-latency feature store + online inference. [systemdesignhandbook](https://www.systemdesignhandbook.com/guides/machine-learning-system-design-interview/)

6) Reliability, scaling, and observability  
Show you can run this in production for millions. [blog.openreplay](https://blog.openreplay.com/5-tips-aiml-interview-2025/)

- Horizontal scaling of stateless services behind load balancers, auto-scaling based on CPU/QPS. [igotanoffer](https://igotanoffer.com/blogs/tech/system-design-interviews)
- Region-aware deployment (at least EU vs LatAm) for latency and data residency. [eu-startups](https://www.eu-startups.com/2025/06/german-edtech-startup-knowunity-raises-e27-million-to-bring-ai-tutor-to-1-billion-students/)
- Backpressure: queues for heavy processing (embeddings, training jobs). [igotanoffer](https://igotanoffer.com/blogs/tech/system-design-interviews)
- Monitoring: per endpoint latency, error rate, LLM timeouts, token usage, drift in model performance, business KPIs (DAU, retention). [blog.openreplay](https://blog.openreplay.com/5-tips-aiml-interview-2025/)
- Fallbacks: if LLM is down, return pre-generated explanations or a simpler model’s output. [systemdesignhandbook](https://www.systemdesignhandbook.com/guides/ml-system-design/)

## 4. How to practice (next 7–10 days)

Leverage your existing strengths but practice interview-style articulation. [blog.openreplay](https://blog.openreplay.com/5-tips-aiml-interview-2025/)

- Pick 3–4 scenarios and do 45-minute mocks:  
  - “Design an AI tutor for math exams for German students.”  
  - “Design a global notes search + recommendation system for 30M students.”  
  - “Design an LLM-based chat assistant for school, with guardrails and cost caps.”  
- For each, follow the same structure: clarify, HLD, data/ML pipeline, LLM/RAG, scaling/monitoring, trade-offs. [systemdesignhandbook](https://www.systemdesignhandbook.com/guides/machine-learning-system-design-interview/)
- Draw diagrams (even on paper) with clear boxes: client, gateway, services, DBs, queues, models. [blog.openreplay](https://blog.openreplay.com/5-tips-aiml-interview-2025/)
- Practice 2–3 deep dives:  
  - Retrieval pipeline and vector DB design. [systemdesignhandbook](https://www.systemdesignhandbook.com/guides/ml-system-design/)
  - Recommendation system (features, offline/online flow). [systemdesignhandbook](https://www.systemdesignhandbook.com/guides/machine-learning-system-design-interview/)
  - LLM orchestration and caching strategy. [youtube](https://www.youtube.com/watch?v=xj5Nf0-S4_0)

## 5. Tailored prep for your profile

Given your background in RAG, LoRA, and scalable backend:

- Bring concrete numbers (e.g., “assume 20M MAU, 2M DAU, 1–2 QPS per user at peak exam season, so peak ~50k QPS globally”) and reason about infra sizing. [eu-startups](https://www.eu-startups.com/2025/06/german-edtech-startup-knowunity-raises-e27-million-to-bring-ai-tutor-to-1-billion-students/)
- Emphasize how you’d use PEFT/LoRA or instruction tuning on top of a base LLM using KnowUnity’s localized materials while protecting PII and complying with EU laws. [vestbee](https://vestbee.com/insights/articles/knowunity-secures-27-m)
- Highlight trade-offs between:  
  - Full fine-tuning vs RAG vs prompt engineering for new curricula and countries. [systemdesignhandbook](https://www.systemdesignhandbook.com/guides/ml-system-design/)
  - Single global model vs per-locale adapters. [systemdesignhandbook](https://www.systemdesignhandbook.com/guides/machine-learning-system-design-interview/)
  - Max accuracy vs latency/cost on mobile. [blog.openreplay](https://blog.openreplay.com/5-tips-aiml-interview-2025/)

If you share the exact JD or what they told you about the round, I can help you craft 1–2 full example designs and a checklist of points to hit during the interview.



----
----


For 20k concurrent students, design a multi-tier LLM + RAG system with stateless chat services, a separate retrieval layer, and horizontally scalable LLM workers behind a gateway. [pmc.ncbi.nlm.nih](https://pmc.ncbi.nlm.nih.gov/articles/PMC12453719/)

## 1. Clarify requirements

- Functional: chat Q&A, explanations, step-by-step help, simple quizzes, persistent sessions, per-student personalization. [arxiv](https://arxiv.org/html/2507.18882v1)
- Non-functional: 20k concurrent users, target p95 latency ~1–2 s for full answer with streaming, high availability, strict safety, and cost control per request. [spiralcompute.co](https://www.spiralcompute.co.nz/designing-ai-powered-tutoring-systems-for-digital-first-classrooms/)
- Scope assumptions: text-only chat (no voice), curriculum-aligned content, web/mobile clients, global but mainly one region initially.

## 2. High-level architecture

- Clients: browser/mobile app using WebSocket/HTTP for chat, with streaming responses. [irjmets](https://www.irjmets.com/upload_newfiles/irjmets70600144789/paper_file/irjmets70600144789.pdf)
- Edge/API gateway: auth, rate limiting, routing to Chat Service and auxiliary APIs (e.g., /quiz, /progress). [fvs.com](https://fvs.com.py/download/papersCollection/1ZjgYM/Alex%20Xu%20Machine%20Learning%20System%20Design%20Interview.pdf)
- Core services:  
  - Chat Orchestrator: session state, dialog context, calls retrieval + LLM gateway, handles streaming back to client. [aclanthology](https://aclanthology.org/2023.findings-emnlp.130.pdf)
  - Retrieval Service: semantic + keyword search over course/tutor docs (RAG). [arxiv](https://arxiv.org/pdf/2311.17696.pdf)
  - Student Profile Service: stores knowledge state, preferences, curriculum and class enrollment. [arxiv](https://arxiv.org/html/2507.18882v1)
  - Progress & Assessment Service: quizzes, mastery estimates, hint logic. [aclanthology](https://aclanthology.org/2023.findings-emnlp.130.pdf)
- Data stores:  
  - Relational DB for users, sessions, progress, metadata. [irjmets](https://www.irjmets.com/upload_newfiles/irjmets70600144789/paper_file/irjmets70600144789.pdf)
  - Object storage for raw course docs and uploads. [pmc.ncbi.nlm.nih](https://pmc.ncbi.nlm.nih.gov/articles/PMC12453719/)
  - Vector DB for embeddings of course material and canonical explanations. [arxiv](https://arxiv.org/pdf/2311.17696.pdf)

## 3. RAG and tutoring logic

- Ingestion pipeline: take course PDFs/notes, chunk, embed with sentence-transformer, store in vector DB with tags (topic, difficulty, curriculum). [pmc.ncbi.nlm.nih](https://pmc.ncbi.nlm.nih.gov/articles/PMC12453719/)
- Query flow:  
  1) Normalize question, add student profile features (course, topic, level). [arxiv](https://arxiv.org/html/2507.18882v1)
  2) Retrieve top-k chunks from vector DB + optionally knowledge graph nodes. [arxiv](https://arxiv.org/pdf/2311.17696.pdf)
  3) Build prompt: instructions (pedagogy, “step-by-step, Socratic”), context docs, student state, conversation history. [aclanthology](https://aclanthology.org/2023.findings-emnlp.130.pdf)
  4) Call LLM gateway, stream tokens back; optionally generate hints or follow-up questions using tutor policy. [pmc.ncbi.nlm.nih](https://pmc.ncbi.nlm.nih.gov/articles/PMC12453719/)
- Hallucination control: require answers to cite retrieved material, use answer-verification / confidence scoring to refuse uncertain responses. [agentiveaiq](https://agentiveaiq.com/listicles/5-must-have-rag-powered-llm-agents-for-tutoring-centers)

## 4. Scaling to 20k concurrent users

- Concurrency → throughput: assume avg session sends 1 question every 20–30 seconds; 20k concurrent → ~700–1000 QPS at peak. [systemdesignhandbook](https://www.systemdesignhandbook.com/guides/machine-learning-system-design-interview/)
- Stateless services: Chat Orchestrator and Retrieval Service are stateless and scale horizontally behind load balancers; user/session state in DB/Redis. [fvs.com](https://fvs.com.py/download/papersCollection/1ZjgYM/Alex%20Xu%20Machine%20Learning%20System%20Design%20Interview.pdf)
- LLM gateway:  
  - Pool of LLM worker pods (or external provider) with autoscaling on tokens/s and queue depth. [systemdesignhandbook](https://www.systemdesignhandbook.com/guides/machine-learning-system-design-interview/)
  - Use streaming: send first token within 300–500 ms by starting generation as soon as retrieval finishes. [spiralcompute.co](https://www.spiralcompute.co.nz/designing-ai-powered-tutoring-systems-for-digital-first-classrooms/)
  - Tiered models: cheap, fast model for most turns; higher-quality model for “exam-mode” or stuck students only. [linkedin](https://www.linkedin.com/pulse/multi-agent-approach-building-ai-tutor-interview-screening-mojes-lozlf)
- Retrieval scaling:  
  - Vector DB sharded by course/domain; replicas for read throughput. [arxiv](https://arxiv.org/pdf/2311.17696.pdf)
  - Cache popular queries and canonical explanations in Redis/CDN; many students ask the same questions. [agentiveaiq](https://agentiveaiq.com/listicles/5-must-have-rag-powered-llm-agents-for-tutoring-centers)
- Backpressure: if LLM queue is high, degrade gracefully: shorter context, lower max tokens, more cache hits, or temporarily limit long-form explanations. [linkedin](https://www.linkedin.com/pulse/multi-agent-approach-building-ai-tutor-interview-screening-mojes-lozlf)

## 5. Personalization and pedagogy

- Student model: maintain estimated mastery per concept (e.g., Bayesian or RL-based tutor models). [sciencedirect](https://www.sciencedirect.com/science/article/pii/S0957417425002854)
- Adaptive responses: adjust explanation depth, examples, and hint frequency using student model and zone-of-proximal-development logic. [sciencedirect](https://www.sciencedirect.com/science/article/pii/S0957417425002854)
- Mixed-initiative: tutor occasionally asks questions, proposes practice problems, and adapts next steps based on responses. [arxiv](https://arxiv.org/html/2507.18882v1)

## 6. Reliability, safety, and monitoring

- Safety: content filters for harmful topics, age-appropriate guidelines, plus moderation for user-generated inputs and outputs. [arxiv](https://arxiv.org/html/2507.18882v1)
- Observability:  
  - Metrics: QPS, latency, token usage, cache hit rate, retrieval recall, tutor satisfaction, learning gains where available. [systemdesignhandbook](https://www.systemdesignhandbook.com/guides/machine-learning-system-design-interview/)
  - Traces: end-to-end spans including retrieval and LLM calls for debugging. [systemdesignhandbook](https://www.systemdesignhandbook.com/guides/machine-learning-system-design-interview/)
- Resilience: timeouts and retries on LLM calls, circuit breakers, fall back to pre-generated answers or simpler models on failure. [pmc.ncbi.nlm.nih](https://pmc.ncbi.nlm.nih.gov/articles/PMC12453719/)

## 7. How to present this in an interview

- Walk the interviewer through: requirements → traffic estimates → high-level architecture → RAG flow → LLM scaling → personalization → reliability. [fvs.com](https://fvs.com.py/download/papersCollection/1ZjgYM/Alex%20Xu%20Machine%20Learning%20System%20Design%20Interview.pdf)
- Be explicit about numbers (QPS, latency targets, token budgets) and trade-offs (quality vs cost, global vs per-course models, vector DB choice, caching strategy). [linkedin](https://www.linkedin.com/pulse/multi-agent-approach-building-ai-tutor-interview-screening-mojes-lozlf)