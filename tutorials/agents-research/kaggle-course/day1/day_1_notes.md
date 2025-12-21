Day 1 Notes

- paper provides a comprehensive foundation:
    - Core Anatomy: Deconstructing an agent into its three essential components: the reasoning Model, actionable Tools, and the governing Orchestration Layer.
    -  A Taxonomy of Capabilities: Classifying agents from simple, connected problem-solvers to complex, collaborative multi-agent systems.
    -  Architectural Design: Diving into the practical design considerations for each component, from model selection to tool implementation.
    -  Building for Production: Establishing the Agent Ops discipline needed to evaluate,   debug, secure, and scale agentic systems from a single instance to a fleet with enterprise governance.

- AI Agent can be defined as the combination of models, tools, an
orchestration layer, and runtime services which uses the LM in a loop to accomplish a goal.


- These four elements form the essential architecture of any autonomous system.
    - The Model (The "Brain"): The core language model (LM) or foundation model that serves as the agent's central reasoning engine to process information, evaluate options, and make decisions.
    - Tools (The "Hands"): These mechanisms connect the agent's reasoning to the outside world, enabling actions beyond text generation
    - The Orchestration Layer (The "Nervous System"): The governing process that manages the agent's operational loop. It handles planning, memory (state), and reasoning strategy execution.
    - Deployment (The "Body and Legs"): This involves hosting the agent on a secure, scalable server and integrating it with essential production services for monitoring, logging, and management .


- Agentic AI problem-solving process
    - Get the Mission
    - Scane the Scene
    - Think it through
    - Take Action
    - Learn and Get Better

- Taxonomy of Agentic Systems
    - Level 0 - The Core Reasoning System
    - Level 1 - The Connected Problem Solver
    - Level 2 - The Strategic Problem Solver
    - Level 3 - Collaborative - Multi Agent Systems
    - Level 4 - Self Evolving Agents
    
- Level 0- Core Reasoning System
    - In this configuration, a Language Model (LM )operates in isolation, responding solely based on its vast pre-trained knowledge without any tools, memory, or interaction with the live environment.
- Level 1 -The Connected Problem-Solver
    - At this level, the reasoning engine becomes a functional agent by connecting to and utilizing external tools - the "Hands" component of our architecture. Its problem-solving is no longer confined to its static, pre-trained knowledge.
- Level 2: The Strategic Problem-Solver
    Level 2 marks a significant expansion in capability, moving from executing simple tasks to strategically planning complex, multi-part goals. The key skill that emerges here is context engineering: the agent's ability to actively select, package, and manage the most relevant information for each step of its plan.

- Level 3: The Collaborative Multi-Agent System
    - At the highest level, the paradigm shifts entirely. We move away from building a single, all-powerful "super-agent" and toward a "team of specialists" working in concert, a model that directly mirrors a human organization. The system's collective strength lies in this division of labor. 

- Level 4: The Self-Evolving System
    - Level 4 represents a profound leap from delegation to autonomous creation and adaptation. At this level, an agentic system can identify gaps in its own capabilities and dynamically create new tools or even new agents to fill them. It moves from using a fixed set of resources to actively expanding them
        - Think
        - Act
        - Observe


- Memory - https://google.github.io/adk-docs/sessions/memory/

- Agentic Design Patter
    - https://cloud.google.com/architecture/choose-design-pattern-agentic-ai-system

- Vertex AI - Agent builder
    - https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/overview

- Agent Started Pack
    - https://github.com/GoogleCloudPlatform/agent-starter-pack

- AgentOps - OpenTelemetry - Agent Steps
    - https://opentelemetry.io/blog/2025/ai-agent-observability/


- Core Agent Architecture: Model, Tools, and Orchestration
    - Model: The “Brain” of your AI Agent
    - Tools: The "Hands" of your AI Agent
        - Retrieving Information: Grounding in Reality
        - Executing Actions: Changing the World
        - Function Calling: Connecting Tools to your Agent
    - The Orchestration Layer

    Core Design Choices
        - Instruct with Domain Knowledge and Persona
        - Augment with Context
        - Multi-Agent Systems and Design Patterns

- Agent Deployment and Services
    - https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/overview

- Agent Ops: A Structured Approach to the Unpredictable
    - https://medium.com/@sokratis.kartakis/genai-in-production-mlops-or-genaiops-25691c9becd0
    - Measure What Matters: Instrumenting Success Like an
    - Quality Instead of Pass/Fail: Using a LM Judge
    - Metrics-Driven Development: Your Go/No-Go for Deployment
    - Debug with OpenTelemetry Traces: Answering "Why?"
    - Cherish Human Feedback: Guiding Your Automation

- Agent Interoperability
    - Agents and Humans
    - Agents and Agents
        - Agent2Agent (A2A) protocol
    - Agents and Money
        - Agent Payments Protocol (AP2)
    - 

- Securing a Single Agent: The Trust Trade-Off
    - Agent Identity: A New Class of Principal
    - Prompt Injection - https://simonwillison.net/series/prompt-injection/
    - Defense in Depth
        - https://storage.googleapis.com/gweb-research2023-media/pubtools/1018686.pdf
    - Policies to Constrain Access

- Securing an ADK Agent
    - https://google.github.io/adk-docs/callbacks/design-patterns-and-best-practices/#guardrails-policy-enforcement

    - A common pattern is a
        - "Gemini as a Judge" that uses a fast, inexpensive model like Gemini Flash-Lite or your own fine-tuned Gemma model to screen user inputs and agent outputs for prompt injections or harmful content in real time        
    - Model Armor
        - https://cloud.google.com/security-command-center/docs/model-armor-overview

    - https://saif.google/focus-on-agents

- Secuirty
    - Security and Privacy: Hardening the Agentic Frontier
    - Agent Governance: A Control Plane instead of Sprawl
    - Cost and Reliability: The Infrastructure Foundation

- Self Evolving Agents
    - https://github.com/CharlesQ9/Self-Evolving-Agents

- How agents learn and self evolve
    - Runtime Experience: Agents learn from runtime artifacts such as session logs, traces, and memory, which capture successes, failures, tool interactions, and decision trajectories
    - External Signals: Learning is also driven by new external documents, such as updated enterprise policies, public regulatory guidelines, or critiques from other agents.

    - Enhanced Context Engineering - the system continuously refines its prompts, few-shot examples, and the information it retrieves from memory.
    - Tool Optimization and Creation: The agent’s reasoning can identify gaps in its capabilities and act to fill them.

    --- 

- Example: Learning New Compliance Guidelines
    - Consider an enterprise agent operating in a heavily regulated industry like finance or life sciences. Its task is to generate reports that must comply with privacy and regulatory rules (e.g., GDPR).
    -     This can be implemented using a multi-agent workflow:
        1. A Querying Agent retrieves raw data in response to a user request.
        2. A Reporting Agent synthesizes this data into a draft report.
        3. A Critiquing Agent, armed with known compliance guidelines, reviews the report. If it encounters ambiguity or requires final sign-off, it escalates to a human domain expert.
        4. A Learning Agent observes the entire interaction, paying special attention to the corrective feedback from the human expert. It then generalizes this feedback into a new,reusable guideline (e.g., an updated rule for the critiquing agent or refined context for the reporting agent).

- Simulation and Agent Gym - the next frontier

- Google Co-Scientist - 
- AlphaEvolve
    - AlphaEvolve: A coding agent for scientific and algorithmic discovery
    - https://deepmind.google/blog/alphaevolve-a-gemini-powered-coding-agent-for-designing-advanced-algorithms/