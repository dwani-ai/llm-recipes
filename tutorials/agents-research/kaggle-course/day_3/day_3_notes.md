Day 3 Notes

- Agent Quality
    - The Trajectory is the Truth
    - Observability is the Foundation
    - Evaluation is a Continuous Loop


- Chapter 1: Agent Quality in a Non-Deterministic World
    - Effectiveness, Efficiency, Robustness,
and Safety
- Chapter 2: The Art of Agent Evaluation
- Chapter 3: Observability -  Three Pillars of Observability: Logs, Traces, and Metrics
- Chaper 4 : Agent Quality Flywheel

- Agent Quality in a Non-Deterministic World
    - Failure modes in Agents
        - Algorithmic Bias
        - Factual Hallucination
        - Performance & Concept Drift
        - Emergent Unintended Behaviors

- From Predictable Code to Unpredictable Agents
    - Traditional Machine Learning
    - The Passive LLM
    - LLM+RAG (Retrieval-Augmented Generation)
    - The Active AI Agent
        - Planning and Multi-Step Reasoning
        - Tool Use and Function Calling
        - Memory
    - Multi-Agent Systems
        - Emergent System Failures
        - Cooperative vs. Competitive Evaluation

- Agent Quality
    - Effectiveness (Goal Achievement)
        - Did the agent successfully and accurately achieve the user's actual intent?
    - Efficiency (Operational Cost)
        - Efficiency is measured in resources consumed: total tokens (cost), wall-clock time (latency), and trajectory complexity(total number of steps)
    - Robustness (Reliability)
        - How does the agent handle adversity and the messiness of the real world?
    - Safety & Alignment (Trustworthiness): 
        - Does the agent operate within its defined ethical boundaries and constraints?

- The Art of Agent Evaluation: Judging the Process
    - A Strategic Framework: The "Outside-In" Evaluation Hierarchy
        -   The "Outside-In" View: End-to-End Evaluation (The Black Box)
            - evaluate the agent's final performance against its defined objective
                - Task Success Rate
                - User Satisfaction
                - Overall Quality

        - The "Inside-Out" View: Trajectory Evaluation (The Glass Box)
            - LLM Planning (The "Thought")
            - Tool Usage (Selection & Parameterization)
            - Tool Response Interpretation (The "Observation")
            - RAG Performance
            - Trajectory Efficiency and Robustness
            - Multi-Agent Dynamics

- The Evaluators: The Who and What of Agent Judgment
     - Automated Metrics
        - Automated metrics provide speed and reproducibility. They are useful for regression testing and benchmarking outputs. Examples include:
            - String-based similarity (ROUGE, BLEU), comparing generated text to references.
            - Embedding-based similarity (BERTScore, cosine similarity), measuring semantic closeness.
            - Task-specific benchmarks, e.g., TruthfulQA 2

- The LLM-as-a-Judge Paradigm
    - involves using a powerful, state-of-the-art model to evaluate the outputs of another agent.
    - To implement this, prioritize pairwise comparison over single-scoring to mitigate the exact biases mentioned 
    - [https://llm-as-a-judge.github.io/](https://llm-as-a-judge.github.io/)

"""

You are an expert evaluator for a customer support chatbot. 
Your goal is to assess which of two responses is more helpful, polite, and correct.

[User Query]
"Hi, my order #12345 hasn't arrived yet."

[Answer A]
"I can see that order #12345 is currently out for delivery and should
arrive by 5 PM today."

[Answer B]
"Order #12345 is on the truck. It will be there by 5."

Please evaluate which answer is better. Compare them on correctness, helpfulness, and tone. 

Provide your reasoning and then output your final
decision in a JSON object with a "winner" key (either "A", "B", or "tie")
and a "rationale" key.

"""    

- Agent as Judge
    - Plan quality: Was the plan logically structured and feasible?
    - Tool use: Were the right tools chosen and applied correctly?
    - Context handling: Did the agent use prior information effectively?

"""
To implement an Agent-as-a-Judge, consider feeding relevant parts of the execution
trace object to your judge. First, configure your agent framework to log and
export the trace, including the internal plan, the list of tools chosen, and the exact
arguments passed
""

- Human-in-the-Loop (HITL) Evaluation
    - Domain Expertise
    - Interpreting Nuance
    - Creating the "Golden Set"

- User Feedback and Reviewer UI
    - Low-friction feedback: thumbs up/down, quick sliders, or short comments.
    - Context-rich review: feedback should be paired with the full conversation and agent’s reasoning trace.
    - Reviewer User Interface (UI): a two-panel interface: conversation on the left, reasoning steps on the right, with inline tagging for issues like “bad plan” or “tool misuse.”
    - Governance dashboards: aggregate feedback to highlight recurring issues and risks.

- Beyond Performance: Responsible AI (RAI) & Safety Evaluation
    - Systematic Red Teaming
    - Automated Filters & Human Review
    - Adherence to Guidelines

- performance metrics tell us if the agent can do the job, but safety evaluation tells
us if it should.