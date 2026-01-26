Multi-agent LLM systems like GenMentor and IntelliCode enable dynamic, personalized learning paths by decomposing tasks across specialized agents for assessment, planning, and adaptation. [arxiv](https://arxiv.org/abs/2501.15749)

## Core Architecture

Deploy a supervisor-orchestrated multi-agent workflow using frameworks like LangGraph or AutoGen, with shared learner state in a central store (Redis/Postgres). [github](https://github.com/GeminiLight/gen-mentor)

- **Supervisor Agent**: Routes tasks, resolves conflicts, and iterates until path converges (e.g., goal achieved). [arxiv](https://arxiv.org/abs/2512.18669)
- **Agents collaborate via message passing** on events like quiz completion or goal update. [arxiv](https://arxiv.org/abs/2508.11401)
- **State management**: Versioned learner profile (mastery per skill, misconceptions, engagement, goals). [arxiv](https://arxiv.org/abs/2512.18669)

## Key Agents

| Agent                  | Role                                                                 | Tools/Inputs                          | Outputs                          |
|------------------------|----------------------------------------------------------------------|---------------------------------------|----------------------------------|
| Goal Analyzer         | Maps user goals (e.g., "ace math exam") to skills/knowledge graph.   | Goal prompt, curriculum KG.          | Skill requirements, gaps.  [arxiv](https://arxiv.org/abs/2501.15749) |
| Assessor              | Evaluates mastery via quizzes/hints; detects misconceptions.         | Learner responses, prior state.      | Mastery scores, errors.  [arxiv](https://arxiv.org/abs/2512.18669) |
| Path Planner          | Builds optimal sequence (prereqs first, spaced repetition).          | Skill gaps, dependencies, time budget.| Learning sequence, milestones.  [arxiv](https://arxiv.org/abs/2501.15749) |
| Content Curator       | Generates/adapts materials (explanations, exercises) per profile.    | RAG over notes, learner level/motivation.| Personalized modules.  [arxiv](https://arxiv.org/abs/2508.11401) |
| Engagement Monitor    | Tracks dwell time, frustration; adjusts difficulty/pace.             | Session logs, biometrics (opt.).     | Interventions (hints, breaks).  [arxiv](https://arxiv.org/abs/2512.18669) |
| Evaluator             | Scores path effectiveness; suggests refinements.                     | Outcomes, learner feedback.          | Audit log, optimizations.  [arxiv](https://arxiv.org/abs/2508.11401) |

## Workflow

1. **Intake**: Goal Analyzer + Assessor build initial profile from baseline quiz. [tianfuwang](https://tianfuwang.tech/gen-mentor/)
2. **Planning**: Path Planner generates sequence using optimization (e.g., topological sort on KG + learner velocity). [arxiv](https://arxiv.org/abs/2501.15749)
3. **Delivery**: Content Curator serves next item; Assessor checks progress in real-time. [arxiv](https://arxiv.org/abs/2508.11401)
4. **Adaptation**: Engagement Monitor flags issues → Supervisor re-routes (e.g., simplify, insert review); loop until mastery threshold. [arxiv](https://arxiv.org/abs/2512.18669)
5. **Review**: Evaluator audits; update global models with anonymized data. [arxiv](https://arxiv.org/abs/2508.11401)

## Scaling and Integration

- **Infra**: Stateless agents on Kubernetes; LLM calls via Gemini 2.5 Flash for low latency. [ieeesmc](https://www.ieeesmc.org/cai-2026/tutorial-9-designing-end-to-end-multi-agent-ai-systems/)
- **Data**: Knowledge graph (Neo4j) for curriculum dependencies; vector DB for content RAG. [edtechbooks](https://edtechbooks.org/jaid_14_3/pkvbrlqcgn)
- **Personalization**: Bayesian mastery models + RL for path optimization; motivation signals from surveys. [arxiv](https://arxiv.org/abs/2501.15749)
- **Safety**: Guardrails on all agents; human-in-loop for high-stakes paths. [arxiv](https://arxiv.org/abs/2508.11401)

This mirrors production systems like GenMentor, boosting completion rates 20–30% via adaptive paths. [tianfuwang](https://tianfuwang.tech/gen-mentor/)



---


Multi-agent tutor for 1M DAU costs ~$1.24M/month using Gemini 2.5 Flash, with LLM calls at $567k and infra at $670k. [knowunity](https://knowunity.com/careers)

## Workload Assumptions

10M daily queries (10/user), but 3x tokens/query for agent orchestration (3k in, 900 out); 40% caching. [knowunity](https://knowunity.com/careers)

- Monthly input tokens: 540B (540M × 1k effective). [knowunity](https://knowunity.com/careers)
- Monthly output tokens: 162B (162M × 300 effective). [knowunity](https://knowunity.com/careers)
- Pricing: Gemini 2.5 Flash ($0.30/M in, $2.50/M out). [pricepertoken](https://pricepertoken.com/pricing-page/model/google-gemini-2.5-flash)

## Cost Breakdown

| Component             | Monthly Cost | Details |
|-----------------------|--------------|---------|
| LLM Calls            | **$567k**   | 540B in + 162B out tokens  [knowunity](https://knowunity.com/careers) |
| App Servers          | $110k       | 200 Kubernetes pods (m5.4xlarge, high QPS) |
| Vector DB + KG       | $500k       | Pinecone (retrieval) + Neo4j (curriculum graph), 100 nodes  [knowunity](https://knowunity.com/careers) |
| Storage/Cache        | $10k        | S3/Redis for content, sessions |
| Orchestration        | $50k        | Queues, monitoring, autoscaling |
| **Total**            | **$1.24M**  | Optimized; GPT-5 would double LLM spend  [knowunity](https://knowunity.com/careers) |

## Optimization Levers

- **Caching/Precompute**: 50–60% hit rate on assessments/plans → $300k LLM savings. [knowunity](https://knowunity.com/careers)
- **Agent routing**: 70% fast/small model (Gemini Nano), 30% full → 40% LLM cut.  
- **Spot instances**: 50% off infra → $840k total.  
- **Hybrid**: Self-host lighter agents on CPUs to offload. [ieeesmc](https://www.ieeesmc.org/cai-2026/tutorial-9-designing-end-to-end-multi-agent-ai-systems/)

At scale, ~$1/user/month; monitor agent loop iterations to control token burn. [knowunity](https://knowunity.com/careers)